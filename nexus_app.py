import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
from fpdf import FPDF

# --- CLASE PDF ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117 !important; }
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22 !important; border-radius: 20px !important; 
        border: 1px solid #30363d !important; padding: 25px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important; margin-bottom: 20px !important;
    }
    div.stButton > button, div.stDownloadButton > button { 
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%) !important;
        color: #f0f6fc !important; border: 1px solid #30363d !important; border-radius: 12px !important; 
        font-weight: 700 !important; height: 45px !important; width: 100% !important;
    }
    .neon-verde { color: #40E0D0 !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    .neon-rojo { color: #FF7F50 !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    .del-btn { color: #ff4b4b !important; cursor: pointer; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES ---
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
    conn.commit()
    return conn

def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(190, 10, "REPORTE DE SALUD - QUEVEDO", ln=True, align='C'); pdf.ln(10)
    pdf.set_fill_color(30, 30, 30); pdf.set_text_color(255, 255, 255)
    cols = ["FECHA", "HORA", "MOMENTO", "VALOR"]
    for c in cols: pdf.cell(47, 10, c, 1, 0, 'C', True)
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, r in df.iterrows():
        pdf.cell(47, 9, str(r['fecha']), 1); pdf.cell(47, 9, str(r['hora']), 1)
        pdf.cell(47, 9, str(r['momento']), 1); pdf.cell(47, 9, f"{r['valor']} mg/dL", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1', errors='replace')

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color:white;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    _, col_b, _ = st.columns([1,1.2,1])
    with col_b:
        with st.form("login"):
            pwd = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("ENTRAR"):
                if pwd == "admin123": st.session_state["password_correct"] = True; st.rerun()
                else: st.error("Incorrecto")
    st.stop()

# --- NAVEGACIÓN ---
with st.sidebar:
    st.markdown("### 🌐 PANEL")
    menu = st.radio("", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    if st.button("SALIR"): del st.session_state["password_correct"]; st.rerun()

# --- MÓDULO FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Control Financiero")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    total = df_f['monto'].sum() if not df_f.empty else 0
    
    st.markdown(f"<div class='balance-box'><h3>Balance Total</h3><div class='neon-verde'>RD$ {total:,.2f}</div></div>", unsafe_allow_html=True)
    
    with st.form("f_mov", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t = c1.selectbox("Tipo", ["GASTO", "INGRESO"])
        f = c2.date_input("Fecha", f_obj)
        cat = st.text_input("Categoría").upper()
        det = st.text_input("Detalle").upper()
        m = st.number_input("Monto RD$:", min_value=0.0)
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            m_v = -m if t == "GASTO" else m
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f.strftime("%d/%m/%Y"), mes_str, t, cat, det, m_v))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.write("### Historial de Transacciones")
        for i, r in df_f.iterrows():
            col1, col2 = st.columns([9,1])
            col1.info(f"**{r['fecha']}** | {r['tipo']} | {r['detalle']} | **RD$ {r['monto']:,.2f}**")
            if col2.button("🗑️", key=f"f_{r['id']}"):
                db.execute("DELETE FROM finanzas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- MÓDULO SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark").update_traces(line_color='#40E0D0'), use_container_width=True)
            c1, c2 = st.columns(2)
            c1.download_button("📥 PDF", generar_pdf_salud(df_g), "Salud.pdf")
            u = df_g.iloc[0]
            msg = f"Reporte: {u['valor']} mg/dL ({u['momento']})"
            c2.link_button("📲 WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(msg)}")
            
            for i, r in df_g.head(5).iterrows():
                col1, col2 = st.columns([9,1])
                col1.success(f"{r['fecha']} - {r['momento']}: **{r['valor']} mg/dL**")
                if col2.button("🗑️", key=f"g_{r['id']}"):
                    db.execute("DELETE FROM glucosa WHERE id=?", (r['id'],)); db.commit(); st.rerun()

        with st.form("g_add"):
            v = st.number_input("Valor:", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Dormir"])
            if st.form_submit_button("GUARDAR TOMA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()

    with t2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for i, r in df_m.iterrows():
            col1, col2 = st.columns([9,1])
            col1.warning(f"💊 **{r['nombre']}** - {r['dosis']} ({r['horario']})")
            if col2.button("🗑️", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("m_add"):
            n, d, h = st.text_input("Nombre"), st.text_input("Dosis"), st.text_input("Horario")
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d, h)); db.commit(); st.rerun()

    with t3:
        df_c = pd.read_sql_query("SELECT * FROM citas", db)
        for i, r in df_c.iterrows():
            col1, col2 = st.columns([9,1])
            col1.error(f"📅 {r['fecha']} | {r['doctor']} | {r['motivo']}")
            if col2.button("🗑️", key=f"c_{r['id']}"):
                db.execute("DELETE FROM citas WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("c_add"):
            doc, fec, mot = st.text_input("Doctor"), st.date_input("Fecha"), st.text_input("Motivo")
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc.upper(), str(fec), mot.upper())); db.commit(); st.rerun()

# --- MÓDULO BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Notas Personales")
    nota = st.text_area("Escribe aquí:", height=200)
    if st.button("GUARDAR NOTA"):
        with open("nexus_bitacora.txt", "a", encoding="utf-8") as f:
            f.write(f"[{f_str} {h_str}]: {nota}\n\n")
        st.success("Nota almacenada")
    st.markdown("---")
    try:
        with open("nexus_bitacora.txt", "r", encoding="utf-8") as f:
            st.text_area("Historial:", f.read(), height=300)
    except: st.info("Sin notas")
