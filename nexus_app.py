import streamlit as st
import pandas as pd
import sqlite3
import datetime
import openai
from fpdf import FPDF
import plotly.express as px
import numpy as np
from PIL import Image
from pyzbar.pyzbar import decode
import io

# --- 1. CONFIGURACIÓN Y MOTOR DE IA ---
# Usa st.secrets["OPENAI_API_KEY"] si lo subes a la nube
openai.api_key = "TU_API_KEY_AQUI"

st.set_page_config(page_title="Nexus AI - Sistema Soberano", layout="wide", initial_sidebar_state="expanded")

DB_FILE = "nexus_intelligent.db"

# --- 2. CAPA DE DATOS (Backend & DB) ---
def query_db(query, params=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

def init_db():
    # Siguiendo tu arquitectura: Tablas para Salud y Finanzas
    query_db('''CREATE TABLE IF NOT EXISTS salud_glucosa 
                (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_meds 
                (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, fecha_inicio TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_citas 
                (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, especialidad TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS finanzas_movs 
                (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, categoria TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS escaneos_history 
                (id INTEGER PRIMARY KEY, fecha TEXT, codigo TEXT, producto TEXT)''')

init_db()

# --- 3. LÓGICA DE NEGOCIO Y ESTILOS ---
def calcular_balance():
    res = query_db("SELECT tipo, monto FROM finanzas_movs")
    if not res: return 0.0
    df = pd.DataFrame(res, columns=["tipo", "monto"])
    ingresos = df[df.tipo == "ingreso"]["monto"].sum()
    gastos = df[df.tipo == "gasto"]["monto"].sum()
    return ingresos - gastos

def estilo_semaforo(val):
    """Lógica de colores para Glucosa según rangos médicos estándar"""
    if val < 70: return "background-color: #f8d7da; color: #721c24;"  # Hipoglucemia
    if 70 <= val <= 130: return "background-color: #d4edda; color: #155724;" # Normal
    if 130 < val <= 180: return "background-color: #fff3cd; color: #856404;" # Elevada
    return "background-color: #f8d7da; color: #721c24;" # Muy Alta

# --- 4. UI - SIDEBAR (Conectividad & PDF) ---
with st.sidebar:
    st.title("🚀 Nexus Control")
    st.metric("Balance Total", f"${calcular_balance():,.2f}")
    st.divider()
    
    st.subheader("Compartir & Reportes")
    if st.button("📄 Generar Reporte PDF Salud"):
        data = query_db("SELECT fecha, valor, nota FROM salud_glucosa ORDER BY id DESC")
        if data:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "REPORTE MÉDICO - NEXUS AI", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            pdf.ln(10)
            for r in data:
                pdf.cell(0, 10, f"Fecha: {r[0]} | Valor: {r[1]} mg/dL | Nota: {r[2]}", ln=True)
            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("⬇️ Descargar Reporte", pdf_out, "Nexus_Salud.pdf")
    
    st.link_button("💬 WhatsApp", "https://web.whatsapp.com")
    st.link_button("📧 Gmail", "https://mail.google.com")

# --- 5. TABS PRINCIPALES (Basados en el Diagrama) ---
tabs = st.tabs(["📊 Dashboard", "💰 Finanzas", "🏥 Salud", "🔍 Escáner", "🤖 Motor de IA"])

# --- DASHBOARD ---
with tabs[0]:
    st.subheader("Dashboard Principal")
    c1, c2, c3 = st.columns(3)
    
    ult_g = query_db("SELECT valor FROM salud_glucosa ORDER BY id DESC LIMIT 1")
    c1.metric("Última Glucosa", f"{ult_g[0][0]} mg/dL" if ult_g else "N/A")
    
    c2.metric("Balance Neto", f"${calcular_balance():,.2f}")
    
    prox_c = query_db("SELECT fecha, doctor FROM salud_citas WHERE fecha >= ? ORDER BY fecha ASC LIMIT 1", (str(datetime.date.today()),))
    c3.metric("Próxima Cita", f"{prox_c[0][1]}" if prox_c else "Sin citas", help=f"Fecha: {prox_c[0][0]}" if prox_c else "")

# --- FINANZAS (Con Borrado) ---
with tabs[1]:
    st.header("Módulo de Finanzas")
    f_col1, f_col2 = st.columns([1, 2])
    
    with f_col1:
        f_tipo = st.radio("Tipo", ["ingreso", "gasto"], horizontal=True)
        f_monto = st.number_input("Monto ($)", min_value=0.0)
        f_cat = st.selectbox("Categoría", ["Sueldo", "Comida", "Salud", "Hogar", "Otros"])
        if st.button("Registrar Movimiento"):
            query_db("INSERT INTO finanzas_movs VALUES(NULL, ?, ?, ?, ?)", 
                     (str(datetime.date.today()), f_tipo, f_monto, f_cat))
            st.rerun()
            
    with f_col2:
        res_f = query_db("SELECT * FROM finanzas_movs ORDER BY id DESC")
        if res_f:
            df_f = pd.DataFrame(res_f, columns=["id", "Fecha", "Tipo", "Monto", "Cat"])
            st.dataframe(df_f[["Fecha", "Tipo", "Monto", "Cat"]], use_container_width=True)
            with st.expander("🗑️ Borrar Movimientos"):
                for _, r in df_f.iterrows():
                    cols = st.columns([3, 1])
                    cols[0].write(f"{r['Fecha']} | {r['Tipo']} | ${r['Monto']}")
                    if cols[1].button("Borrar", key=f"del_f_{r['id']}"):
                        query_db("DELETE FROM finanzas_movs WHERE id=?", (r['id'],))
                        st.rerun()

# --- SALUD (Glucosa + Meds + Citas + Semáforo) ---
with tabs[2]:
    st.header("Módulo de Salud Inteligente")
    s_tab1, s_tab2, s_tab3 = st.tabs(["🩸 Registro de Glucosa", "💊 Medicamentos", "📅 Citas Médicas"])
    
    with s_tab1:
        g_col1, g_col2 = st.columns([1, 2])
        with g_col1:
            g_val = st.number_input("Medición (mg/dL)", value=110.0)
            g_nota = st.text_input("Nota (ej. Ayunas)")
            if st.button("Guardar Glucosa"):
                query_db("INSERT INTO salud_glucosa VALUES(NULL, ?, ?, ?)", 
                         (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), g_val, g_nota))
                st.rerun()
        with g_col2:
            res_g = query_db("SELECT id, fecha, valor, nota FROM salud_glucosa ORDER BY id DESC")
            if res_g:
                df_g = pd.DataFrame(res_g, columns=["id", "Fecha", "Valor", "Nota"])
                # SEMÁFORO APLICADO AQUÍ
                st.dataframe(df_g[["Fecha", "Valor", "Nota"]].style.map(estilo_semaforo, subset=["Valor"]), use_container_width=True)
                if st.button("Borrar último registro de glucosa"):
                    query_db("DELETE FROM salud_glucosa WHERE id=?", (res_g[0][0],))
                    st.rerun()

    with s_tab2:
        m_col1, m_col2 = st.columns([1, 2])
        with m_col1:
            m_nom = st.text_input("Nombre del Medicamento")
            m_dos = st.text_input("Dosis (ej. 500mg)")
            if st.button("Añadir Medicamento"):
                query_db("INSERT INTO salud_meds VALUES(NULL, ?, ?, ?)", (m_nom, m_dos, str(datetime.date.today())))
                st.rerun()
        with m_col2:
            res_m = query_db("SELECT * FROM salud_meds")
            if res_m:
                df_m = pd.DataFrame(res_m, columns=["id", "Nombre", "Dosis", "Inicio"])
                st.table(df_m[["Nombre", "Dosis"]])
                for _, r in df_m.iterrows():
                    if st.button(f"Eliminar {r['Nombre']}", key=f"del_m_{r['id']}"):
                        query_db("DELETE FROM salud_meds WHERE id=?", (r['id'],))
                        st.rerun()

    with s_tab3:
        c_col1, c_col2 = st.columns([1, 2])
        with c_col1:
            c_fecha = st.date_input("Fecha de Cita")
            c_doc = st.text_input("Doctor")
            c_esp = st.text_input("Especialidad")
            if st.button("Agendar Cita"):
                query_db("INSERT INTO salud_citas VALUES(NULL, ?, ?, ?)", (str(c_fecha), c_doc, c_esp))
                st.rerun()
        with c_col2:
            res_c = query_db("SELECT * FROM salud_citas ORDER BY fecha ASC")
            if res_c:
                df_c = pd.DataFrame(res_c, columns=["id", "Fecha", "Doctor", "Especialidad"])
                st.dataframe(df_c[["Fecha", "Doctor", "Especialidad"]], use_container_width=True)
                for _, r in df_c.iterrows():
                    if st.button(f"Cancelar cita: {r['Fecha']} con {r['Doctor']}", key=f"del_c_{r['id']}"):
                        query_db("DELETE FROM salud_citas WHERE id=?", (r['id'],))
                        st.rerun()

# --- ESCÁNER ---
with tabs[3]:
    st.header("Escáner & PDF")
    cam = st.camera_input("Capturar código de barras")
    if cam:
        img = Image.open(cam)
        decoded = decode(np.array(img))
        if decoded:
            code = decoded[0].data.decode("utf-8")
            st.success(f"Código: {code}")
            # Lógica de búsqueda en API (simplificada para estabilidad)
            st.info("Buscando información nutricional...")

# --- MOTOR DE IA ---
with tabs[4]:
    st.header("Nexus IA: Análisis Predictivo")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("¿Cómo están mis niveles hoy?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            try:
                # El motor de IA real
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Eres Nexus AI, asistente personal de salud y finanzas de Dario."}] + st.session_state.chat_history
                )["choices"][0]["message"]["content"]
                st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            except:
                st.error("Error de Motor de IA. Verifica tu API Key.")
