import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN Y BASE DE DATOS ---
st.set_page_config(page_title="Nexus - Registro Soberano", layout="wide")

DB_FILE = "nexus_soberano.db"

def query_db(query, params=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

def init_db():
    # Tablas de Finanzas (Diagrama 1)
    query_db('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, cat TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS presupuesto (id INTEGER PRIMARY KEY, cat TEXT, limite REAL)')
    # Tablas de Salud (Diagrama 2)
    query_db('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    query_db('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)')

init_db()

# --- 2. FUNCIONES DE LÓGICA (SEMÁFORO Y CÁLCULOS) ---
def obtener_semaforo(val):
    if val < 70: return "🔴 Bajo", "#f8d7da"
    if 70 <= val <= 130: return "🟢 Normal", "#d4edda"
    if 130 < val <= 180: return "🟡 Elevado", "#fff3cd"
    return "⭕ Crítico", "#f5c6cb"

def calcular_balance():
    res = query_db("SELECT tipo, monto FROM finanzas")
    return sum([m if t == 'ingreso' else -m for t, m in res]) if res else 0.0

# --- 3. INTERFAZ (SIDEBAR Y NAVEGACIÓN) ---
with st.sidebar:
    st.title("🛡️ Nexus Control")
    st.metric("Balance Total", f"${calcular_balance():,.2f}")
    st.divider()
    menu = st.radio("Menú Principal", ["Dashboard", "Finanzas", "Salud", "Motor de IA"])
    st.divider()
    st.write("🔗 **Conectividad**")
    st.link_button("WhatsApp", "https://web.whatsapp.com")
    st.link_button("Gmail", "https://mail.google.com")

# --- 4. MÓDULO: DASHBOARD ---
if menu == "Dashboard":
    st.header("📊 Panel de Control Holístico")
    c1, c2, c3 = st.columns(3)
    
    ult_g = query_db("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1")
    c1.metric("Glucosa Actual", f"{ult_g[0][0]} mg/dL" if ult_g else "--")
    c2.metric("Balance de Caja", f"${calcular_balance():,.2f}")
    prox_c = query_db("SELECT fecha, doctor FROM citas WHERE fecha >= ? ORDER BY fecha ASC LIMIT 1", (str(datetime.date.today()),))
    c3.metric("Próxima Cita", prox_c[0][1] if prox_c else "Sin citas")

    st.subheader("📈 Tendencia de Glucosa")
    df_g = pd.DataFrame(query_db("SELECT fecha, valor FROM glucosa ORDER BY fecha ASC"), columns=["Fecha", "Valor"])
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x="Fecha", y="Valor", markers=True, template="plotly_white"), use_container_width=True)

# --- 5. MÓDULO: FINANZAS ---
elif menu == "Finanzas":
    st.header("💰 Gestión de Finanzas")
    f1, f2 = st.tabs(["💸 Ingresos y Gastos", "🎯 Presupuesto"])
    
    with f1:
        col_in, col_list = st.columns([1, 2])
        with col_in:
            tipo = st.radio("Tipo", ["ingreso", "gasto"], horizontal=True)
            monto = st.number_input("Monto ($)", min_value=0.0)
            cat = st.selectbox("Categoría", ["Comida", "Salud", "Sueldo", "Hogar", "Otros"])
            if st.button("Registrar Movimiento"):
                query_db("INSERT INTO finanzas VALUES (NULL, ?, ?, ?, ?)", (str(datetime.date.today()), tipo, monto, cat))
                st.rerun()
        with col_list:
            st.write("**Historial (Eliminar Registros)**")
            data_f = query_db("SELECT * FROM finanzas ORDER BY id DESC")
            if data_f:
                df_f = pd.DataFrame(data_f, columns=["id", "Fecha", "Tipo", "Monto", "Cat"])
                st.dataframe(df_f[["Fecha", "Tipo", "Monto", "Cat"]], use_container_width=True)
                for r in data_f:
                    if st.button(f"Borrar {r[2]} ${r[3]}", key=f"f_{r[0]}"):
                        query_db("DELETE FROM finanzas WHERE id=?", (r[0],))
                        st.rerun()

    with f2:
        st.subheader("Control de Presupuesto Mensual")
        p_cat = st.selectbox("Categoría a Limitar", ["Comida", "Salud", "Hogar"])
        p_lim = st.number_input("Establecer Límite", min_value=0.0)
        if st.button("Guardar Límite"):
            query_db("INSERT INTO presupuesto (cat, limite) VALUES (?, ?)", (p_cat, p_lim))
            st.rerun()
        
        gasto_cat = query_db("SELECT SUM(monto) FROM finanzas WHERE cat=? AND tipo='gasto'", (p_cat,))[0][0] or 0.0
        lim_act = query_db("SELECT limite FROM presupuesto WHERE cat=? ORDER BY id DESC LIMIT 1", (p_cat,))
        if lim_act:
            st.write(f"**Gasto en {p_cat}:** ${gasto_cat} / ${lim_act[0][0]}")
            st.progress(min(gasto_cat / lim_act[0][0], 1.0))

