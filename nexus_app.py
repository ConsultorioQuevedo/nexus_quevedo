import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px

# --- CONFIGURACIÓN VISUAL NEXUS ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Contraseña Maestra:", type="password")
        if st.form_submit_button("ACCEDER"):
            if pwd == "admin123":
                st.session_state["password_correct"] = True
                st.rerun()
    st.stop()

# --- BASES DE DATOS ---
def iniciar_db():
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    conn.commit()
    return conn

db = iniciar_db()
zona = pytz.timezone('America/Santo_Domingo')
ahora = datetime.now(zona)
f_str = ahora.strftime("%d/%m/%Y")
h_str = ahora.strftime("%I:%M %p")

# --- MENÚ ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.write(f"📅 {f_str} | ⏰ {h_str}")
    menu = st.radio("MENÚ", ["💰 FINANZAS", "🩺 SALUD"])

# --- FINANZAS (ELIMINANDO ERRORES DE COLUMNAS) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    URL = "https://docs.google.com/spreadsheets/d/12jg8nHRUCJwwty0VcsbWFvTIpRcGLCITNKLevZ7Nwb8/export?format=csv"
    
    try:
        df = pd.read_csv(URL)
        # Ajuste para que no importe si hay tilde o no
        df.columns = [c.replace('Categoría', 'Categoria') for c in df.columns]
        
        st.success("✅ Conectado a DB_NEXUS_FINANZAS")
        
        # Balance
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
        st.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1 style='color:#2ecc71;'>RD$ {df['Monto'].sum():,.2f}</h1></div>", unsafe_allow_html=True)
        
        st.subheader("Registros en Google Sheets")
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error de columnas. Asegúrese de que en su Excel los títulos sean: Fecha, Mes, Tipo, Categoría, Detalle, Monto")

# --- SALUD (CON HORARIOS Y BORRADO) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS"])

    with t1:
        v = st.number_input("Nivel mg/dL:", min_value=0)
        if st.button("GUARDAR GLUCOSA"):
            db.execute("INSERT INTO glucosa (fecha, hora, valor) VALUES (?,?,?)", (f_str, h_str, v))
            db.commit(); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT fecha, hora, valor FROM glucosa ORDER BY id DESC", db))

    with t2:
        st.subheader("💊 Medicinas con Horario")
        with st.form("f_med"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Nombre:")
            d = c2.text_input("Dosis:")
            h = c3.text_input("Horario:") # Campo restaurado
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT id, nombre, dosis, horario FROM medicamentos", db)
        for i, r in df_m.iterrows():
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"**{r['nombre']}** - {r['dosis']} ({r['horario']})")
            if col_b.button("Borrar", key=f"del_{r['id']}"): # Botón de borrado restaurado
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],))
                db.commit(); st.rerun()
