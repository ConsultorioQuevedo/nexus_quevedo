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
import os
import re

# OCR opcional
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# PostgreSQL opcional
try:
    from sqlalchemy import create_engine
    PG_AVAILABLE = True
except Exception:
    PG_AVAILABLE = False

# -------------------------
# Configuración UI
# -------------------------
st.set_page_config(page_title="Nexus - Escanear y Registrar", layout="wide")
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
      html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #0E1117; color: #E6EEF3; }
      .stButton>button { background-color:#2563EB; color: white; width: 100%; }
      .stDownloadButton>button { background-color:#059669; color: white; width: 100%; }
      .card { background:#0F1724; padding:12px; border-radius:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

DBPATH = "nexussimple_scan.db"

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
def validar_glucosa(valor):
    try:
        v = float(valor)
    except Exception:
        return False, "Valor no numérico."
    if v <= 0 or v > 1000:
        return False, "Valor fuera de rango razonable."
    return True, ""

def guardar_glucosa(valor, nota=""):
    ok, msg = validar_glucosa(valor)
    if not ok:
        return False, msg
    fecha = datetime.datetime.now().isoformat(timespec="seconds")
    run_query('INSERT INTO glucosa (fecha, valor, nota) VALUES (?,?,?)', (fecha, float(valor), nota), fetch="none")
    return True, fecha

def listar_glucosa():
    rows = run_query('SELECT id, fecha, valor, nota FROM glucosa ORDER BY fecha DESC', fetch="all")
    return pd.DataFrame(rows, columns=["id","fecha","valor","nota"]) if rows else pd.DataFrame(columns=["id","fecha","valor","nota"])

def borrar_glucosa(row_id):
    run_query('DELETE FROM glucosa WHERE id=?', (row_id,), fetch="none")

def guardar_medicamento(nombre, dosis, hora, nota=""):
    if not nombre:
        return False, "Nombre del medicamento obligatorio."
    fecha = datetime.datetime.now().isoformat(timespec="seconds")
    run_query('INSERT INTO meds (fecha, nombre, dosis, nota) VALUES (?,?,?,?)', (fecha, nombre, dosis, nota), fetch="none")
    return True, fecha

def listar_meds():
    rows = run_query('SELECT id, fecha, nombre, dosis, nota FROM meds ORDER BY fecha DESC', fetch="all")
    return pd.DataFrame(rows, columns=["id","fecha","nombre","dosis","nota"]) if rows else pd.DataFrame(columns=["id","fecha","nombre","dosis","nota"])

def borrar_med(row_id):
    run_query('DELETE FROM meds WHERE id=?', (row_id,), fetch="none")

def guardar_cita(fecha_iso, doctor, nota=""):
    if not doctor:
        return False, "Doctor/Especialidad obligatorio."
    run_query('INSERT INTO citas (fecha, doctor, nota) VALUES (?,?,?)', (fecha_iso, doctor, nota), fetch="none")
    return True, fecha_iso

def listar_citas():
    rows = run_query('SELECT id, fecha, doctor, nota FROM citas ORDER BY fecha DESC', fetch="all")
    return pd.DataFrame(rows, columns=["id","fecha","doctor","nota"]) if rows else pd.DataFrame(columns=["id","fecha","doctor","nota"])

def borrar_cita(row_id):
    run_query('DELETE FROM citas WHERE id=?', (row_id,), fetch="none")

def guardar_escaneo(filename, texto):
    fecha = datetime.datetime.now().isoformat(timespec="seconds")
    run_query('INSERT INTO escaneos (fecha, filename, texto_extraido) VALUES (?,?,?)', (fecha, filename, texto), fetch="none")
    return True

def listar_escaneos():
    rows = run_query('SELECT id, fecha, filename, texto_extraido FROM escaneos ORDER BY fecha DESC', fetch="all")
    return pd.DataFrame(rows, columns=["id","fecha","filename","texto_extraido"]) if rows else pd.DataFrame(columns=["id","fecha","filename","texto_extraido"])

# Backup
def generar_backup_excel():
    dfg, dfm, dfc, dfe = listar_glucosa(), listar_meds(), listar_citas(), listar_escaneos()
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        dfg.to_excel(writer, sheet_name="Glucosa", index=False)
        dfm.to_excel(writer, sheet_name="Medicamentos", index=False)
        dfc.to_excel(writer, sheet_name="Citas", index=False)
        dfe.to_excel(writer, sheet_name="Escaneos", index=False)
    out.seek(0)
    return out

def generar_backup_csv():
    dfg, dfm, dfc, dfe = listar_glucosa(), listar_meds(), listar_citas(), listar_escaneos()
    out = BytesIO()
    s = f"=== Glucosa ===\n{dfg.to_csv(index=False)}\n=== Meds ===\n{dfm.to_csv(index=False)}\n=== Citas ===\n{dfc.to_csv(index=False)}\n=== Escaneos ===\n{dfe.to_csv(index=False)}"
    out.write(s.encode("utf-8"))
    out.seek(0)
    return out

# OCR
def ocr_from_bytes(file_bytes):
    if not OCR_AVAILABLE: return "OCR no disponible."
    try:
        img = Image.open(BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang='spa').strip()
    except Exception as e: return f"Error: {e}"

# QR
def generar_qr_for_scan(phone_number=None, email_address=None):
    token = str(uuid.uuid4())[:8]
    data = "Nexus-Scan"
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
st.title("Nexus - Escanear y ver registros")

st.sidebar.header("Acciones rápidas")
if st.sidebar.button("Generar QR WhatsApp"):
    img_bytes, token, link = generar_qr_for_scan(phone_number="1XXXXXXXXXX")
    st.sidebar.image(img_bytes, caption=f"Token: {token}")

if st.sidebar.button("Descargar Backup Excel"):
    st.sidebar.download_button("Bajar Excel", generar_backup_excel(), "backup.xlsx")

tabs = st.tabs(["Glucosa", "Medicamentos", "Citas", "Escanear / OCR", "Configuración"])

with tabs[0]:
    st.header("Glucosa")
    col1, col2 = st.columns([2,1])
    with col1:
        val = st.number_input("Valor (mg/dL)", min_value=0.0, key="g_val")
        nt = st.text_input("Nota", key="g_nt")
        if st.button("Guardar Glucosa"):
            ok, msg = guardar_glucosa(val, nt)
            if ok: st.success("Guardado"); st.rerun()
            else: st.error(msg)
    with col2:
        dfg = listar_glucosa()
        if not dfg.empty:
            st.dataframe(dfg, use_container_width=True)
            for _, row in dfg.head(5).iterrows():
                if st.button(f"Borrar ID {row['id']}", key=f"dg{row['id']}"):
                    borrar_glucosa(row['id']); st.rerun()

with tabs[1]:
    st.header("Medicamentos")
    nom = st.text_input("Nombre")
    dos = st.text_input("Dosis")
    hor = st.time_input("Hora")
    if st.button("Registrar Medicamento"):
        guardar_medicamento(nom, dos, str(hor))
        st.success("Registrado"); st.rerun()
    dfm = listar_meds()
    st.dataframe(dfm)

with tabs[2]:
    st.header("Citas")
    f_c = st.date_input("Fecha")
    h_c = st.time_input("Hora", key="h_c")
    doc = st.text_input("Doctor")
    if st.button("Agendar Cita"):
        dt = datetime.datetime.combine(f_c, h_c).isoformat()
        guardar_cita(dt, doc)
        st.success("Agendada"); st.rerun()
    st.dataframe(listar_citas())

with tabs[3]:
    st.header("Escanear / OCR")
    up = st.file_uploader("Subir imagen", type=["png","jpg","jpeg"])
    if up:
        st.image(up)
        if OCR_AVAILABLE:
            txt = ocr_from_bytes(up.getvalue())
            st.text_area("Texto detectado", txt)
            if st.button("Guardar como Escaneo"):
                guardar_escaneo(up.name, txt)
                st.success("Guardado")

with tabs[4]:
    st.header("Configuración")
    pg = st.text_input("PostgreSQL URL")
    if st.button("Migrar Datos"):
        ok, msg = migratetopostgres(pg)
        st.write(msg)
