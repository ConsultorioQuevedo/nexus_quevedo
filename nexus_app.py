import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import requests
import openai
from fpdf import FPDF
from PIL import Image
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression
import speech_recognition as sr
import pyttsx3

openai.api_key = "TU_API_KEY_AQUI"

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Nexus AI PRO", layout="wide")

st.markdown("""
<style>
body {background-color: #0e1117; color: white;}
.stDataFrame td {
    text-align: center !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# LOGIN
# -------------------------
if "login" not in st.session_state:
    st.session_state.login = False

def login():
    st.title("🔐 Nexus AI")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "1234":
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Error")

if not st.session_state.login:
    login()
    st.stop()

# -------------------------
# DB
# -------------------------
def conn():
    return sqlite3.connect("nexus.db", check_same_thread=False)

def run(q,p=()):
    with conn() as c:
        cur=c.cursor()
        cur.execute(q,p)
        c.commit()
        return cur.fetchall()

run("CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)")

# -------------------------
# FUNCIONES
# -------------------------
def guardar_glucosa(v):
    run("INSERT INTO glucosa VALUES(NULL,?,?)",(datetime.datetime.now(),v))

def glucosa_df():
    df = pd.DataFrame(run("SELECT * FROM glucosa"),columns=["id","fecha","valor"])
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["hora"] = df["fecha"].dt.strftime("%H:%M")
        df["fecha"] = df["fecha"].dt.strftime("%d/%m/%Y")
    return df

def color_glucosa(v):
    if v < 70:
        return "background-color: #3498db; color:white"   # azul
    elif v <= 140:
        return "background-color: #2ecc71; color:white"   # verde
    elif v <= 180:
        return "background-color: #f39c12; color:white"   # amarillo
    else:
        return "background-color: #e74c3c; color:white"   # rojo

# -------------------------
# UI
# -------------------------
st.title("🩺 Control de Glucosa Inteligente")

tabs = st.tabs(["Glucosa","IA","Reportes"])

# -------------------------
# GLUCOSA
# -------------------------
with tabs[0]:

    st.subheader("Registrar glucosa")
    valor = st.number_input("Valor mg/dL")

    if st.button("Guardar"):
        guardar_glucosa(valor)
        st.success("Guardado")
        st.rerun()

    df = glucosa_df()

    if not df.empty:

        st.subheader("Historial con semáforo")

        styled = df.style.applymap(color_glucosa, subset=["valor"])
        st.dataframe(styled, use_container_width=True)

        st.subheader("Evolución")
        st.line_chart(df["valor"])

# -------------------------
# IA
# -------------------------
with tabs[1]:

    if "chat" not in st.session_state:
        st.session_state.chat=[]

    if st.button("🎤 Hablar"):
        r = sr.Recognizer()
        with sr.Microphone() as s:
            st.info("Habla...")
            audio = r.listen(s)
        try:
            texto = r.recognize_google(audio, language="es-ES")
        except:
            texto = "No entendí"

        st.write("Tú:", texto)

        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":texto}]
        )

        respuesta = res["choices"][0]["message"]["content"]

        st.write("IA:", respuesta)

        engine = pyttsx3.init()
        engine.say(respuesta)
        engine.runAndWait()

# -------------------------
# REPORTES
# -------------------------
with tabs[2]:

    if st.button("Generar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        df = glucosa_df()

        for i,row in df.iterrows():
            pdf.cell(200,10,f"{row['fecha']} {row['hora']} - {row['valor']}", ln=True)

        pdf.output("reporte.pdf")
        st.success("PDF generado")

    st.markdown("### Compartir")
    st.markdown("[WhatsApp](https://wa.me/123456789)")
    st.markdown("[Gmail](mailto:test@gmail.com)")
