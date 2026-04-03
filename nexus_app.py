import streamlit as st
import pandas as pd
import sqlite3
import datetime
import openai
from fpdf import FPDF
import plotly.express as px
import numpy as np

# --- CONFIGURACIÓN DE SEGURIDAD (Motor de IA) ---
# Recuerda colocar tu API Key real aquí
openai.api_key = "TU_API_KEY_AQUI"

st.set_page_config(page_title="Nexus AI - Sistema Integral", layout="wide")

DB_FILE = "nexus_intelligent.db"

# --- CAPA DE DATOS (Backend & DB) ---
def query_db(query, params=()):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.fetchall()

def init_db():
    # Tablas de Salud
    query_db('''CREATE TABLE IF NOT EXISTS salud_glucosa 
                (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_meds 
                (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)''')
    query_db('''CREATE TABLE IF NOT EXISTS salud_citas 
                (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)''')
    # Tablas de Finanzas
    query_db('''CREATE TABLE IF NOT EXISTS finanzas_movs 
                (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, categoria TEXT)''')

init_db()

# --- FUNCIONES DE SOPORTE (PDF & IA) ---
def generar_reporte_pdf(titulo, df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"NEXUS AI - {titulo}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    for index, row in df.iterrows():
        linea = " | ".join([f"{col}: {val}" for col, val in row.items()])
        pdf.cell(0, 10, linea, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ DE USUARIO ---
st.title("🛡️ Nexus: Inteligencia en Finanzas y Salud")
st.markdown("---")

menu = st.sidebar.radio("Módulos de Arquitectura", 
                       ["🏠 Dashboard", "💰 Finanzas", "🏥 Salud", "🤖 Motor de IA"])

# --- 1. DASHBOARD ---
if menu == "🏠 Dashboard":
    st.subheader("Panel de Control Principal")
    c1, c2 = st.columns(2)
    
    with c1:
        st.info("### Salud")
        ult_g = query_db("SELECT valor, fecha FROM salud_glucosa ORDER BY id DESC LIMIT 1")
        if ult_g:
            st.metric("Última Glucosa", f"{ult_g[0][0]} mg/dL", f"Registrado: {ult_g[0][1]}")
        
        prox_c = query_db("SELECT fecha, doctor FROM salud_citas WHERE fecha >= ? ORDER BY fecha ASC LIMIT 1", (str(datetime.date.today()),))
        if prox_c:
            st.write(f"📅 **Próxima Cita:** {prox_c[0][0]} con Dr. {prox_c[0][1]}")

    with c2:
        st.success("### Finanzas")
        res_f = query_db("SELECT tipo, monto FROM finanzas_movs")
        if res_f:
            df_f = pd.DataFrame(res_f, columns=["tipo", "monto"])
            bal = df_f[df_f['tipo']=='ingreso']['monto'].sum() - df_f[df_f['tipo']=='gasto']['monto'].sum()
            st.metric("Balance Neto", f"${bal:,.2f}")

# --- 2. FINANZAS ---
elif menu == "💰 Finanzas":
    st.header("Gestión Financiera")
    col_in, col_vis = st.columns([1, 2])
    
    with col_in:
        tipo = st.radio("Operación", ["ingreso", "gasto"], horizontal=True)
        monto = st.number_input("Cantidad ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Sueldo", "Comida", "Hogar", "Salud", "Transporte"])
        if st.button("Registrar Movimiento"):
            query_db("INSERT INTO finanzas_movs VALUES(NULL, ?, ?, ?, ?)", 
                     (str(datetime.date.today()), tipo, monto, cat))
            st.rerun()

    with col_vis:
        data = query_db("SELECT * FROM finanzas_movs ORDER BY id DESC")
        if data:
            df_f = pd.DataFrame(data, columns=["id", "Fecha", "Tipo", "Monto", "Cat"])
            st.dataframe(df_f[["Fecha", "Tipo", "Monto", "Cat"]], use_container_width=True)
            
            with st.expander("🗑️ Borrar Registros"):
                for i, row in df_f.iterrows():
                    if st.button(f"Eliminar {row['Tipo']} ${row['Monto']}", key=f"f_{row['id']}"):
                        query_db("DELETE FROM finanzas_movs WHERE id=?", (row['id'],))
                        st.rerun()

# --- 3. SALUD ---
elif menu == "🏥 Salud":
    st.header("Centro de Salud")
    tab1, tab2, tab3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])

    with tab1:
        v = st.number_input("mg/dL", value=100.0)
        n = st.text_input("Nota", "Ayunas")
        if st.button("Guardar Glucosa"):
            query_db("INSERT INTO salud_glucosa VALUES(NULL, ?, ?, ?)", 
                     (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v, n))
            st.rerun()
        
        hist_g = query_db("SELECT fecha, valor FROM salud_glucosa ORDER BY id DESC")
        if hist_g:
            df_g = pd.DataFrame(hist_g, columns=["Fecha", "Valor"])
            st.plotly_chart(px.line(df_g, x="Fecha", y="Valor", markers=True))
            st.dataframe(df_g, use_container_width=True)

    with tab2:
        st.subheader("Registro de Medicamentos")
        col_m1, col_m2 = st.columns(2)
        m_nom = col_m1.text_input("Nombre Med")
        m_dos = col_m2.text_input("Dosis (ej. 500mg)")
        if st.button("Añadir a mi lista"):
            query_db("INSERT INTO salud_meds VALUES(NULL, ?, ?, ?)", (m_nom, m_dos, "Diario"))
            st.rerun()
        
        data_m = query_db("SELECT * FROM salud_meds")
        if data_m:
            df_m = pd.DataFrame(data_m, columns=["id", "Nombre", "Dosis", "Horario"])
            st.table(df_m[["Nombre", "Dosis"]])
            for i, r in df_m.iterrows():
                if st.button(f"Quitar {r['Nombre']}", key=f"m_{r['id']}"):
                    query_db("DELETE FROM salud_meds WHERE id=?", (r['id'],))
                    st.rerun()

    with tab3:
        st.subheader("Agenda Médica")
        f_c = st.date_input("Fecha")
        d_c = st.text_input("Doctor")
        if st.button("Agendar"):
            query_db("INSERT INTO salud_citas VALUES(NULL, ?, ?, ?)", (str(f_c), d_c, "Consulta"))
            st.rerun()
        
        data_c = query_db("SELECT * FROM salud_citas ORDER BY fecha ASC")
        if data_c:
            df_c = pd.DataFrame(data_c, columns=["id", "Fecha", "Doctor", "Motivo"])
            st.dataframe(df_c[["Fecha", "Doctor"]], use_container_width=True)
            for i, r in df_c.iterrows():
                if st.button(f"Borrar Cita: {r['Fecha']}", key=f"c_{r['id']}"):
                    query_db("DELETE FROM salud_citas WHERE id=?", (r['id'],))
                    st.rerun()

# --- 4. MOTOR DE IA & REPORTES ---
elif menu == "🤖 Motor de IA":
    st.header("Análisis Nexus Intelligence")
    
    st.subheader("Generación de Reportes PDF")
    if st.button("Generar Reporte Completo de Salud"):
        data = query_db("SELECT fecha, valor FROM salud_glucosa")
        pdf = generar_reporte_pdf("HISTORIAL SALUD", pd.DataFrame(data, columns=["Fecha", "Valor"]))
        st.download_button("Descargar PDF", pdf, "reporte_salud.pdf")

    st.divider()
    st.subheader("Consulta al Motor de IA")
    pregunta = st.text_input("¿Qué quieres consultar hoy?")
    if st.button("Preguntar"):
        try:
            r = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": pregunta}]
            )
            st.write(r["choices"][0]["message"]["content"])
        except:
            st.error("Error de conexión. Verifica tu API Key.")