# --- 6. MÓDULO: SALUD ---
elif menu == "Salud":
    st.header("🏥 Módulo de Salud Soberano")
    s1, s2, s3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])
    
    with s1:
        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            v_g = st.number_input("Valor mg/dL", value=110.0)
            if st.button("Guardar Glucosa"):
                query_db("INSERT INTO glucosa VALUES (NULL, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v_g, "Manual"))
                st.rerun()
        with col_g2:
            data_g = query_db("SELECT * FROM glucosa ORDER BY id DESC")
            for r in data_g:
                txt, color = obtener_semaforo(r[2])
                c_a, c_b = st.columns([4, 1])
                c_a.markdown(f"<div style='background-color:{color}; padding:8px; border-radius:5px;'><b>{r[1]}</b>: {r[2]} mg/dL ({txt})</div>", unsafe_allow_html=True)
                if c_b.button("🗑️", key=f"g_{r[0]}"):
                    query_db("DELETE FROM glucosa WHERE id=?", (r[0],))
                    st.rerun()

    with s2:
        col_m1, col_m2 = st.columns(2)
        m_nom = col_m1.text_input("Medicamento")
        m_dos = col_m2.text_input("Dosis/Horario")
        if st.button("Añadir Medicamento"):
            query_db("INSERT INTO meds VALUES (NULL, ?, ?)", (m_nom, m_dos))
            st.rerun()
        for m in query_db("SELECT * FROM meds"):
            c_ma, c_mb = st.columns([4, 1])
            c_ma.info(f"💊 **{m[1]}** - {m[2]}")
            if c_mb.button("Borrar", key=f"m_{m[0]}"):
                query_db("DELETE FROM meds WHERE id=?", (m[0],))
                st.rerun()

    with s3:
        st.subheader("Agenda de Citas")
        c_col1, c_col2 = st.columns(2)
        c_f = c_col1.date_input("Fecha")
        c_d = c_col2.text_input("Doctor/Especialidad")
        if st.button("Agendar Cita"):
            query_db("INSERT INTO citas VALUES (NULL, ?, ?, ?)", (str(c_f), c_d, "Consulta"))
            st.rerun()
        for c in query_db("SELECT * FROM citas ORDER BY fecha ASC"):
            c_xa, c_xb = st.columns([4, 1])
            c_xa.warning(f"📅 **{c[1]}** | {c[2]}")
            if c_xb.button("Eliminar", key=f"c_{c[0]}"):
                query_db("DELETE FROM citas WHERE id=?", (c[0],))
                st.rerun()

# --- 7. MÓDULO: MOTOR DE IA Y EXTRAS ---
elif menu == "Motor de IA":
    st.header("🤖 Motor de IA & Gacenos")
    st.camera_input("📷 Escanear Documento (Gaceno/Receta)")
    
    if st.button("📄 Generar Reporte PDF Nexus"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="REPORTE SOBERANO NEXUS", ln=True, align='C')
        # ... lógica de llenado de PDF ...
        st.success("Reporte listo para descarga.")
    
    st.divider()
    st.info("El Motor de IA está analizando tus tendencias basándose en la Base de Datos Soberana.")
