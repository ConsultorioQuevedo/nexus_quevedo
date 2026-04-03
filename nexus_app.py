import streamlit as st
import pandas as pd
import sqlite3
import datetime
import openai
from fpdf import FPDF
import plotly.express as px
from PIL import Image
from pyzbar.pyzbar import decode

# --- CONFIGURACIÓN DE SEGURIDAD (Motor de IA) ---
openai.api_key = "TU_API_KEY_AQUI"

st.set_page_config(page_title="Nexus AI - Arquitectura Inteligente", layout="wide")

# --- CAPA DE DATOS (Backend & DB) ---
# Siguiendo tu diagrama: Centralizamos el manejo de la base de datos
DB_FILE = "nexus_intelligent.db"

def query_db(query, params=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

def init_db():
    # Salud
    query_db('''CREATE TABLE IF NOT EXISTS salud_glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)''')
    # Finanzas
    query_db('''CREATE TABLE IF NOT EXISTS finanzas_movs (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, categoria TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS finanzas_presupuesto (id INTEGER PRIMARY KEY, categoria TEXT, limite REAL)''')

init_db()

# --- MOTOR DE IA (Modelos Predictivos) ---
def ia_motor_predictivo(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Eres el Motor de IA de Nexus. Analizas finanzas y salud."},
                      {"role": "user", "content": prompt}]
        )
        return response["choices"][0]["message"]["content"]
    except:
        return "Motor de IA en modo offline (Revisa tu API Key)."

# --- COMPONENTE: GENERADOR DE PDF ---
def generar_reporte_pdf(data_type):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Reporte de {data_type} - Nexus AI", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Generado el: {datetime.date.today()}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ DE USUARIO (Dashboard Principal) ---
st.title("🛡️ Nexus: Finanzas y Salud Inteligente")
st.markdown("---")

# Módulos principales basados en tu diagrama
menu = st.sidebar.radio("Navegación Arquitectónica", ["🏠 Dashboard Principal", "💰 Finanzas", "🏥 Salud", "🤖 Motor de IA"])

# --- 1. DASHBOARD PRINCIPAL ---
if menu == "🏠 Dashboard Principal":
    st.subheader("Dashboard Principal (Vista Holística)")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### Resumen Financiero")
        res_f = query_db("SELECT tipo, monto FROM finanzas_movs")
        if res_f:
            df_f = pd.DataFrame(res_f, columns=["tipo", "monto"])
            balance = df_f[df_f['tipo']=='ingreso']['monto'].sum() - df_f[df_f['tipo']=='gasto']['monto'].sum()
            st.metric("Balance Neto", f"${balance:,.2f}")
        else:
            st.write("Sin datos financieros.")

    with col2:
        st.success("### Resumen de Salud")
        res_g = query_db("SELECT valor FROM salud_glucosa ORDER BY id DESC LIMIT 1")
        if res_g:
            st.metric("Última Glucosa", f"{res_g[0][0]} mg/dL")
        else:
            st.write("Sin registros médicos.")

# --- 2. MÓDULO FINANZAS ---
elif menu == "💰 Finanzas":
    st.header("Módulo de Finanzas")
    tab1, tab2, tab3 = st.tabs(["➕ Ingresos & Gastos", "🎯 Presupuesto", "📈 Predicción"])
    
    with tab1:
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo", ["ingreso", "gasto"])
        monto = c2.number_input("Monto", min_value=0.0)
        cat = st.selectbox("Categoría", ["Sueldo", "Comida", "Salud", "Ocio"])
        if st.button("Registrar Movimiento"):
            query_db("INSERT INTO finanzas_movs VALUES(NULL, ?, ?, ?, ?)", (str(datetime.date.today()), tipo, monto, cat))
            st.toast("Movimiento Guardado")

    with tab3:
        st.write("Análisis del Motor de IA sobre tus gastos...")
        if st.button("Generar Predicción Financiera"):
            st.write(ia_motor_predictivo("Analiza mis gastos de este mes y dime si podré ahorrar."))

# --- 3. MÓDULO SALUD ---
elif menu == "🏥 Salud":
    st.header("Módulo de Salud")
    tab1, tab2, tab3, tab4 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas", "📄 Escáner & PDF"])
    
    with tab1:
        val = st.number_input("Nivel de Glucosa (mg/dL)", value=100.0)
        nota = st.text_input("Nota (Ayunas/Postprandial)")
        if st.button("Guardar Registro"):
            query_db("INSERT INTO salud_glucosa VALUES(NULL, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), val, nota))
            st.rerun()
        
        datos = query_db("SELECT fecha, valor FROM salud_glucosa")
        if datos:
            df = pd.DataFrame(datos, columns=["Fecha", "Valor"])
            fig = px.line(df, x="Fecha", y="Valor", title="Evolución de Glucosa")
            st.plotly_chart(fig)

    with tab4:
        st.subheader("Generación de Documentos (Gacenos & PDF)")
        if st.button("Generar Reporte de Salud PDF"):
            pdf_data = generar_reporte_pdf("Salud")
            st.download_button("Descargar Reporte", pdf_data, "reporte_salud.pdf")

# --- 4. MOTOR DE IA & CONECTIVIDAD ---
elif menu == "🤖 Motor de IA":
    st.header("Centro de Inteligencia y Conectividad")
    
    st.subheader("API de WhatsApp")
    msg = st.text_area("Mensaje para compartir")
    st.link_button("Enviar vía WhatsApp", f"https://wa.me/?text={msg}")
    
    st.divider()
    st.subheader("Modelos Predictivos")
    pregunta = st.text_input("Pregunta al Motor de IA sobre tu arquitectura:")
    if st.button("Consultar"):
        st.write(ia_motor_predictivo(pregunta))

# --- GESTIÓN DE BORRADO (Para correcciones) ---
st.sidebar.divider()
if st.sidebar.checkbox("Modo Edición (Borrar Datos)"):
    st.sidebar.warning("Selecciona qué tabla deseas limpiar:")
    if st.sidebar.button("Limpiar Finanzas"):
        query_db("DELETE FROM finanzas_movs")
        st.rerun()
    if st.sidebar.button("Limpiar Salud"):
        query_db("DELETE FROM salud_glucosa")
        st.rerun()
