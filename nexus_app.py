import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import requests
import openai
from fpdf import FPDF
import plotly.express as px  # Cambio a gráficos interactivos
from PIL import Image
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression
import io

# -------------------------
# CONFIG & SEGURIDAD
# -------------------------
# Nota: En Streamlit Cloud, usa st.secrets["OPENAI_API_KEY"]
openai.api_key = "TUAPIKEYAQUI"

st.set_page_config(page_title="Nexus AI Personal", layout="wide", initial_sidebar_state="expanded")

DB = "nexus_personal.db"

def run(q, p=()):
    with sqlite3.connect(DB, check_same_thread=False) as c:
        cur = c.cursor()
        cur.execute(q, p)
        c.commit()
        return cur.fetchall()

# -------------------------
# DB INITIALIZATION (Mantenida)
# -------------------------
def init():
    run('''CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS medicamentos(id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, dosis TEXT, estado TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS citas(id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, especialidad TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS finanzas(id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, categoria TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS escaneos(id INTEGER PRIMARY KEY, fecha TEXT, codigo TEXT, producto TEXT, tipo TEXT)''')

init()

# -------------------------
# LÓGICA DE NEGOCIO (Mejorada)
# -------------------------
def balance_total():
    df = pd.DataFrame(run("SELECT tipo, monto FROM finanzas"), columns=["tipo", "monto"])
    if df.empty: return 0.0
    ingresos = df[df.tipo == "ingreso"]["monto"].sum()
    gastos = df[df.tipo == "gasto"]["monto"].sum()
    return ingresos - gastos

def color_glucosa_css(valor):
    if 90 <= valor <= 130: return "background-color: #d4edda; color: #155724;" # Verde suave
    elif 130 < valor <= 160: return "background-color: #fff3cd; color: #856404;" # Amarillo suave
    elif valor > 160: return "background-color: #f8d7da; color: #721c24;" # Rojo suave
    return ""

