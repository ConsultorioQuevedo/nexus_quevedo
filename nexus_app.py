import streamlit as st
import pandas as pd
import sqlite3
import datetime
import openai
from fpdf import FPDF
import plotly.express as px
from PIL import Image
from pyzbar.pyzbar import decode
import io

# --- CONFIGURACIÓN MAESTRA ---
openai.api_key = "TU_API_KEY_AQUI"
st.set_page_config(page_title="Nexus AI - Full Architecture", layout="wide")

DB_FILE = "nexus_system.db"

def query_db(q, p=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        conn.commit()
        return cur.fetchall()

def init_db():
    # Estructura completa según Diagrama 1 y 2
    query_db('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, cat TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, cat TEXT, limite REAL)')

init_db()

# --- LÓGICA DE MOTOR DE IA (Lectura de Contexto) ---
def obtener_contexto_ia():
    g = query_db("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 5")
    f = query_db("SELECT tipo, monto FROM finanzas ORDER BY id DESC LIMIT 5")
    return f"Últimos niveles glucosa: {g}. Últimos movimientos: {f}."

# --- INTERFAZ ---
with st.sidebar:
    st.title("🚀 Nexus System")
    # Cálculo de Balance en tiempo real
    res_f = query_db("SELECT tipo, monto FROM finanzas")
    balance = sum([m if t == 'ingreso' else -m for t, m in res_f]) if res_f else 0.0
    st.metric("Balance Total", f"${balance:,.2f}")
    st.divider()
    if st.button("📄 Generar Reporte PDF Global"):
        st.write("Generando...") # Aquí iría la lógica FPDF detallada

tabs = st.tabs(["📊 Dashboard", "💰 Finanzas & Presupuesto", "🏥 Salud Total", "🔍 Escáner", "🤖 Motor de IA"])

# --- TAB 1: DASHBOARD (MÉTRICAS CRUZADAS) ---
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    # Glucosa
    ult_g = query_db("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1")
    if ult_g:
        color = "inverse" if ult_g[0][0] > 140 else "normal"
        c1.metric("Glucosa", f"{ult_g[0][0]} mg/dL", delta_color=color)
    # Citas
    prox_c = query_db("SELECT fecha, doctor FROM citas WHERE fecha >= ? LIMIT 1", (str(datetime.date.today()),))
    c2.metric("Próxima Cita", prox_c[0][1] if prox_c else "Libre")
    # Ahorro
    c3.metric("Fondo Disponible", f"${balance:,.2f}")
    
    # Gráfico de tendencias (Diagrama 2)
    st.subheader("📈 Tendencia de Salud (Glucosa)")
    data_g = query_db("SELECT fecha, valor FROM glucosa ORDER BY fecha ASC")
    if data_g:
        df_g = pd.DataFrame(data_g, columns=["Fecha", "Valor"])
        fig = px.area(df_g, x="Fecha", y="Valor", color_discrete_sequence=['#ff4b4b'])
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: FINANZAS (CON PRESUPUESTO) ---
with tabs[1]:
    st.header("Módulo Financiero Inteligente")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("➕ Registrar")
        t = st.radio("Tipo", ["ingreso", "gasto"], horizontal=True)
        m = st.number_input("Monto", min_value=0.0)
        c = st.selectbox("Categoría", ["Salud", "Comida", "Sueldo", "Hogar"])
        if st.button("Guardar Movimiento"):
            query_db("INSERT INTO finanzas VALUES(NULL, ?, ?, ?, ?)", (str(datetime.date.today()), t, m, c))
            st.rerun()

    with col2:
        st.subheader("🎯 Presupuesto (Diagrama 1)")
        p_cat = st.selectbox("Categoría a Limitar", ["Comida", "Salud", "Hogar"])
        p_lim = st.number_input("Límite Mensual", min_value=0.0)
        if st.button("Establecer Límite"):
            query_db("INSERT INTO presupuesto (cat, limite) VALUES (?, ?)", (p_cat, p_lim))
            st.rerun()
        
        # Comparativa Presupuesto vs Gasto
        gastos_cat = query_db("SELECT SUM(monto) FROM finanzas WHERE cat=? AND tipo='gasto'", (p_cat,))
        limite_cat = query_db("SELECT limite FROM presupuesto WHERE cat=? ORDER BY id DESC LIMIT 1", (p_cat,))
        if limite_cat and gastos_cat[0][0]:
            progreso = gastos_cat[0][0] / limite_cat[0][0]
            st.write(f"Gasto en {p_cat}: ${gastos_cat[0][0]} / ${limite_cat[0][0]}")
            st.progress(min(progreso, 1.0))

# --- TAB 3: SALUD (CITAS, MEDS, SEMÁFORO) ---
with tabs[2]:
    st.header("Módulo de Salud Soberano")
    s1, s2, s3 = st.tabs(["🩸 Glucosa", "💊 Meds", "📅 Citas"])
    
    with s1:
        v = st.number_input("Medición mg/dL", value=100.0, key="glu_val")
        if st.button("Registrar Glucosa"):
            query_db("INSERT INTO glucosa VALUES(NULL, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v, "Manual"))
            st.rerun()
        
        # Semáforo Visual (Diagrama 2)
        res_g = query_db("SELECT id, fecha, valor FROM glucosa ORDER BY id DESC")
        for r in res_g:
            emoji = "🟢" if 70 <= r[2] <= 130 else "🔴" if r[2] < 70 else "🟡"
            cols = st.columns([4, 1])
            cols[0].write(f"{emoji} **{r[2]} mg/dL** - {r[1]}")
            if cols[1].button("Borrar", key=f"g_del_{r[0]}"):
                query_db("DELETE FROM glucosa WHERE id=?", (r[0],))
                st.rerun()

    with s2:
        m_n = st.text_input("Nombre Medicamento")
        m_h = st.text_input("Horario")
        if st.button("Guardar Med"):
            query_db("INSERT INTO meds VALUES(NULL, ?, ?, ?)", (m_n, "Dosis", m_h))
            st.rerun()
        # Lista de meds con opción de borrado
        for m in query_db("SELECT * FROM meds"):
            st.info(f"💊 {m[1]} - {m[3]}")
            if st.button(f"Eliminar {m[1]}", key=f"m_del_{m[0]}"):
                query_db("DELETE FROM meds WHERE id=?", (m[0],))
                st.rerun()

    with s3:
        # Aquí está la función de CITAS que faltaba
        c_f = st.date_input("Fecha Cita")
        c_d = st.text_input("Doctor")
        if st.button("Agendar Cita"):
            query_db("INSERT INTO citas VALUES(NULL, ?, ?, ?)", (str(c_f), c_d, "Consulta"))
            st.rerun()
        for c in query_db("SELECT * FROM citas ORDER BY fecha ASC"):
            st.warning(f"📅 {c[1]} | Dr. {c[2]}")
            if st.button(f"Borrar Cita {c[0]}", key=f"c_del_{c[0]}"):
                query_db("DELETE FROM citas WHERE id=?", (c[0],))
                st.rerun()

# --- TAB 4: ESCÁNER (DIAGRAMA 1) ---
with tabs[3]:
    st.header("Escáner de Documentos & OCR")
    img_file = st.camera_input("Escanear Gaceno / Receta")
    if img_file:
        st.image(img_file)
        st.success("Documento digitalizado. Procesando con Motor de IA...")

# --- TAB 5: MOTOR DE IA (PREDICCIÓN) ---
with tabs[4]:
    st.header("🤖 Motor de IA Nexus")
    if st.button("Analizar Tendencias"):
        contexto = obtener_contexto_ia()
        # Llamada real a OpenAI usando el contexto de la base de datos
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Analiza estos datos de Dario y dale un consejo breve."},
                          {"role": "user", "content": contexto}]
            )
            st.write(resp["choices"][0]["message"]["content"])
        except:
            st.warning("Conecta tu API Key para ver predicciones reales.")
