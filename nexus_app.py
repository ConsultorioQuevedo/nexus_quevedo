import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
from io import BytesIO
import matplotlib.pyplot as plt
import base64
import qrcode
import uuid
import re
import os

# OCR opcional
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# PostgreSQL opcional (solo para migración)
try:
    from sqlalchemy import create_engine
    PG_AVAILABLE = True
except Exception:
    PG_AVAILABLE = False

# -------------------------
# Configuración UI
# -------------------------
st.set_page_config(page_title="Nexus - Escanear y Registrar (Sin Auth)", layout="wide")
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
      html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #0E1117; color: #E6EEF3; }
      .stButton>button { background-color:#2563EB; color: white; width: 100%; }
      .stDownloadButton>button { background-color:#059669; color: white; width: 100%; }
      .card { background:#0F1724; padding:12px; border-radius:8px; }
      .small { font-size:12px; color:#9CA3AF; }
    </style>
    """,
    unsafe_allow_html=True,
)

DBPATH = "nexusnoauth.db"

# -------------------------
# Base de datos (SQLite)
# -------------------------
def get_conn():
    return sqlite3.connect(DBPATH, check_same_thread=False)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS glucosa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                valor REAL,
                nota TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS meds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                nombre TEXT,
                dosis TEXT,
                hora TEXT,
                nota TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS citas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                doctor TEXT,
                nota TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS escaneos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                filename TEXT,
                texto_extraido TEXT
            )
        ''')
        conn.commit()

def run_query(sql, params=(), fetch="all"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        conn.commit()
    return None

init_db()

# -------------------------
# Funciones de negocio
# -------------------------
def guardar_glucosa(valor, nota=""):
    try:
        v = float(valor)
        if v <= 0 or v > 1000: return False, "Rango inválido."
    except: return False, "No es numérico."
    
    fecha = datetime.datetime.now().isoformat(timespec="seconds")
    run_query('INSERT INTO glucosa (fecha, valor, nota) VALUES (?,?,?)', (fecha, v, nota), fetch="none")
    return True, fecha

def listar_glucosa():
    rows = run_query('SELECT id, fecha, valor, nota FROM glucosa ORDER BY fecha DESC')
    return pd.DataFrame(rows, columns=["id","fecha","valor","nota"]) if rows else pd.DataFrame(columns=["id","fecha","valor","nota"])

def borrar_glucosa(rowid):
    run_query('DELETE FROM glucosa WHERE id=?', (rowid,), fetch="none")

def guardar_medicamento(nombre, dosis, hora, nota=""):
    if not nombre: return False, "Nombre obligatorio."
    fecha = datetime.datetime.now().isoformat(timespec="seconds")
    run_query('INSERT INTO meds (fecha, nombre, dosis, hora, nota) VALUES (?,?,?,?,?)', (fecha, nombre, dosis, str(hora), nota), fetch="none")
    return True, fecha

def listar_meds():
    rows = run_query('SELECT id, fecha, nombre, dosis, hora, nota FROM meds ORDER BY fecha DESC')
    return pd.DataFrame(rows, columns=["id","fecha","nombre","dosis","hora","nota"]) if rows else pd.DataFrame(columns=["id","fecha","nombre","dosis","hora","nota"])

def borrar_med(rowid):
    run_query('DELETE FROM meds WHERE id=?', (rowid,), fetch="none")

def guardar_cita(fechaiso, doctor, nota=""):
    if not doctor: return False, "Doctor obligatorio."
    run_query('INSERT INTO citas (fecha, doctor, nota) VALUES (?,?,?)', (fechaiso, doctor, nota), fetch="none")
    return True, fechaiso

def listar_citas():
    rows = run_query('SELECT id, fecha, doctor, nota FROM citas ORDER BY fecha DESC')
    return pd.DataFrame(rows, columns=["id","fecha","doctor","nota"]) if rows else pd.DataFrame(columns=["id","fecha","doctor","nota"])

def borrar_cita(rowid):
    run_query('DELETE FROM citas WHERE id=?', (rowid,), fetch="none")

def guardar_escaneo(filename, texto):
    fecha = datetime.datetime.now().isoformat(timespec="seconds")
    run_query('INSERT INTO escaneos (fecha, filename, texto_extraido) VALUES (?,?,?)', (fecha, filename, texto), fetch="none")
    return True

def listar_escaneos():
    rows = run_query('SELECT id, fecha, filename, texto_extraido FROM escaneos ORDER BY fecha DESC')
    return pd.DataFrame(rows, columns=["id","fecha","filename","texto_extraido"]) if rows else pd.DataFrame(columns=["id","fecha","filename","texto_extraido"])

# --- Backup ---
def generar_backup_excel():
    dfg, dfm, dfc, dfe = listar_glucosa(), listar_meds(), listar_citas(), listar_escaneos()
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        dfg.to_excel(writer, sheet_name="Glucosa", index=False)
        dfm.to_excel(writer, sheet_name="Meds", index=False)
        dfc.to_excel(writer, sheet_name="Citas", index=False)
        dfe.to_excel(writer, sheet_name="Escaneos", index=False)
    out.seek(0)
    return out

# --- OCR ---
def ocr_from_bytes(file_bytes):
    if not OCR_AVAILABLE: return "OCR no disponible."
    try:
        img = Image.open(BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang='spa').strip()
    except Exception as e: return f"Error OCR: {e}"

# --- QR ---
def generar_qr_for_scan(phone_number=None, email_address=None):
    token = str(uuid.uuid4())[:8]
    data = f"Nexus-Token-{token}"
    if phone_number:
        data = f"https://wa.me/{phone_number.lstrip('+')}?text=Nexus%20Scan%20Token%20{token}"
    elif email_address:
        data = f"mailto:{email_address}?subject=Scan%20{token}"
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue(), token, data

# -------------------------
# Interfaz principal
# -------------------------
st.title("Nexus - Escaneo y Registro Soberano")

st.sidebar.header("Acciones")
if st.sidebar.button("Generar QR WhatsApp"):
    img_b, token, link = generar_qr_for_scan(phone_number="1XXXXXXXXXX")
    st.sidebar.image(img_b, caption=f"Token: {token}")
    st.sidebar.write(f"[Link directo]({link})")

st.sidebar.markdown("---")
st.sidebar.download_button("📥 Backup Excel", generar_backup_excel(), "nexus_backup.xlsx")

tabs = st.tabs(["Glucosa", "Medicamentos", "Citas", "Escanear / OCR", "Migración"])

with tabs[0]:
    st.header("Glucosa")
    col1, col2 = st.columns([2,1])
    with col1:
        val = st.number_input("Valor (mg/dL)", min_value=0.0, step=1.0, key="g_val")
        nt = st.text_input("Nota", key="g_nt")
        if st.button("Guardar Glucosa"):
            ok, msg = guardar_glucosa(val, nt)
            if ok: st.success("Guardado"); st.rerun()
            else: st.error(msg)
        
        up_g = st.file_uploader("Subir imagen de análisis", type=["png","jpg","jpeg"], key="up_g")
        if up_g:
            st.image(up_g)
            if OCR_AVAILABLE:
                txt = ocr_from_bytes(up_g.getvalue())
                st.text_area("OCR detectado", txt)
                m = re.search(r"(\d{2,3}(\.\d+)?)", txt)
                if m:
                    st.info(f"Valor detectado: {m.group(1)}")
                    if st.button("Usar este valor"):
                        guardar_glucosa(m.group(1), f"OCR: {txt[:50]}")
                        st.rerun()
    with col2:
        dfg = listar_glucosa()
        if not dfg.empty:
            st.dataframe(dfg, use_container_width=True)
            for _, row in dfg.head(5).iterrows():
                if st.button(f"Borrar {row['id']}", key=f"bg{row['id']}"):
                    borrar_glucosa(row['id']); st.rerun()
            # Gráfico simple
            fig, ax = plt.subplots(figsize=(5,3))
            ax.plot(pd.to_datetime(dfg['fecha']), dfg['valor'], marker='o')
            st.pyplot(fig)

with tabs[1]:
    st.header("Medicamentos")
    nom = st.text_input("Nombre Med")
    dos = st.text_input("Dosis")
    hor = st.time_input("Hora")
    if st.button("Registrar Med"):
        guardar_medicamento(nom, dos, hor)
        st.success("Registrado"); st.rerun()
    st.dataframe(listar_meds(), use_container_width=True)

with tabs[2]:
    st.header("Citas")
    f_c = st.date_input("Fecha")
    h_c = st.time_input("Hora", key="hora_citas")
    doc = st.text_input("Doctor")
    if st.button("Agendar Cita"):
        dt = datetime.datetime.combine(f_c, h_c).isoformat()
        guardar_cita(dt, doc)
        st.success("Agendada"); st.rerun()
    st.dataframe(listar_citas(), use_container_width=True)

with tabs[3]:
    st.header("Visor / OCR")
    up_s = st.file_uploader("Subir documento", type=["png","jpg","jpeg","pdf"], key="up_s")
    if up_s:
        if up_s.name.lower().endswith(".pdf"):
            b64 = base64.b64encode(up_s.read()).decode('utf-8')
            st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600">', unsafe_allow_html=True)
        else:
            st.image(up_s)
            if OCR_AVAILABLE:
                txt = ocr_from_bytes(up_s.getvalue())
                st.text_area("Contenido", txt)
                if st.button("Guardar en Historial"):
                    guardar_escaneo(up_s.name, txt)
                    st.success("Guardado")
    st.dataframe(listar_escaneos(), use_container_width=True)

with tabs[4]:
    st.header("Migración")
    pg_url = st.text_input("PostgreSQL URL (SQLAlchemy)")
    if st.button("Iniciar Migración"):
        if PG_AVAILABLE:
            try:
                engine = create_engine(pg_url)
                # Aquí iría la lógica de .to_sql() para cada tabla
                st.success("Conexión establecida y datos migrados (simulado).")
            except Exception as e: st.error(f"Error: {e}")
        else: st.warning("Instale sqlalchemy para usar esta función.")
