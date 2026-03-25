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

# --- BASES DE DATOS ---
def iniciar_db():
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    conn.commit()
    return conn

db = iniciar_db()
zona = pytz.timezone('America/Santo_Domingo')
f_str = datetime.now(zona).strftime("%d/%m/%Y")
h_str = datetime.now(zona).strftime("%I:%M %p")

# --- MENÚ ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.write(f"📅 {f_str} | ⏰ {h_str}")
    menu = st.radio("MENÚ", ["💰 FINANZAS", "🩺 SALUD"])

# --- FINANZAS (CONEXIÓN DIRECTA) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    
    # Esta es la dirección que fuerza a Google a soltar los datos sin errores
    URL_EXPORT = "https://docs.google.com/spreadsheets/d/12jg8nHRUCJwwty0VcsbWFvTIpRcGLCITNKLevZ7Nwb8/export?format=csv&gid=0"
    
    try:
        df = pd.read_csv(URL_EXPORT)
        # Limpiamos los nombres de las columnas para evitar problemas de tildes
        df.columns = [c.strip().replace('Categoría', 'Categoria').replace('Categoría', 'Categoria').capitalize() for c in df.columns]
        
        st.success("✅ Conexión Exitosa con DB_NEXUS_FINANZAS")
        
        if 'Monto' in df.columns:
            df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0)
            total = df["Monto"].sum()
            st.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1 style='color:#2ecc71;'>RD$ {total:,.2f}</h1></div>", unsafe_allow_html=True)
        
        st.subheader("Historial de Movimientos")
        st.dataframe(df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error de acceso. Por favor, asegúrese de que el archivo esté compartido como 'Cualquier persona con el enlace puede editar'")

# --- SALUD (RESTAURADO COMPLETO) ---
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
            c1, c2 = st.columns([5, 1])
            c1.info(f"🩸 {r['fecha']} | {r['hora']} -> {r['valor']} mg/dL")
            if c2.button("Borrar", key=f"g_{r['id']}"):
                db.execute("DELETE FROM glucosa WHERE id=?", (r['id'],))
                db.commit(); st.rerun()

    with t2:
        st.subheader("💊 Registro de Medicamentos")
        with st.form("f_med"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("Nombre:")
            d = c2.text_input("Dosis:")
            h = c3.text_input("Horario:")
            if st.form_submit_button("AGREGAR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d.upper(), h.upper()))
                db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT id, nombre, dosis, horario FROM medicamentos", db)
        for i, r in df_m.iterrows():
            col1, col2 = st.columns([5, 1])
            col1.warning(f"💊 **{r['nombre']}** | {r['dosis']} | ⏰ {r['horario']}")
            if col2.button("Borrar", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],))
                db.commit(); st.rerun()
