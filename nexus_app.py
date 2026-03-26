import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
from fpdf import FPDF

# --- CLASE ESPECIAL PARA EL PDF ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- 1. CONFIGURACIÓN VISUAL PRO (FORZADA) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117 !important; }

    /* Tarjetas Modernas */
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22 !important; 
        border-radius: 25px !important; 
        border: 1px solid #30363d !important; 
        padding: 30px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important;
        margin-bottom: 25px !important;
    }
    
    .balance-box h3 { color: #8b949e !important; font-size: 13px !important; text-transform: uppercase !important; letter-spacing: 2px !important; margin-bottom: 10px !important; }

    /* Botones Premium */
    div.stButton > button, div.stDownloadButton > button { 
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%) !important;
        color: #f0f6fc !important; border: 1px solid #30363d !important; border-radius: 15px !important; 
        font-weight: 700 !important; height: 45px !important; width: 100% !important; transition: 0.3s all ease !important;
    }
    div.stButton > button:hover { border-color: #58a6ff !important; transform: translateY(-2px) !important; }
    
    /* Botón Rojo para Borrar (Pequeño) */
    .btn-borrar button {
        background: #21262d !important;
        color: #ff7f50 !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        font-size: 12px !important;
        height: 30px !important;
    }

    /* Colores Neón */
    .neon-verde { color: #40E0D0 !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    .neon-rojo { color: #FF7F50 !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES CORE ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_pro_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tomas_diarias (fecha TEXT, medicina_id INTEGER, PRIMARY KEY (fecha, medicina_id))')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- 3. SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 50px; font-weight:800; color:white;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    _, col_b, _ = st.columns([1,1.5,1])
    with col_b:
        with st.form("login"):
            pwd = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("ACCEDER"):
                if pwd == "admin123": st.session_state["password_correct"] = True; st.rerun()
                else: st.error("❌")
    st.stop()

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 MENU</h2>", unsafe_allow_html=True)
    menu = st.radio("", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    if st.button("CERRAR SESIÓN"): del st.session_state["password_correct"]; st.rerun()

# --- 5. LÓGICA DE MÓDULOS ---

if menu == "💰 FINANZAS":
    st.title("💰 Finanzas")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='balance-box'><h3>Balance Actual</h3><div class='neon-verde'>RD$ {disponible:,.2f}</div></div>", unsafe_allow_html=True)
    
    with st.form("f_fin", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo", ["GASTO", "INGRESO"])
        f_mov = col2.date_input("Fecha", value=f_obj)
        cat = st.text_input("Categoría").upper()
        det = st.text_input("Detalle").upper()
        monto = st.number_input("Monto RD$:", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_mov.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, m_real))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.write("### Últimos Movimientos (Click en borrar para corregir)")
        for idx, row in df_f.head(10).iterrows():
            col_d, col_b = st.columns([9, 1])
            col_d.write(f"**{row['fecha']}** | {row['tipo']} | {row['detalle']} | **RD$ {row['monto']:,.2f}**")
            if col_b.button("🗑️", key=f"del_fin_{row['id']}"):
                db.execute("DELETE FROM finanzas WHERE id = ?", (row['id'],)); db.commit(); st.rerun()

elif menu == "🩺 SALUD":
    st.title("🩺 Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        with st.form("f_gluc", clear_on_submit=True):
            v = st.number_input("Valor:", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Antes de dormir"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()
        
        if not df_g.empty:
            for idx, row in df_g.head(5).iterrows():
                col_d, col_b = st.columns([9, 1])
                col_d.write(f"📅 {row['fecha']} - {row['momento']}: **{row['valor']} mg/dL**")
                if col_b.button("🗑️", key=f"del_glu_{row['id']}"):
                    db.execute("DELETE FROM glucosa WHERE id = ?", (row['id'],)); db.commit(); st.rerun()

    with t2:
        st.write("### Mis Medicamentos")
        df_meds = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, m in df_meds.iterrows():
            c_txt, c_del = st.columns([8, 2])
            c_txt.write(f"💊 **{m['nombre']}** ({m['dosis']}) - {m['horario']}")
            if c_del.button("BORRAR 💊", key=f"del_med_{m['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id = ?", (m['id'],)); db.commit(); st.rerun()
        
        with st.form("add_med", clear_on_submit=True):
            n, d, h = st.text_input("Nombre").upper(), st.text_input("Dosis").upper(), st.text_input("Horario").upper()
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()

    with t3:
        st.write("### Citas Agendadas")
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        for _, c in df_c.iterrows():
            c_txt, c_del = st.columns([8, 2])
            c_txt.write(f"📅 {c['fecha']} | **{c['doctor']}** | {c['motivo']}")
            if c_del.button("BORRAR 📅", key=f"del_cit_{c['id']}"):
                db.execute("DELETE FROM citas WHERE id = ?", (c['id'],)); db.commit(); st.rerun()

        with st.form("f_citas", clear_on_submit=True):
            doc, fec, mot = st.text_input("Doctor").upper(), st.date_input("Fecha"), st.text_input("Motivo").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot)); db.commit(); st.rerun()

elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    nota = st.text_area("Nota:", height=150)
    if st.button("GUARDAR"):
        with open("nexus_notas.txt", "a", encoding="utf-8") as f: f.write(f"[{f_str}]: {nota}\n\n")
        st.success("Nota Guardada")
