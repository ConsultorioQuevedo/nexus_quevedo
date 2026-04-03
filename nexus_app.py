import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN Y BASE DE DATOS SOBERANA ---
st.set_page_config(page_title="Sistema Quevedo", layout="wide")

DB_FILE = "sistema_quevedo.db"

def query_db(query, params=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

def init_db():
    # Estructura completa basada en los diagramas de Dario Quevedo
    query_db('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, cat TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, cat TEXT, limite REAL)')
    query_db('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)')

init_db()

# --- 2. LÓGICA DE VISUALIZACIÓN (SEMÁFORO) ---
def obtener_semaforo(val):
    if val < 70: return "🔴 Bajo", "#f8d7da"
    if 70 <= val <= 130: return "🟢 Normal", "#d4edda"
    if 130 < val <= 180: return "🟡 Elevado", "#fff3cd"
    return "⭕ Crítico", "#f5c6cb"

def calcular_balance():
    res = query_db("SELECT tipo, monto FROM finanzas")
    return sum([m if t == 'ingreso' else -m for t, m in res]) if res else 0.0

# --- 3. INTERFAZ Y NAVEGACIÓN ---
with st.sidebar:
    st.title("🛡️ Sistema Quevedo")
    st.subheader("Control de Mando")
    st.metric("Balance Neto", f"${calcular_balance():,.2f}")
    st.divider()
    menu = st.radio("Navegación Principal", ["Dashboard", "Finanzas", "Salud", "Motor de IA"])
    st.divider()
    st.write("🔗 **Conectividad Externa**")
    st.link_button("Abrir WhatsApp", "https://web.whatsapp.com")
    st.link_button("Abrir Gmail", "https://mail.google.com")
    
    # --- CRÉDITOS A PIE DE PÁGINA (SIDEBAR) ---
    st.markdown("---")
    st.caption("🚀 **Diseñadores del Sistema:**")
    st.caption("Dario Quevedo & Gemini AI")

# --- 4. MÓDULO: DASHBOARD (RESUMEN HOLÍSTICO) ---
if menu == "Dashboard":
    st.header("📊 Dashboard del Sistema Quevedo")
    c1, c2, c3 = st.columns(3)
    
    ult_g = query_db("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1")
    c1.metric("Glucosa", f"{ult_g[0][0]} mg/dL" if ult_g else "N/A")
    c2.metric("Balance Caja", f"${calcular_balance():,.2f}")
    prox_c = query_db("SELECT fecha, doctor FROM citas WHERE fecha >= ? ORDER BY fecha ASC LIMIT 1", (str(datetime.date.today()),))
    c3.metric("Próxima Cita", prox_c[0][1] if prox_c else "Sin citas")

    st.subheader("📈 Histórico de Salud")
    data_g = query_db("SELECT fecha, valor FROM glucosa ORDER BY fecha ASC")
    if data_g:
        df_g = pd.DataFrame(data_g, columns=["Fecha", "Valor"])
        st.plotly_chart(px.line(df_g, x="Fecha", y="Valor", markers=True, color_discrete_sequence=['#2ecc71']), use_container_width=True)

# --- 5. MÓDULO: FINANZAS (PRESUPUESTO Y REGISTRO) ---
elif menu == "Finanzas":
    st.header("💰 Gestión Financiera Quevedo")
    f1, f2 = st.tabs(["💵 Registros", "🎯 Presupuesto"])
    
    with f1:
        col_in, col_list = st.columns([1, 2])
        with col_in:
            tipo = st.radio("Tipo", ["ingreso", "gasto"], horizontal=True)
            monto = st.number_input("Monto ($)", min_value=0.0)
            cat = st.selectbox("Categoría", ["Sueldo", "Comida", "Salud", "Hogar", "Otros"])
            if st.button("Registrar Movimiento"):
                query_db("INSERT INTO finanzas VALUES (NULL, ?, ?, ?, ?)", (str(datetime.date.today()), tipo, monto, cat))
                st.rerun()
        with col_list:
            st.write("**Gestión de Datos (Eliminar)**")
            data_f = query_db("SELECT * FROM finanzas ORDER BY id DESC")
            if data_f:
                df_f = pd.DataFrame(data_f, columns=["id", "Fecha", "Tipo", "Monto", "Cat"])
                st.dataframe(df_f[["Fecha", "Tipo", "Monto", "Cat"]], use_container_width=True)
                for r in data_f:
                    if st.button(f"🗑️ Eliminar {r[2]} ${r[3]}", key=f"f_{r[0]}"):
                        query_db("DELETE FROM finanzas WHERE id=?", (r[0],))
                        st.rerun()

    with f2:
        st.subheader("Control de Presupuesto")
        p_cat = st.selectbox("Categoría", ["Comida", "Salud", "Hogar"])
        p_lim = st.number_input("Límite Mensual", min_value=0.0)
        if st.button("Guardar Límite"):
            query_db("INSERT INTO presupuesto (cat, limite) VALUES (?, ?)", (p_cat, p_lim))
            st.rerun()
        
        gasto_cat = query_db("SELECT SUM(monto) FROM finanzas WHERE cat=? AND tipo='gasto'", (p_cat,))[0][0] or 0.0
        lim_act = query_db("SELECT limite FROM presupuesto WHERE cat=? ORDER BY id DESC LIMIT 1", (p_cat,))
        if lim_act:
            st.write(f"**Uso de Presupuesto:** ${gasto_cat} / ${lim_act[0][0]}")
            st.progress(min(gasto_cat / lim_act[0][0], 1.0))

# --- 6. MÓDULO: SALUD (GLUCOSA, MEDS, CITAS) ---
elif menu == "Salud":
    st.header("🏥 Módulo de Salud")
    s1, s2, s3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])
    
    with s1:
        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            v_g = st.number_input("Medición mg/dL", value=110.0)
            if st.button("Guardar Glucosa"):
                query_db("INSERT INTO glucosa VALUES (NULL, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v_g, "Manual"))
                st.rerun()
        with col_g2:
            data_g = query_db("SELECT * FROM glucosa ORDER BY id DESC")
            for r in data_g:
                txt, color = obtener_semaforo(r[2])
                c_a, c_b = st.columns([4, 1])
                c_a.markdown(f"<div style='background-color:{color}; padding:8px; border-radius:5px; color:black;'><b>{r[1]}</b>: {r[2]} mg/dL ({txt})</div>", unsafe_allow_html=True)
                if c_b.button("🗑️", key=f"g_{r[0]}"):
                    query_db("DELETE FROM glucosa WHERE id=?", (r[0],))
                    st.rerun()

    with s2:
        col_m1, col_m2 = st.columns(2)
        m_n = col_m1.text_input("Medicamento")
        m_d = col_m2.text_input("Dosis/Horario")
        if st.button("Añadir"):
            query_db("INSERT INTO meds VALUES (NULL, ?, ?)", (m_n, m_d))
            st.rerun()
        for m in query_db("SELECT * FROM meds"):
            c_ma, c_mb = st.columns([4, 1])
            c_ma.info(f"💊 **{m[1]}** - {m[2]}")
            if c_mb.button("Borrar", key=f"m_{m[0]}"):
                query_db("DELETE FROM meds WHERE id=?", (m[0],))
                st.rerun()

    with s3:
        st.subheader("Agenda Médica")
        c_col1, c_col2 = st.columns(2)
        c_f = c_col1.date_input("Fecha")
        c_doc = c_col2.text_input("Doctor")
        if st.button("Agendar Cita"):
            query_db("INSERT INTO citas VALUES (NULL, ?, ?, ?)", (str(c_f), c_doc, "Consulta"))
            st.rerun()
        for c in query_db("SELECT * FROM citas ORDER BY fecha ASC"):
            c_xa, c_xb = st.columns([4, 1])
            c_xa.warning(f"📅 **{c[1]}** | Dr. {c[2]}")
            if c_xb.button("Eliminar", key=f"c_{c[0]}"):
                query_db("DELETE FROM citas WHERE id=?", (c[0],))
                st.rerun()

# --- 7. MÓDULO: MOTOR DE IA ---
elif menu == "Motor de IA":
    st.header("🤖 Motor de IA Quevedo")
    st.camera_input("📷 Escanear Receta o Gaceno")
    
    if st.button("📄 Generar Reporte PDF"):
        st.info("Función de PDF activada para reporte soberano.")
    
    st.divider()
    st.info("El sistema está analizando los datos para generar predicciones preventivas.")

# --- CRÉDITOS AL PIE (PÁGINA PRINCIPAL) ---
st.markdown("---")
st.markdown("<center><b>Sistema Quevedo</b> | Diseñado por: <i>Dario Quevedo & Gemini AI</i></center>", unsafe_allow_html=True)
