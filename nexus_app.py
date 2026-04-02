import streamlit as st
import pandas as pd
import sqlite3
import datetime
from fpdf import FPDF
import numpy as np
import requests
from openai import OpenAI
from PIL import Image
import pytesseract
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression
import io

# 🔐 CONFIGURACIÓN SEGURA
st.set_page_config(page_title="Nexus AI GOD", layout="wide")

# Conexión moderna a OpenAI usando los Secrets de Streamlit
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

DB = "nexus_god.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def run(q, p=()):
    with conn() as c:
        cur = c.cursor()
        cur.execute(q, p)
        c.commit()
        return cur.fetchall()

# -------------------------
# BASE DE DATOS
# -------------------------
def init():
    run('''CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)''')
    run('''CREATE TABLE IF NOT EXISTS medicamentos(id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, dosis TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS citas(id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS escaneos(id INTEGER PRIMARY KEY, fecha TEXT, codigo TEXT, producto TEXT, info TEXT, tipo TEXT)''')

init()

# -------------------------
# FUNCIONES
# -------------------------
def guardar_glucosa(v):
    run("INSERT INTO glucosa VALUES(NULL,?,?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v))

def listar_glucosa():
    return pd.DataFrame(run("SELECT * FROM glucosa"), columns=["id","fecha","valor"])

def guardar_scan(codigo, producto, info, tipo):
    run("INSERT INTO escaneos VALUES(NULL,?,?,?,?,?)", (datetime.datetime.now(), codigo, producto, info, tipo))

def listar_scans():
    return pd.DataFrame(run("SELECT * FROM escaneos ORDER BY fecha DESC"), columns=["id","fecha","codigo","producto","info","tipo"])

def buscar_producto(codigo):
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{codigo}.json"
        data = requests.get(url).json()
        if data["status"] == 1:
            p = data["product"]
            nombre = p.get("product_name", "Desconocido")
            marca = p.get("brands", "")
            calorias = p.get("nutriments", {}).get("energy-kcal_100g", "N/A")
            ingredientes = p.get("ingredients_text", "No disponible")
            info = f"🔥 Calorías: {calorias} kcal\n🥗 Ingredientes: {ingredientes[:150]}..."
            return f"{nombre} ({marca})", info
        return "Producto no encontrado", ""
    except: return "Error", ""

# -------------------------
# IA (VERSION MODERNA)
# -------------------------
def chat(p):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":p}]
    )
    return r.choices[0].message.content

def analizar_medicamento(nombre):
    return chat(f"Explica qué es el medicamento {nombre}, para qué sirve y precauciones.")

def evaluar_producto(producto, info):
    df = listar_glucosa()
    contexto = f"Glucosa reciente: {df.tail(5)['valor'].tolist()}" if not df.empty else ""
    return chat(f"Producto: {producto}\nInfo: {info}\n{contexto}\n¿Es recomendable para mi salud?")

# -------------------------
# UI (INTERFAZ)
# -------------------------
st.title("🧠 Nexus AI GOD MODE")

tabs = st.tabs(["Glucosa", "Escáner Inteligente", "Historial", "Dashboard", "Asistente IA"])

with tabs[0]:
    v = st.number_input("Glucosa mg/dL", key="val_glucosa")
    if st.button("Guardar", key="btn_glucosa"):
        guardar_glucosa(v)
        st.rerun()
    st.dataframe(listar_glucosa())

with tabs[1]:
    img = st.camera_input("Escanea producto o medicamento", key="cam_principal")
    if img:
        image = Image.open(img)
        decoded = decode(np.array(image))
        if decoded:
            codigo = decoded[0].data.decode("utf-8")
            st.success(f"Código: {codigo}")
            producto, info = buscar_producto(codigo)
            st.info(producto)
            st.text(info)
            tipo = st.selectbox("Tipo", ["alimento","medicamento"], key="sel_tipo")
            if tipo == "medicamento":
                if st.button("Analizar medicamento", key="btn_med"):
                    st.warning(analizar_medicamento(producto))
            else:
                if st.button("Evaluar salud", key="btn_salud"):
                    st.success(evaluar_producto(producto, info))
            if st.button("Guardar en historial", key="btn_hist"):
                guardar_scan(codigo, producto, info, tipo)
                st.success("Guardado")
        else: st.warning("No detectado")

with tabs[2]:
    st.dataframe(listar_scans())

with tabs[3]:
    df_pred = listar_glucosa()
    if len(df_pred) >= 5:
        df_pred["t"] = range(len(df_pred))
        model = LinearRegression().fit(df_pred[["t"]], df_pred["valor"])
        pred = model.predict([[len(df_pred)]])[0]
        st.info(f"Predicción próxima: {pred:.1f}")
    else: st.info("Datos insuficientes")

with tabs[4]:
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    p_chat = st.text_input("Pregunta", key="input_chat")
    if st.button("Enviar", key="btn_chat_send"):
        r_chat = chat(p_chat)
        st.session_state.chat_history.append(("Tú", p_chat))
        st.session_state.chat_history.append(("IA", r_chat))
    for rol, msg in st.session_state.chat_history:
        st.markdown(f"**{rol}:** {msg}")

# GENERAR PDF (DESCARGABLE)
if st.sidebar.button("Generar Reporte PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200,10,"Reporte Nexus AI",ln=True)
    for _, r in listar_glucosa().iterrows():
        pdf.cell(200,10,f"{r['fecha']} - {r['valor']}",ln=True)
    pdf_out = pdf.output(dest='S').encode('latin-1')
    st.sidebar.download_button("📥 Descargar PDF", data=pdf_out, file_name="reporte.pdf")
