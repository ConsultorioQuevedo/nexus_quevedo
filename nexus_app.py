import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import requests
from openai import OpenAI
from fpdf import FPDF
from PIL import Image

# -------------------------
# CONFIGURACIÓN INICIAL
# -------------------------
st.set_page_config(page_title="Nexus AI PRO", layout="wide")

# Estilos CSS para el modo oscuro y centrado
st.markdown("""
<style>
body {background-color: #0e1117; color: white;}
.stDataFrame td {
    text-align: center !important;
}
</style>
""", unsafe_allow_html=True)

# Inicialización del cliente OpenAI con Secrets (Línea crítica corregida)
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("Configura 'OPENAI_API_KEY' en los Secrets de Streamlit.")

# -------------------------
# SISTEMA DE LOGIN
# -------------------------
if "login" not in st.session_state:
    st.session_state.login = False

def login():
    st.title("🔐 Nexus AI")
    u = st.text_input("Usuario", key="login_user")
    p = st.text_input("Contraseña", type="password", key="login_pass")
    if st.button("Entrar"):
        if u == "admin" and p == "1234":
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

if not st.session_state.login:
    login()
    st.stop()

# -------------------------
# BASE DE DATOS (SQLite)
# -------------------------
def conn():
    return sqlite3.connect("nexus.db", check_same_thread=False)

def run_db(q, p=()):
    with conn() as c:
        cur = c.cursor()
        cur.execute(q, p)
        c.commit()
        return cur.fetchall()

# Crear tabla si no existe
run_db("CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)")

# -------------------------
# LÓGICA DE NEGOCIO
# -------------------------
def guardar_glucosa(v):
    run_db("INSERT INTO glucosa VALUES(NULL,?,?)", (datetime.datetime.now().isoformat(), v))

def glucosa_df():
    data = run_db("SELECT * FROM glucosa")
    df = pd.DataFrame(data, columns=["id", "fecha", "valor"])
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["hora"] = df["fecha"].dt.strftime("%H:%M")
        df["fecha_str"] = df["fecha"].dt.strftime("%d/%m/%Y")
    return df

def color_glucosa(v):
    if v < 70:
        return "background-color: #3498db; color:white"   # Azul (Baja)
    elif v <= 140:
        return "background-color: #2ecc71; color:white"   # Verde (Normal)
    elif v <= 180:
        return "background-color: #f39c12; color:white"   # Amarillo (Alta)
    else:
        return "background-color: #e74c3c; color:white"   # Rojo (Muy Alta)

# -------------------------
# INTERFAZ DE USUARIO (TABS)
# -------------------------
st.title("🩺 Control de Glucosa Inteligente")

tabs = st.tabs(["Glucosa", "Asistente IA", "Reportes"])

# --- PESTAÑA 1: GLUCOSA ---
with tabs[0]:
    st.subheader("Registrar glucosa")
    valor = st.number_input("Valor mg/dL", min_value=0.0, step=1.0, key="input_glucosa")

    if st.button("Guardar Registro"):
        guardar_glucosa(valor)
        st.success("Dato guardado correctamente")
        st.rerun()

    df = glucosa_df()
    if not df.empty:
        st.subheader("Historial con semáforo")
        # Mostramos columnas relevantes
        df_display = df[["fecha_str", "hora", "valor"]].copy()
        styled = df_display.style.applymap(color_glucosa, subset=["valor"])
        st.dataframe(styled, use_container_width=True)

        st.subheader("Evolución Temporal")
        st.line_chart(df.set_index("fecha")["valor"])

# --- PESTAÑA 2: ASISTENTE IA (Sintaxis V1 Corregida) ---
with tabs[1]:
    st.subheader("Nexus AI Chat")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Entrada de texto (Nota: SpeechRecognition y pyttsx3 se omiten por ser incompatibles con servidores web)
    texto_usuario = st.text_input("Escribe tu consulta aquí:", key="chat_input")

    if st.button("Consultar IA"):
        if texto_usuario:
            try:
                # Llamada corregida para la nueva versión de la API
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": texto_usuario}]
                )
                respuesta = response.choices[0].message.content
                
                st.session_state.chat_history.append({"u": texto_usuario, "ai": respuesta})
                
                st.markdown(f"**Tú:** {texto_usuario}")
                st.info(f"**Nexus AI:** {respuesta}")
            except Exception as e:
                st.error(f"Error en la conexión con OpenAI: {e}")
        else:
            st.warning("Por favor, escribe algo.")

# --- PESTAÑA 3: REPORTES ---
with tabs[2]:
    st.subheader("Exportar Datos")
    
    if st.button("Generar PDF de Historial"):
        df = glucosa_df()
        if not df.empty:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "Reporte de Glucosa - Nexus AI", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", size=12)
            for i, row in df.iterrows():
                linea = f"Fecha: {row['fecha_str']} | Hora: {row['hora']} | Valor: {row['valor']} mg/dL"
                pdf.cell(200, 10, linea, ln=True)

            pdf.output("reporte_nexus.pdf")
            st.success("PDF generado con éxito")
            
            with open("reporte_nexus.pdf", "rb") as f:
                st.download_button("Descargar PDF", f, file_name="reporte_nexus.pdf")
        else:
            st.error("No hay datos para generar el reporte.")

    st.markdown("---")
    st.markdown("### Enlaces de Contacto")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("[📲 Enviar por WhatsApp](https://wa.me/123456789)")
    with col2:
        st.markdown("[📧 Enviar por Gmail](mailto:test@gmail.com)")
