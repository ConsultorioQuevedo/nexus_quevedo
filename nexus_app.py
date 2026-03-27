import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import urllib.parse
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide")

# --- ESTILOS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stForm { background-color: #1c2128; border-radius: 10px; padding: 20px; border: 1px solid #30363d; }
    .stButton>button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.title("🌐 ACCESO NEXUS")
    with st.form("login"):
        pwd = st.text_input("Contraseña:", type="password")
        if st.form_submit_button("Entrar"):
            if pwd == "admin123":
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Incorrecto")
    st.stop()

# --- FUNCIONES BASE ---
def obtener_tiempo():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y")

def conectar():
    conn = sqlite3.connect("quevedo_db.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    conn.commit()
    return conn

db_conn = conectar()
db = db_conn.cursor()
f_hoy, h_ahora, m_actual = obtener_tiempo()

# --- NAVEGACIÓN ---
with st.sidebar:
    st.title("🌐 NEXUS")
    st.write(f"📅 {f_hoy}")
    menu = st.radio("MENÚ", ["🩺 SALUD", "💰 FINANZAS", "💊 MEDICINAS", "📝 NOTAS", "⚙️ RESET"])

# --- SALUD (CON WHATSAPP Y BORRADO) ---
if menu == "🩺 SALUD":
    st.header("Control de Glucosa")
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db_conn)
    
    if not df_g.empty:
        col1, col2 = st.columns(2)
        with col1:
            u = df_g.iloc[0]
            texto_wa = f"Mi glucosa hoy: {u['valor']} mg/dL ({u['momento']}) - {u['fecha']}"
            st.link_button("📲 WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(texto_wa)}")
        with col2:
            if st.button("🗑️ BORRAR ÚLTIMO"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                db_conn.commit()
                st.rerun()
        
        st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True))
        st.dataframe(df_g[['fecha', 'momento', 'valor']], use_container_width=True)

    with st.form("f_g"):
        val = st.number_input("Valor:", min_value=0)
        mom = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
        if st.form_submit_button("Guardar"):
            db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_hoy, h_ahora, mom, val))
            db_conn.commit(); st.rerun()

# --- FINANZAS (CON BORRADO) ---
elif menu == "💰 FINANZAS":
    st.header("Finanzas RD$")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db_conn)
    
    if not df_f.empty:
        if st.button("🗑️ BORRAR ÚLTIMO MOVIMIENTO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)")
            db_conn.commit(); st.rerun()
            
        st.metric("Balance Disponible", f"RD$ {df_f['monto'].sum():,.2f}")
        st.dataframe(df_f[['fecha', 'tipo', 'detalle', 'monto']], use_container_width=True)

    with st.form("f_f"):
        tipo = st.selectbox("Tipo", ["GASTO", "INGRESO"])
        det = st.text_input("Detalle:").upper()
        mon = st.number_input("Monto:", min_value=0.0)
        if st.form_submit_button("Registrar"):
            m_final = -mon if tipo == "GASTO" else mon
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, detalle, monto) VALUES (?,?,?,?,?)", (f_hoy, m_actual, tipo, det, m_final))
            db_conn.commit(); st.rerun()

# --- MEDICINAS (CON BORRADO INDIVIDUAL) ---
elif menu == "💊 MEDICINAS":
    st.header("Medicamentos")
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", db_conn)
    for _, r in df_m.iterrows():
        c1, c2 = st.columns([4,1])
        c1.warning(f"{r['nombre']} - {r['dosis']} ({r['horario']})")
        if c2.button("🗑️", key=f"m_{r['id']}"):
            db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],))
            db_conn.commit(); st.rerun()

    with st.form("f_m"):
        nom = st.text_input("Nombre:").upper()
        dos = st.text_input("Dosis:").upper()
        hor = st.text_input("Horario:").upper()
        if st.form_submit_button("Añadir"):
            db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (nom, dos, hor))
            db_conn.commit(); st.rerun()

# --- NOTAS ---
elif menu == "📝 NOTAS":
    st.header("Bitácora")
    if st.button("Borrar Notas"):
        if os.path.exists("notas.txt"): os.remove("notas.txt")
        st.rerun()
    n_txt = st.text_area("Escribir:")
    if st.button("Guardar"):
        with open("notas.txt", "a") as f: f.write(f"{f_hoy}: {n_txt}\n")
        st.rerun()
    if os.path.exists("notas.txt"):
        st.text(open("notas.txt", "r").read())

# --- RESET ---
elif menu == "⚙️ RESET":
    if st.button("⚠️ ELIMINAR TODA LA DATA"):
        for t in ["glucosa", "finanzas", "medicamentos"]: db.execute(f"DELETE FROM {t}")
        db_conn.commit(); st.rerun()

st.write("---")
st.caption("Nexus Quevedo v1.0")
