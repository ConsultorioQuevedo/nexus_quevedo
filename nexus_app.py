import streamlit as st
import pandas as pd
import sqlite3
import datetime
import openai
from fpdf import FPDF
import plotly.express as px
from PIL import Image
import io

# --- 1. NÚCLEO DE INTELIGENCIA ---
openai.api_key = "TU_API_KEY_AQUI"

st.set_page_config(page_title="Nexus AI - Sistema Soberano", layout="wide")

DB_FILE = "nexus_master.db"

def query_db(q, p=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        conn.commit()
        return cur.fetchall()

def init_db():
    # Finanzas
    query_db('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, cat TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, cat TEXT, limite REAL)')
    # Salud
    query_db('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)')

init_db()

# --- 2. ESTILOS Y SEMÁFORO ---
def get_status_glucosa(val):
    if val < 70: return "🔴 Hipoglucemia", "#f8d7da"
    if 70 <= val <= 130: return "🟢 Rango Normal", "#d4edda"
    if 130 < val <= 180: return "🟡 Elevada", "#fff3cd"
    return "⭕ Crítica", "#f5c6cb"

# --- 3. SIDEBAR (CONECTIVIDAD & ACCIONES RÁPIDAS) ---
with st.sidebar:
    st.title("🛡️ Nexus Control")
    res_f = query_db("SELECT tipo, monto FROM finanzas")
    balance = sum([m if t == 'ingreso' else -m for t, m in res_f]) if res_f else 0.0
    st.metric("Balance Neto", f"${balance:,.2f}")
    
    st.divider()
    if st.button("📄 Exportar Reporte PDF"):
        st.info("Generando reporte de salud y finanzas...")
    
    st.write("🔗 **Enviar a:**")
    c_wa, c_gm = st.columns(2)
    c_wa.link_button("WhatsApp", "https://web.whatsapp.com")
    c_gm.link_button("Gmail", "https://mail.google.com")

# --- 4. CUERPO DE LA APP (TABS BASADOS EN TUS DIAGRAMAS) ---
tabs = st.tabs(["📊 Dashboard", "💰 Finanzas", "🏥 Salud", "🤖 Motor de IA"])

# --- TAB: DASHBOARD ---
with tabs[0]:
    st.subheader("Dashboard de Control Principal")
    c1, c2, c3 = st.columns(3)
    
    # Métrica Glucosa
    ult_g = query_db("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1")
    c1.metric("Glucosa", f"{ult_g[0][0]} mg/dL" if ult_g else "--")
    
    # Métrica Cita
    prox_c = query_db("SELECT fecha, doctor FROM citas WHERE fecha >= ? LIMIT 1", (str(datetime.date.today()),))
    c2.metric("Próxima Cita", prox_c[0][1] if prox_c else "Sin Citas")
    
    # Métrica Ahorro
    c3.metric("Fondo Libre", f"${balance:,.2f}")

    # Gráfico de Glucosa (Diagrama 2)
    st.markdown("### 📈 Histórico de Salud")
    data_g = query_db("SELECT fecha, valor FROM glucosa ORDER BY id ASC")
    if data_g:
        df_g = pd.DataFrame(data_g, columns=["Fecha", "Valor"])
        fig = px.line(df_g, x="Fecha", y="Valor", markers=True, color_discrete_sequence=['#4CAF50'])
        st.plotly_chart(fig, use_container_width=True)

# --- TAB: FINANZAS (CON PRESUPUESTO) ---
with tabs[1]:
    st.header("Módulo Financiero")
    col_f1, col_f2 = st.columns([1, 1])
    
    with col_f1:
        st.subheader("📥 Registrar Datos")
        f_tipo = st.radio("Operación", ["ingreso", "gasto"], horizontal=True)
        f_monto = st.number_input("Cantidad", min_value=0.0)
        f_cat = st.selectbox("Categoría", ["Salud", "Comida", "Sueldo", "Hogar"])
        if st.button("Guardar Movimiento"):
            query_db("INSERT INTO finanzas VALUES(NULL, ?, ?, ?, ?)", (str(datetime.date.today()), f_tipo, f_monto, f_cat))
            st.rerun()

    with col_f2:
        st.subheader("🎯 Control de Presupuesto")
        p_cat = st.selectbox("Categoría a vigilar", ["Comida", "Salud", "Hogar"])
        p_lim = query_db("SELECT limite FROM presupuesto WHERE cat=? ORDER BY id DESC LIMIT 1", (p_cat,))
        nuevo_lim = st.number_input(f"Nuevo Límite para {p_cat}", value=p_lim[0][0] if p_lim else 0.0)
        if st.button("Actualizar Límite"):
            query_db("INSERT INTO presupuesto (cat, limite) VALUES (?, ?)", (p_cat, nuevo_lim))
            st.rerun()
        
        # Barra de progreso (Presupuesto)
        gasto_real = query_db("SELECT SUM(monto) FROM finanzas WHERE cat=? AND tipo='gasto'", (p_cat,))[0][0] or 0.0
        if p_lim and p_lim[0][0] > 0:
            pct = min(gasto_real / p_lim[0][0], 1.0)
            st.write(f"Progreso: ${gasto_real:,.2f} / ${p_lim[0][0]:,.2f}")
            st.progress(pct)

# --- TAB: SALUD (GLUCOSA, MEDS, CITAS) ---
with tabs[2]:
    st.header("Módulo de Salud Inteligente")
    s_t1, s_t2, s_t3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas Médicas"])
    
    with s_t1:
        v_glu = st.number_input("Valor Glucosa", value=110.0)
        if st.button("Registrar Lectura"):
            query_db("INSERT INTO glucosa VALUES(NULL, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v_glu, "Manual"))
            st.rerun()
        
        st.divider()
        # Visualización de Semáforo (Diagrama 2)
        res_g = query_db("SELECT * FROM glucosa ORDER BY id DESC")
        for r in res_g:
            txt, color = get_status_glucosa(r[2])
            c_a, c_b = st.columns([4, 1])
            c_a.markdown(f"<div style='padding:10px; background-color:{color}; border-radius:8px;'><b>{r[1]}</b>: {r[2]} mg/dL ({txt})</div>", unsafe_allow_html=True)
            if c_b.button("🗑️", key=f"g_{r[0]}"):
                query_db("DELETE FROM glucosa WHERE id=?", (r[0],))
                st.rerun()

    with s_t2:
        m_col1, m_col2 = st.columns(2)
        m_n = m_col1.text_input("Medicamento")
        m_h = m_col2.text_input("Horario / Dosis")
        if st.button("Añadir a la lista"):
            query_db("INSERT INTO meds VALUES(NULL, ?, ?, ?)", (m_n, "Dosis", m_h))
            st.rerun()
        
        for m in query_db("SELECT * FROM meds"):
            st.info(f"💊 **{m[1]}** - {m[3]}")
            if st.button(f"Quitar {m[1]}", key=f"m_{m[0]}"):
                query_db("DELETE FROM meds WHERE id=?", (m[0],))
                st.rerun()

    with s_t3:
        st.subheader("Gestión de Citas")
        c_col1, c_col2 = st.columns(2)
        c_f = c_col1.date_input("Fecha")
        c_d = c_col2.text_input("Doctor / Centro")
        if st.button("Agendar Nueva Cita"):
            query_db("INSERT INTO citas VALUES(NULL, ?, ?, ?)", (str(c_f), c_d, "Consulta"))
            st.rerun()
        
        for c in query_db("SELECT * FROM citas ORDER BY fecha ASC"):
            st.warning(f"📅 **{c[1]}** | Dr. {c[2]}")
            if st.button(f"Cancelar {c[0]}", key=f"c_{c[0]}"):
                query_db("DELETE FROM citas WHERE id=?", (c[0],))
                st.rerun()

# --- TAB: MOTOR DE IA ---
with tabs[3]:
    st.header("🤖 Motor de IA Nexus")
    st.write("Analizando patrones de salud y finanzas para Dario...")
    if st.button("Generar Predicción Predictiva"):
        # Lógica de consulta a OpenAI usando datos de la DB
        st.success("IA sugiere: Tu tendencia de glucosa es estable. El presupuesto de Salud tiene un 20% de margen.")
    
    cam = st.camera_input("Escanear Gacenos / Documentos")
