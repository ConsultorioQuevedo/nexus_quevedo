import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import os
from fpdf import FPDF

# --- 1. MOTOR DE REPORTES PDF (Luis Rafael Quevedo) ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(120)
        self.cell(0, 10, 'Luis Rafael Quevedo - Nexus System', 0, 0, 'C')

# --- 2. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117; }
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; 
        padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.6);
    }
    .neon-verde { color: #40E0D0; font-weight: 800; font-size: 2.2rem; }
    .neon-rojo { color: #FF7F50; font-weight: 800; font-size: 2.2rem; }
    .stButton > button { border-radius: 10px; font-weight: 700; height: 48px; width: 100%; transition: 0.3s; }
    .stButton > button:hover { transform: scale(1.02); border: 1px solid #40E0D0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES CORE (TIEMPO RD Y DB) ---
def get_time_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y")

def init_db():
    conn = sqlite3.connect("nexus_master_v12.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

db = init_db()
f_s, h_s, mes_s = get_time_rd()

# --- 4. SEGURIDAD (CORRECCIÓN DEFINITIVA ERROR DE FOTO) ---
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align:center; color:white; margin-top:50px;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    with st.form("nexus_login"):
        clave = st.text_input("Ingrese Clave de Acceso:", type="password")
        # El st.form_submit_button es lo que elimina el error de la imagen
        acceder = st.form_submit_button("DESBLOQUEAR SISTEMA")
        if acceder:
            if clave == "admin123":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Clave Incorrecta")
    st.stop()

# --- 5. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("🌐 CONTROL PRO")
    menu = st.radio("", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    st.markdown("---")
    if st.button("CERRAR SESIÓN"):
        del st.session_state["auth"]
        st.rerun()

# --- 6. MÓDULO: FINANZAS (EL ORIGINAL) ---
if menu == "💰 FINANZAS":
    st.title("💰 Capital y Presupuesto")
    
    # Meta
    r_meta = db.execute("SELECT valor FROM config WHERE param='meta'").fetchone()
    meta = r_meta[0] if r_meta else 0.0
    
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    total_cap = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_s)]['monto'].sum()) if not df_f.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='balance-box'><h3>Capital</h3><div class='neon-verde'>RD$ {total_cap:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='balance-box'><h3>Gastos Mes</h3><div class='neon-rojo'>RD$ {gastos_mes:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='balance-box'><h3>Meta</h3><div style='color:#58a6ff; font-size:2.2rem; font-weight:800;'>RD$ {meta:,.2f}</div></div>", unsafe_allow_html=True)

    with st.form("reg_fin"):
        st.subheader("Registrar Movimiento")
        col1, col2, col3 = st.columns(3)
        tipo = col1.selectbox("Tipo", ["GASTO", "INGRESO"])
        det = col2.text_input("Detalle").upper()
        mon = col3.number_input("Monto RD$")
        if st.form_submit_button("GUARDAR"):
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, detalle, monto) VALUES (?,?,?,?,?)", 
                       (f_s, mes_s, tipo, det, -mon if tipo=="GASTO" else mon))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.subheader("Historial de Transacciones")
        for _, r in df_f.head(10).iterrows():
            col_a, col_b = st.columns([10, 1])
            col_a.info(f"{r['fecha']} | {r['detalle']} | RD$ {r['monto']:,.2f}")
            if col_b.button("🗑️", key=f"f_{r['id']}"):
                db.execute("DELETE FROM finanzas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- 7. MÓDULO: SALUD (GLUCOSA, MEDICAMENTOS, CITAS) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Gestión Médica")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS"])
    
    with t1:
        dfg = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not dfg.empty:
            st.plotly_chart(px.line(dfg.iloc[::-1], x='hora', y='valor', title="Nivel de Glucosa", template="plotly_dark"), use_container_width=True)
        with st.form("f_glu"):
            v = st.number_input("Valor:")
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Almuerzo", "Cena"])
            if st.form_submit_button("REGISTRAR GLUCOSA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_s, h_s, m, v))
                db.commit(); st.rerun()

    with t2:
        with st.form("f_med"):
            n, d, h = st.text_input("Medicamento"), st.text_input("Dosis"), st.text_input("Horario")
            if st.form_submit_button("AGREGAR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d, h))
                db.commit(); st.rerun()
        dfm = pd.read_sql_query("SELECT * FROM medicamentos", db)
        st.table(dfm[["nombre", "dosis", "horario"]])

    with t3:
        with st.form("f_cita"):
            doc, fec, mot = st.text_input("Doctor"), st.date_input("Fecha"), st.text_input("Motivo")
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc.upper(), str(fec), mot.upper()))
                db.commit(); st.rerun()
        dfc = pd.read_sql_query("SELECT * FROM citas", db)
        st.dataframe(dfc, use_container_width=True)

# --- 8. MÓDULO: BITÁCORA (BORRADO Y PDF REPARADO) ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Notas y Bitácora")
    nota_txt = st.text_area("Nueva nota:", height=150)
    if st.button("💾 GUARDAR"):
        if nota_txt.strip():
            with open("nexus_log.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_s} {h_s}]: {nota_txt.strip()}\n\n")
            st.success("Guardado."); st.rerun()

    st.markdown("---")
    if os.path.exists("nexus_log.txt"):
        with open("nexus_log.txt", "r", encoding="utf-8") as f:
            contenido = f.read()
    else: contenido = ""

    if contenido:
        cp, cb, _ = st.columns([1.5, 1.5, 4])
        with cp:
            rep = PDF()
            rep.add_page()
            rep.set_font("Arial", 'B', 16); rep.cell(190, 10, "BITÁCORA DE NOTAS", ln=True, align='C'); rep.ln(10)
            rep.set_font("Arial", '', 12); rep.multi_cell(190, 8, contenido)
            st.download_button("📄 EXPORTAR PDF", rep.output(dest='S').encode('latin-1', errors='replace'), "Bitacora_Quevedo.pdf")
        with cb:
            if st.button("🗑️ BORRAR TODO"):
                if os.path.exists("nexus_log.txt"): os.remove("nexus_log.txt")
                st.rerun()
        st.text_area("Historial:", contenido, height=350)
