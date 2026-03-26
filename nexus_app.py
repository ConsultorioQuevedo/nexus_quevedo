import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import os
from fpdf import FPDF

# --- 1. CLASE PDF PROFESIONAL ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(120)
        # PIE DE PÁGINA SOLICITADO
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- 2. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117; }
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; margin-bottom: 20px;
    }
    .neon-verde { color: #40E0D0; font-weight: 800; font-size: 2rem; }
    .neon-rojo { color: #FF7F50; font-weight: 800; font-size: 2rem; }
    .stButton > button { border-radius: 10px; font-weight: 700; height: 45px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES CORE (TIEMPO Y DB) ---
def obtener_fecha_hora():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def gestionar_db():
    conn = sqlite3.connect("nexus_ordenado.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

db = gestionar_db()
f_s, h_s, mes_s, f_o = obtener_fecha_hora()

# --- 4. SEGURIDAD ---
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align:center; color:white;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        if st.text_input("Clave de Acceso:", type="password") == "admin123" and st.form_submit_button("ENTRAR"):
            st.session_state["auth"] = True; st.rerun()
    st.stop()

# --- 5. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("🌐 MENÚ NEXUS")
    menu = st.radio("", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    if st.button("CERRAR SESIÓN"): del st.session_state["auth"]; st.rerun()

# --- 6. MÓDULO: FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión de Capital")
    res = db.execute("SELECT valor FROM config WHERE param='meta'").fetchone()
    meta_val = res[0] if res else 0.0
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    total = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_s)]['monto'].sum()) if not df_f.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='balance-box'><h3>Capital Total</h3><div class='neon-verde'>RD$ {total:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='balance-box'><h3>Gastos Mes</h3><div class='neon-rojo'>RD$ {gastos:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='balance-box'><h3>Meta Fija</h3><div style='color:#58a6ff; font-size:2rem; font-weight:800;'>RD$ {meta_val:,.2f}</div></div>", unsafe_allow_html=True)

    with st.form("registro_p"):
        st.subheader("Nuevo Movimiento")
        col_t, col_d, col_m = st.columns(3)
        t_m = col_t.selectbox("Tipo", ["GASTO", "INGRESO"])
        d_m = col_d.text_input("Detalle").upper()
        m_m = col_m.number_input("Monto RD$")
        if st.form_submit_button("REGISTRAR"):
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, detalle, monto) VALUES (?,?,?,?,?)", (f_s, mes_s, t_m, d_m, -m_m if t_m=="GASTO" else m_m))
            db.commit(); st.rerun()

    for _, r in df_f.iterrows():
        ct, cd = st.columns([9,1])
        ct.info(f"{r['fecha']} | {r['detalle']} | RD$ {r['monto']:,.2f}")
        if cd.button("🗑️", key=f"f_{r['id']}"):
            db.execute("DELETE FROM finanzas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- 7. MÓDULO: SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control Médico")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])
    
    with t1:
        dfg = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not dfg.empty:
            st.plotly_chart(px.line(dfg.iloc[::-1], x='hora', y='valor', template="plotly_dark"), use_container_width=True)
        with st.form("g_form"):
            v, m = st.number_input("Valor:"), st.selectbox("Momento:", ["Ayunas", "Cena"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_s, h_s, m, v)); db.commit(); st.rerun()

    with t2:
        dfm = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in dfm.iterrows():
            ct, cb = st.columns([9,1]); ct.warning(f"💊 {r['nombre']} | {r['dosis']}")
            if cb.button("🗑️", key=f"m_{r['id']}"): db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()

    with t3:
        dfc = pd.read_sql_query("SELECT * FROM citas", db)
        for _, r in dfc.iterrows():
            ct, cb = st.columns([9,1]); ct.error(f"📅 {r['fecha']} | {r['doctor']}")
            if cb.button("🗑️", key=f"c_{r['id']}"): db.execute("DELETE FROM citas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- 8. MÓDULO: BITÁCORA (ORDENADO Y COMPLETO) ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora Personal")
    
    nota_texto = st.text_area("Nueva nota:", height=150)
    if st.button("💾 GUARDAR NOTA"):
        if nota_texto.strip():
            with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_s} {h_s}]: {nota_texto.strip()}\n\n")
            st.success("Nota almacenada."); st.rerun()

    st.markdown("---")
    
    if os.path.exists("nexus_notas.txt"):
        with open("nexus_notas.txt", "r", encoding="utf-8") as f:
            contenido = f.read()
    else: contenido = ""

    if contenido:
        # BOTONES ALINEADOS SEGÚN SOLICITUD
        c_pdf, c_del, c_esp = st.columns([1, 1, 2])
        
        with c_pdf:
            pdf_gen = PDF()
            pdf_gen.add_page()
            pdf_gen.set_font("Arial", 'B', 16); pdf_gen.cell(190, 10, "NOTAS NEXUS", ln=True, align='C'); pdf_gen.ln(10)
            pdf_gen.set_font("Arial", '', 12); pdf_gen.multi_cell(190, 8, contenido)
            st.download_button("📄 GENERAR PDF", pdf_gen.output(dest='S').encode('latin-1', errors='replace'), "Bitacora.pdf")

        with c_del:
            if st.button("🗑️ ELIMINAR TODO"):
                if os.path.exists("nexus_notas.txt"): os.remove("nexus_notas.txt")
                st.rerun()

        st.text_area("Historial de Notas:", contenido, height=300)
    else:
        st.info("No hay notas.")
