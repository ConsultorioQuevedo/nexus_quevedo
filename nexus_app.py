import streamlit as st
import pandas as pd
import sqlite3
import datetime
import openai
from fpdf import FPDF
import plotly.express as px

# --- CONFIGURACIÓN ---
openai.api_key = "TU_API_KEY_AQUI"
st.set_page_config(page_title="Nexus AI - Final Edition", layout="wide")

DB_FILE = "nexus_intelligent.db"

def query_db(query, params=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

def init_db():
    query_db('''CREATE TABLE IF NOT EXISTS salud_glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS finanzas_movs (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, categoria TEXT)''')

init_db()

# --- LÓGICA DEL SEMÁFORO ---
def semaforo_glucosa(val):
    if val < 70: return "background-color: #f8d7da; color: #721c24;" # Hipoglucemia (Rojo)
    if 70 <= val <= 130: return "background-color: #d4edda; color: #155724;" # Normal (Verde)
    if 130 < val <= 180: return "background-color: #fff3cd; color: #856404;" # Elevada (Amarillo)
    return "background-color: #f8d7da; color: #721c24;" # Muy alta (Rojo)

# --- INTERFAZ ---
st.title("🛡️ Nexus: Sistema Soberano de Control")
st.markdown("---")

menu = st.sidebar.radio("Navegación", ["🏠 Dashboard", "💰 Finanzas", "🏥 Salud", "🤖 Motor de IA"])

# --- 1. DASHBOARD ---
if menu == "🏠 Dashboard":
    st.subheader("Panel General")
    c1, c2 = st.columns(2)
    with c1:
        st.info("📊 Salud")
        ult = query_db("SELECT valor FROM salud_glucosa ORDER BY id DESC LIMIT 1")
        if ult: st.metric("Última Glucosa", f"{ult[0][0]} mg/dL")
    with c2:
        st.success("💸 Finanzas")
        res = query_db("SELECT tipo, monto FROM finanzas_movs")
        if res:
            df = pd.DataFrame(res, columns=["tipo", "monto"])
            bal = df[df['tipo']=='ingreso']['monto'].sum() - df[df['tipo']=='gasto']['monto'].sum()
            st.metric("Balance", f"${bal:,.2f}")

# --- 2. FINANZAS (CON BOTÓN DE BORRADO) ---
elif menu == "💰 Finanzas":
    st.header("Módulo Financiero")
    col1, col2 = st.columns([1, 2])
    with col1:
        t = st.radio("Tipo", ["ingreso", "gasto"], horizontal=True)
        m = st.number_input("Monto", min_value=0.0)
        c = st.selectbox("Categoría", ["Salud", "Comida", "Sueldo", "Otros"])
        if st.button("Registrar"):
            query_db("INSERT INTO finanzas_movs VALUES(NULL, ?, ?, ?, ?)", (str(datetime.date.today()), t, m, c))
            st.rerun()
    with col2:
        res_f = query_db("SELECT * FROM finanzas_movs ORDER BY id DESC")
        if res_f:
            df_f = pd.DataFrame(res_f, columns=["id", "Fecha", "Tipo", "Monto", "Categoría"])
            st.dataframe(df_f[["Fecha", "Tipo", "Monto", "Categoría"]], use_container_width=True)
            with st.expander("🗑️ Gestionar Movimientos"):
                for _, r in df_f.iterrows():
                    col_a, col_b = st.columns([3, 1])
                    col_a.write(f"{r['Fecha']} | {r['Tipo']} | ${r['Monto']}")
                    if col_b.button("Borrar", key=f"f_{r['id']}"):
                        query_db("DELETE FROM finanzas_movs WHERE id=?", (r['id'],))
                        st.rerun()

# --- 3. SALUD (CON SEMÁFORO CORREGIDO) ---
elif menu == "🏥 Salud":
    st.header("Módulo Médico")
    t1, t2, t3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])

    with t1:
        v = st.number_input("Medición mg/dL", value=110.0)
        if st.button("Guardar Glucosa"):
            query_db("INSERT INTO salud_glucosa VALUES(NULL, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v, "Manual"))
            st.rerun()
        res_g = query_db("SELECT fecha, valor FROM salud_glucosa ORDER BY id DESC")
        if res_g:
            df_g = pd.DataFrame(res_g, columns=["Fecha", "Valor"])
            # Aplicación del SEMÁFORO
            st.dataframe(df_g.style.map(semaforo_glucosa, subset=["Valor"]), use_container_width=True)

    with t2:
        m_n = st.text_input("Nombre Med")
        m_d = st.text_input("Dosis")
        if st.button("Añadir Med"):
            query_db("INSERT INTO salud_meds VALUES(NULL, ?, ?)", (m_n, m_d))
            st.rerun()
        res_m = query_db("SELECT id, nombre, dosis FROM salud_meds")
        if res_m:
            df_m = pd.DataFrame(res_m, columns=["id", "Nombre", "Dosis"])
            st.table(df_m[["Nombre", "Dosis"]])
            for _, r in df_m.iterrows():
                if st.button(f"Quitar {r['Nombre']}", key=f"m_{r['id']}"):
                    query_db("DELETE FROM salud_meds WHERE id=?", (r['id'],))
                    st.rerun()

    with t3:
        f_c = st.date_input("Fecha")
        d_c = st.text_input("Doctor")
        if st.button("Agendar"):
            query_db("INSERT INTO salud_citas VALUES(NULL, ?, ?)", (str(f_c), d_c))
            st.rerun()
        res_c = query_db("SELECT id, fecha, doctor FROM salud_citas ORDER BY fecha ASC")
        if res_c:
            df_c = pd.DataFrame(res_c, columns=["id", "Fecha", "Doctor"])
            st.dataframe(df_c[["Fecha", "Doctor"]], use_container_width=True)
            for _, r in df_c.iterrows():
                if st.button(f"Borrar Cita {r['Fecha']}", key=f"c_{r['id']}"):
                    query_db("DELETE FROM salud_citas WHERE id=?", (r['id'],))
                    st.rerun()

# --- 4. MOTOR DE IA ---
elif menu == "🤖 Motor de IA":
    st.header("Análisis Nexus")
    if st.button("Generar Reporte"):
        st.write("Reporte listo para análisis...")
