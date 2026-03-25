import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz

# --- CONFIGURACIÓN VISUAL NEXUS ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
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

# --- BASES DE DATOS LOCALES ---
def iniciar_db():
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, valor INTEGER)')
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

# --- FINANZAS (SOLUCIÓN DEFINITIVA DE COLUMNAS) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    URL = "https://docs.google.com/spreadsheets/d/12jg8nHRUCJwwty0VcsbWFvTIpRcGLCITNKLevZ7Nwb8/export?format=csv"
    
    try:
        df = pd.read_csv(URL)
        
        # --- EL CAMBIO EN "OTRO LUGAR" ---
        # Forzamos a que el código ignore tildes y mayúsculas en los títulos
        df.columns = [c.strip().capitalize() for c in df.columns]
        if 'Categoría' in df.columns or 'Categoria' in df.columns:
            df.rename(columns={'Categoría': 'Categoria'}, inplace=True)
        
        st.success("✅ Conectado con éxito")
        
        # Balance
        if 'Monto' in df.columns:
            df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
            st.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1 style='color:#2ecc71;'>RD$ {df['Monto'].sum():,.2f}</h1></div>", unsafe_allow_html=True)
        
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error("Error al leer los datos. Verifique que el enlace en Secrets sea el correcto.")

# --- SALUD (CON BOTONES DE BORRADO Y HORARIOS) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS"])

    with t1:
        v = st.number_input("Nivel mg/dL:", min_value=0)
        if st.button("GUARDAR GLUCOSA"):
            db.execute("INSERT INTO glucosa (fecha, hora, valor) VALUES (?,?,?)", (f_str, h_str, v))
            db.commit(); st.rerun()
        
        df_g = pd.read_sql_query("SELECT id, fecha, hora, valor FROM glucosa ORDER BY id DESC", db)
        for i, r in df_g.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"🩸 {r['fecha']} - {r['hora']}: **{r['valor']} mg/dL**")
            if c2.button("Borrar", key=f"g_{r['id']}"):
                db.execute("DELETE FROM glucosa WHERE id=?", (r['id'],))
                db.commit(); st.rerun()

    with t2:
        st.subheader("💊 Medicinas con Horario")
        with st.form("f_med"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Nombre:")
            d = c2.text_input("Dosis:")
            h = c3.text_input("Horario:")
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d.upper(), h.upper()))
                db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT id, nombre, dosis, horario FROM medicamentos", db)
        for i, r in df_m.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.write(f"💊 **{r['nombre']}** - {r['dosis']} ({r['horario']})")
            if col2.button("Borrar", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],))
                db.commit(); st.rerun()
