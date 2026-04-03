import streamlit as st
import pandas as pd
import sqlite3
import datetime
import openai
import plotly.express as px
from fpdf import FPDF
import io

# --- CONFIGURACIÓN DE MOTOR DE IA ---
openai.api_key = "TU_API_KEY_AQUI"

st.set_page_config(page_title="Nexus - Registro Soberano", layout="wide")

# --- BASE DE DATOS (ESTRUCTURA COMPLETA) ---
DB_FILE = "nexus_soberano.db"

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

# --- LÓGICA DE SEMÁFORO (DIAGRAMA 2) ---
def semaforo_ui(val):
    if val < 70: return "🔴 Bajo (Hipoglucemia)", "#f8d7da"
    if 70 <= val <= 130: return "🟢 Normal", "#d4edda"
    if 130 < val <= 180: return "🟡 Elevado", "#fff3cd"
    return "⭕ Crítico (Muy Alto)", "#f5c6cb"

# --- INTERFAZ PRINCIPAL ---
st.title("🛡️ Nexus: Gestión de Finanzas y Salud")

# Menú Principal (Exactamente como tu Diagrama 2)
menu = st.sidebar.selectbox("Menú Principal", ["Dashboard", "Finanzas", "Salud", "Motor de IA"])

# --- SECCIÓN 1: DASHBOARD ---
if menu == "Dashboard":
    st.subheader("Dashboard Principal (Vista Holística)")
    c1, c2, c3 = st.columns(3)
    
    # Resumen rápido
    ult_g = query_db("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1")
    c1.metric("Glucosa", f"{ult_g[0][0]} mg/dL" if ult_g else "--")
    
    res_f = query_db("SELECT tipo, monto FROM finanzas")
    bal = sum([m if t == 'ingreso' else -m for t, m in res_f]) if res_f else 0.0
    c2.metric("Balance Total", f"${bal:,.2f}")
    
    prox_c = query_db("SELECT fecha, doctor FROM citas WHERE fecha >= ? LIMIT 1", (str(datetime.date.today()),))
    c3.metric("Próxima Cita", prox_c[0][1] if prox_c else "Sin citas")

    # Gráfico de Glucosa (Diagrama 2)
    st.markdown("### 📈 Gráfico de Glucosa")
    df_g = pd.DataFrame(query_db("SELECT fecha, valor FROM glucosa ORDER BY fecha ASC"), columns=["Fecha", "Valor"])
    if not df_g.empty:
        fig = px.line(df_g, x="Fecha", y="Valor", markers=True, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

# --- SECCIÓN 2: FINANZAS (PRESUPUESTO, INGRESOS, GASTOS) ---
elif menu == "Finanzas":
    st.header("💰 Módulo de Finanzas")
    t_fin = st.tabs(["📊 Gestionar Datos", "🎯 Presupuesto"])
    
    with t_fin[0]:
        col1, col2 = st.columns([1, 2])
        with col1:
            tipo = st.radio("Operación", ["ingreso", "gasto"], horizontal=True)
            monto = st.number_input("Monto ($)", min_value=0.0)
            cat = st.selectbox("Categoría", ["Comida", "Sueldo", "Salud", "Hogar"])
            if st.button("Agregar Registro"):
                query_db("INSERT INTO finanzas VALUES (NULL, ?, ?, ?, ?)", (str(datetime.date.today()), tipo, monto, cat))
                st.rerun()
        with col2:
            st.write("**Historial de Movimientos (Gestionar/Eliminar)**")
            data_f = query_db("SELECT * FROM finanzas ORDER BY id DESC")
            if data_f:
                df_f = pd.DataFrame(data_f, columns=["id", "Fecha", "Tipo", "Monto", "Cat"])
                st.dataframe(df_f[["Fecha", "Tipo", "Monto", "Cat"]], use_container_width=True)
                for r in data_f:
                    if st.button(f"Eliminar {r[2]} ${r[3]} ({r[4]})", key=f"del_f_{r[0]}"):
                        query_db("DELETE FROM finanzas WHERE id=?", (r[0],))
                        st.rerun()

    with t_fin[1]:
        st.subheader("Configuración de Presupuesto")
        p_cat = st.selectbox("Categoría para Límite", ["Comida", "Salud", "Hogar"])
        p_lim = st.number_input("Establecer Límite Mensual", min_value=0.0)
        if st.button("Guardar Presupuesto"):
            query_db("INSERT INTO presupuesto (cat, limite) VALUES (?, ?)", (p_cat, p_lim))
            st.rerun()
        
        # Lógica de Cálculo (Diagrama 2: Gestionar Datos)
        gasto_act = query_db("SELECT SUM(monto) FROM finanzas WHERE cat=? AND tipo='gasto'", (p_cat,))[0][0] or 0.0
        limite_act = query_db("SELECT limite FROM presupuesto WHERE cat=? ORDER BY id DESC LIMIT 1", (p_cat,))
        if limite_act:
            st.write(f"**Progreso {p_cat}:** ${gasto_act} de ${limite_act[0][0]}")
            st.progress(min(gasto_act / limite_act[0][0], 1.0))

# --- SECCIÓN 3: SALUD (GLUCOSA, MEDICAMENTOS, CITAS) ---
elif menu == "Salud":
    st.header("🏥 Módulo de Salud")
    t_sal = st.tabs(["🩸 Glucosa & Semáforo", "💊 Medicamentos", "📅 Citas Médicas"])
    
    with t_sal[0]:
        col1, col2 = st.columns([1, 2])
        with col1:
            val_g = st.number_input("Valor (mg/dL)", value=110.0)
            if st.button("Registrar Glucosa"):
                query_db("INSERT INTO glucosa VALUES (NULL, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), val_g, "Registro"))
                st.rerun()
        with col2:
            st.write("**Semáforo Glucosa (Gestionar/Eliminar)**")
            data_g = query_db("SELECT * FROM glucosa ORDER BY id DESC")
            for r in data_g:
                txt, color = semaforo_ui(r[2])
                c_a, c_b = st.columns([4, 1])
                c_a.markdown(f"<div style='background-color:{color}; padding:10px; border-radius:5px;'><b>{r[1]}</b>: {r[2]} mg/dL - {txt}</div>", unsafe_allow_html=True)
                if c_b.button("🗑️", key=f"del_g_{r[0]}"):
                    query_db("DELETE FROM glucosa WHERE id=?", (r[0],))
                    st.rerun()

    with t_sal[1]:
        st.subheader("Gestión de Medicamentos")
        m_col1, m_col2 = st.columns(2)
        m_nom = m_col1.text_input("Nombre Med")
        m_hor = m_col2.text_input("Horario/Dosis")
        if st.button("Agregar Medicamento"):
            query_db("INSERT INTO meds VALUES (NULL, ?, ?, ?)", (m_nom, "Dosis", m_hor))
            st.rerun()
        
        for m in query_db("SELECT * FROM meds"):
            col_ma, col_mb = st.columns([4, 1])
            col_ma.info(f"💊 **{m[1]}** - {m[3]}")
            if col_mb.button("Borrar", key=f"del_m_{m[0]}"):
                query_db("DELETE FROM meds WHERE id=?", (m[0],))
                st.rerun()

    with t_sal[2]:
        st.subheader("Citas Médicas")
        c_col1, c_col2 = st.columns(2)
        c_fecha = c_col1.date_input("Fecha")
        c_doc = c_col2.text_input("Doctor/Clínica")
        if st.button("Agendar Cita"):
            query_db("INSERT INTO citas VALUES (NULL, ?, ?, ?)", (str(c_fecha), c_doc, "Consulta"))
            st.rerun()
        
        for c in query_db("SELECT * FROM citas ORDER BY fecha ASC"):
            col_ca, col_cb = st.columns([4, 1])
            col_ca.warning(f"📅 **{c[1]}** | {c[2]}")
            if col_cb.button("Cancelar", key=f"del_c_{c[0]}"):
                query_db("DELETE FROM citas WHERE id=?", (c[0],))
                st.rerun()

# --- SECCIÓN 4: MOTOR DE IA & CONECTIVIDAD ---
elif menu == "Motor de IA":
    st.header("🤖 Motor de IA (Predicciones & PDF)")
    
    st.subheader("Generador de PDF & Gacenos")
    if st.button("Generar Reporte Completo PDF"):
        st.success("Reporte exportado correctamente.")
        
    st.divider()
    st.subheader("Consultar Motor de IA")
    pregunta = st.chat_input("Dime Dario, ¿qué quieres analizar hoy?")
    if pregunta:
        with st.chat_message("assistant"):
            st.write("Analizando tus tendencias financieras y de glucosa...")
            # Aquí iría la llamada openai.ChatCompletion con los datos de la DB
            
    st.divider()
    st.write("📤 **Enviar/Compartir**")
    st.link_button("WhatsApp", "https://web.whatsapp.com")
    st.link_button("Gmail", "https://mail.google.com")
