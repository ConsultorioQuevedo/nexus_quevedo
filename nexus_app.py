import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import urllib.parse
import os
from fpdf import FPDF

# --- 1. CLASE PDF PROFESIONAL ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NEXUS - REPORTE DE SALUD', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo - Control Personal', 0, 0, 'C')
    def dibujar_semaforo(self, x, y, color_tipo):
        if color_tipo == "VERDE": self.set_fill_color(27, 94, 32) 
        elif color_tipo == "AMARILLO": self.set_fill_color(251, 192, 45) 
        elif color_tipo == "ROJO": self.set_fill_color(183, 28, 28) 
        else: self.set_fill_color(200, 200, 200) 
        self.ellipse(x, y, 4, 4, 'F')

# --- 2. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 10px 0; }
    .alerta-card { padding: 15px; border-radius: 10px; border-left: 5px solid; margin-bottom: 15px; background-color: #1c2128; border: 1px solid #30363d; }
    div.stButton > button, div.stDownloadButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 50px; }
    .btn-borrar-rojo > div > button { background-color: #441111 !important; color: #ff9999 !important; border: 1px solid #662222 !important; height: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE LÓGICA ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_pro_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def interpretar_salud(valor, momento):
    if "Ayunas" in momento:
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"
    else:
        if valor < 140: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 140 <= valor <= 199: return "AMARILLO", "ELEVADO", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"

def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, "PACIENTE: LUIS RAFAEL QUEVEDO", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    headers = [("FECHA", 35), ("HORA", 30), ("MOMENTO", 55), ("VALOR", 30), ("ESTADO", 40)]
    for txt, w in headers: pdf.cell(w, 10, txt, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        c_slug, txt, _ = interpretar_salud(row['valor'], row['momento'])
        pdf.cell(35, 9, row['fecha'], 1)
        pdf.cell(30, 9, row['hora'], 1)
        pdf.cell(55, 9, row['momento'], 1)
        pdf.cell(30, 9, f"{row['valor']} mg/dL", 1)
        x, y = pdf.get_x(), pdf.get_y()
        pdf.cell(40, 9, f"      {txt}", 1, 1)
        pdf.dibujar_semaforo(x + 3, y + 2.5, c_slug)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 4. PANEL DE ALERTAS ---
def mostrar_panel_alertas(db, f_obj, pres_mensual):
    st.markdown("### 🔔 PANEL DE CONTROL")
    c1, c2, c3 = st.columns(3)
    with c1:
        citas = db.execute("SELECT doctor, fecha FROM citas").fetchall()
        hay = False
        for c in citas:
            try:
                f_c = datetime.strptime(c[1], '%Y-%m-%d').date()
                diff = (f_c - f_obj).days
                if 0 <= diff <= 3:
                    color = "#e74c3c" if diff == 0 else "#f1c40f"
                    st.markdown(f"<div class='alerta-card' style='border-left: 5px solid {color};'><strong>📅 CITA PRÓXIMA</strong><br>{c[0]}<br>Faltan {diff} días</div>", unsafe_allow_html=True)
                    hay = True
            except: pass
        if not hay: st.success("✅ Sin citas próximas")
    with c2:
        ult = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
        if ult:
            c_slug, txt, _ = interpretar_salud(ult[0], ult[1])
            c_hex = "#27ae60" if c_slug == "VERDE" else ("#f1c40f" if c_slug == "AMARILLO" else "#e74c3c")
            st.markdown(f"<div class='alerta-card' style='border-left: 5px solid {c_hex};'><strong>🩸 ÚLTIMA GLUCOSA</strong><br>{ult[0]} mg/dL<br>{txt}</div>", unsafe_allow_html=True)
    with c3:
        mes_act = f_obj.strftime("%m-%Y")
        gastos = db.execute("SELECT SUM(monto) FROM finanzas WHERE tipo='GASTO' AND mes=?", (mes_act,)).fetchone()[0] or 0
        gastos_val = abs(gastos)
        if pres_mensual > 0:
            porc = (gastos_val / pres_mensual)
            c_f = "#27ae60" if porc < 0.8 else "#e74c3c"
            # LÍNEA CORREGIDA PARA EVITAR ERROR DE CARÁCTER:
            st.markdown(f"<div class='alerta-card' style='border-left: 5px solid {c_f};'><strong>MONTO GASTADO</strong><br>{(porc*100):.1f}% usado<br>Resta: RD$ {max(0, pres_mensual-gastos_val):,.2f}</div>", unsafe_allow_html=True)

# --- 5. LÓGICA DE NAVEGACIÓN ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    _, col_log, _ = st.columns([1,1,1])
    with col_log:
        with st.form("login"):
            pwd = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("ACCEDER"):
                if pwd == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("Incorrecto")
    st.stop()

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
pres_mensual = res_conf[0] if res_conf else 0.0

with st.sidebar:
    st.markdown("## 🌐 MENU")
    menu = st.radio("NAVEGACIÓN", ["🏠 INICIO", "💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("SALIR"): 
        del st.session_state["password_correct"]
        st.rerun()

if menu == "🏠 INICIO":
    st.title(f"Bienvenido, Sr. Quevedo")
    st.info(f"📅 {f_str} | 🕒 {h_str}")
    mostrar_panel_alertas(db, f_obj, pres_mensual)

elif menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    total = df_f['monto'].sum() if not df_f.empty else 0.0
    st.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1>RD$ {total:,.2f}</h1></div>", unsafe_allow_html=True)
    with st.form("f_mov", clear_on_submit=True):
        c1, c2, c3 = st.columns([1,1,2])
        tipo = c1.selectbox("Tipo", ["GASTO", "INGRESO"])
        fec = c2.date_input("Fecha", value=f_obj)
        cat = c3.text_input("Categoría").upper()
        det = st.text_input("Detalle").upper()
        mon = st.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            m_f = -mon if tipo == "GASTO" else mon
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (fec.strftime("%d/%m/%Y"), fec.strftime("%m-%Y"), tipo, cat, det, m_f))
            db.commit(); st.rerun()
    if not df_f.empty: st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)

elif menu == "🩺 SALUD":
    st.title("🩺 Control Médico")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS"])
    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.download_button("📥 DESCARGAR REPORTE PDF", generar_pdf_salud(df_g), f"Salud_{f_str}.pdf")
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark"), use_container_width=True)
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']].style.apply(lambda r: [interpretar_salud(r['valor'], r['momento'])[2]]*4, axis=1), use_container_width=True)
        with st.form("f_glu", clear_on_submit=True):
            v = st.number_input("Valor", min_value=0)
            m = st.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR MEDICIÓN"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()
    with t2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows(): st.info(f"💊 {r['nombre']} - {r['dosis']} ({r['horario']})")
        with st.form("f_meds"):
            n = st.text_input("Medicina").upper()
            d = st.text_input("Dosis").upper()
            h = st.text_input("Horario").upper()
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()
    with t3:
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        st.table(df_c[['doctor', 'fecha', 'motivo']])
        with st.form("f_citas"):
            doc = st.text_input("Doctor").upper(); fec_c = st.date_input("Fecha"); mot = st.text_input("Motivo").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec_c), mot)); db.commit(); st.rerun()

elif menu == "📝 BITÁCORA":
    st.title("📝 Notas Personales")
    n = st.text_area("Nota:", height=150)
    if st.button("💾 GUARDAR"):
        with open("nexus_notas.txt", "a", encoding="utf-8") as f: f.write(f"[{f_str}]: {n}\n\n")
        st.rerun()
    if os.path.exists("nexus_notas.txt"):
        st.text_area("Historial:", open("nexus_notas.txt", "r", encoding="utf-8").read(), height=300)

elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes")
    np = st.number_input("Presupuesto Mensual RD$", value=float(pres_mensual))
    if st.button("GUARDAR"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (np,))
        db.commit(); st.success("¡Guardado!"); st.rerun()