# -------------------------
# UI - SIDEBAR (Accesos y PDF)
# -------------------------
with st.sidebar:
    st.title("🚀 Nexus Control")
    st.info(f"💰 **Balance Actual:** ${balance_total():,.2f}")
    
    st.divider()
    if st.button("📄 Generar Reporte Médico PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "REPORTE PERSONAL NEXUS AI", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        pdf.cell(200, 10, f"Fecha de reporte: {datetime.date.today()}", ln=True)
        pdf.cell(200, 10, f"Balance Financiero: ${balance_total()}", ln=True)
        # Aquí podrías iterar sobre los datos de la DB para llenar el PDF
        pdf_output = pdf.output(dest='S').encode('latin-1')
        st.download_button("⬇️ Descargar PDF", data=pdf_output, file_name="reporte_nexus.pdf")

    st.divider()
    st.link_button("💬 WhatsApp", "https://web.whatsapp.com")
    st.link_button("📧 Gmail", "https://mail.google.com")

# -------------------------
# TABS PRINCIPALES
# -------------------------
tabs = st.tabs(["📊 Dashboard", "🩸 Salud", "💊 Meds", "📅 Citas", "💸 Finanzas", "🔍 Escáner", "🤖 IA Chat"])

# --- DASHBOARD ---
with tabs[0]:
    col1, col2, col3 = st.columns(3)
    
    # Predicción Glucosa
    df_g = pd.DataFrame(run("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 10"), columns=["valor"])
    if len(df_g) >= 5:
        df_g["t"] = range(len(df_g))
        model = LinearRegression().fit(df_g[["t"]], df_g["valor"])
        pred = model.predict([[len(df_g)]])[0]
        col1.metric("Próxima Glucosa (Est.)", f"{pred:.1f} mg/dL")
    else:
        col1.metric("Próxima Glucosa", "Faltan datos")
        
    col2.metric("Balance Total", f"${balance_total():,.2f}")
    
    prox_cita = run("SELECT fecha, doctor FROM citas WHERE fecha >= ? ORDER BY fecha ASC LIMIT 1", (str(datetime.date.today()),))
    if prox_cita:
        col3.metric("Próxima Cita", f"{prox_cita[0][0]}", help=f"Dr. {prox_cita[0][1]}")

# --- SALUD (GLUCOSA) ---
with tabs[1]:
    c1, c2 = st.columns([1, 2])
    with c1:
        val = st.number_input("Medición (mg/dL)", min_value=0.0, step=1.0)
        nota = st.text_input("Nota (ej. Ayunas, Post-comida)")
        if st.button("Registrar Glucosa"):
            run("INSERT INTO glucosa VALUES(NULL,?,?,?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), val, nota))
            st.rerun()
    
    with c2:
        df_sql = pd.DataFrame(run("SELECT fecha, valor, nota FROM glucosa ORDER BY id DESC"), columns=["fecha", "valor", "nota"])
        if not df_sql.empty:
            # Gráfico interactivo con Plotly
            fig = px.line(df_sql, x="fecha", y="valor", title="Historial de Glucosa", markers=True)
            fig.add_hline(y=130, line_dash="dash", line_color="green", annotation_text="Límite normal")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_sql.style.applymap(color_glucosa_css, subset=["valor"]), use_container_width=True)

# --- MEDICAMENTOS ---
with tabs[2]:
    n = st.text_input("Medicamento")
    d = st.text_input("Dosis / Frecuencia")
    if st.button("Añadir Medicamento"):
        run("INSERT INTO medicamentos VALUES(NULL,?,?,?,?)", (datetime.date.today(), n, d, "Activo"))
        st.rerun()
    st.table(pd.DataFrame(run("SELECT nombre, dosis, estado FROM medicamentos"), columns=["Nombre", "Dosis", "Estado"]))

# --- CITAS ---
with tabs[3]:
    f_cita = st.date_input("Fecha de la cita")
    doc = st.text_input("Nombre del Doctor")
    esp = st.text_input("Especialidad")
    if st.button("Agendar"):
        run("INSERT INTO citas VALUES(NULL,?,?,?)", (str(f_cita), doc, esp))
        st.success("Cita guardada")
    st.dataframe(pd.DataFrame(run("SELECT fecha, doctor, especialidad FROM citas"), columns=["Fecha", "Doctor", "Especialidad"]))

# --- FINANZAS ---
with tabs[4]:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tipo = st.radio("Tipo", ["ingreso", "gasto"], horizontal=True)
        monto = st.number_input("Monto ($)", min_value=0.0)
        cat = st.selectbox("Categoría", ["Salud", "Comida", "Transporte", "Sueldo", "Otros"])
        if st.button("Guardar Movimiento"):
            run("INSERT INTO finanzas VALUES(NULL,?,?,?,?)", (datetime.datetime.now(), tipo, monto, cat))
            st.rerun()
    with col_f2:
        df_fin = pd.DataFrame(run("SELECT fecha, tipo, monto, categoria FROM finanzas ORDER BY id DESC"), columns=["Fecha", "Tipo", "Monto", "Cat"])
        st.dataframe(df_fin)

# --- ESCÁNER ---
with tabs[5]:
    cam = st.camera_input("Escanear Producto")
    if cam:
        img = Image.open(cam)
        decoded = decode(np.array(img))
        if decoded:
            code = decoded[0].data.decode("utf-8")
            st.write(f"**Código detectado:** {code}")
            try:
                r = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{code}.json").json()
                if r.get("status") == 1:
                    prod = r["product"]
                    nombre = prod.get("product_name", "Desconocido")
                    cal = prod.get("nutriments", {}).get("energy-kcal_100g", "N/A")
                    st.success(f"Producto: {nombre} | Calorías: {cal} kcal")
                    if st.button("Guardar en historial"):
                        run("INSERT INTO escaneos VALUES(NULL,?,?,?,?)", (datetime.datetime.now(), code, nombre, "Alimento"))
                else:
                    st.warning("No encontrado en la base de datos nutricional.")
            except:
                st.error("Error al conectar con el servidor nutricional.")
        else:
            st.warning("No se detectó código de barras.")

# --- IA CHAT ---
with tabs[6]:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Aquí la IA podría recibir contexto de la DB si quisieras
            res = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Eres Nexus AI, un asistente personal de salud y finanzas."}] + st.session_state.messages
            )
            response = res["choices"][0]["message"]["content"]
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
