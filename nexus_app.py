import streamlit as st
import pandas as pd
import sqlite3
import datetime
from fpdf import FPDF
import numpy as np
import requests
import openai

from PIL import Image
import pytesseract
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression

# 🔐 API KEY
openai.api_key = "TU_API_KEY_AQUI"

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Nexus AI GOD", layout="wide")

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
# DB
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
    run("INSERT INTO glucosa VALUES(NULL,?,?)", (datetime.datetime.now(), v))

def listar_glucosa():
    return pd.DataFrame(run("SELECT * FROM glucosa"), columns=["id","fecha","valor"])

def guardar_scan(codigo, producto, info, tipo):
    run("INSERT INTO escaneos VALUES(NULL,?,?,?,?,?)",
        (datetime.datetime.now(), codigo, producto, info, tipo))

def listar_scans():
    return pd.DataFrame(run("SELECT * FROM escaneos ORDER BY fecha DESC"),
                        columns=["id","fecha","codigo","producto","info","tipo"])

# -------------------------
# 📦 PRODUCTOS + NUTRICIÓN
# -------------------------
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

    except:
        return "Error", ""

# -------------------------
# 💊 MEDICAMENTOS (IA)
# -------------------------
def analizar_medicamento(nombre):
    prompt = f"""
    Explica qué es el medicamento {nombre}, para qué sirve y precauciones.
    """

    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return r["choices"][0]["message"]["content"]

# -------------------------
# 📷 ESCÁNER
# -------------------------
def escanear_codigo(img):
    decoded = decode(np.array(img))
    if decoded:
        return decoded[0].data.decode("utf-8")
    return None

# -------------------------
# 🤖 IA SALUD PRODUCTO
# -------------------------
def evaluar_producto(producto, info):
    df = listar_glucosa()

    contexto = ""
    if not df.empty:
        contexto = f"Glucosa reciente: {df.tail(5)['valor'].tolist()}"

    prompt = f"""
    Producto: {producto}
    Info: {info}

    {contexto}

    Dime si este producto es recomendable para la salud del usuario.
    """

    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return r["choices"][0]["message"]["content"]

# -------------------------
# 🤖 CHAT
# -------------------------
def chat(p):
    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":p}]
    )
    return r["choices"][0]["message"]["content"]

# -------------------------
# 📊 IA PREDICCIÓN
# -------------------------
def prediccion():
    df = listar_glucosa()
    if len(df) < 5:
        return "Datos insuficientes"

    df["t"] = range(len(df))
    model = LinearRegression()
    model.fit(df[["t"]], df["valor"])
    pred = model.predict([[len(df)]])[0]

    return f"Predicción próxima: {pred:.1f}"

# -------------------------
# PDF
# -------------------------
def generar_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200,10,"Reporte Nexus AI",ln=True)

    for _, r in listar_glucosa().iterrows():
        pdf.cell(200,10,f"{r['fecha']} - {r['valor']}",ln=True)

    pdf.output("reporte.pdf")

# -------------------------
# UI
# -------------------------
st.title("🧠 Nexus AI GOD MODE")

tabs = st.tabs([
    "Glucosa",
    "Escáner Inteligente",
    "Historial",
    "Dashboard",
    "Asistente IA"
])

# GLUCOSA
with tabs[0]:
    v = st.number_input("Glucosa mg/dL")
    if st.button("Guardar"):
        guardar_glucosa(v)
        st.rerun()

    st.dataframe(listar_glucosa())

# ESCÁNER
with tabs[1]:
    img = st.camera_input("Escanea producto o medicamento")

    if img:
        image = Image.open(img)
        codigo = escanear_codigo(image)

        if codigo:
            st.success(f"Código: {codigo}")

            producto, info = buscar_producto(codigo)

            st.info(producto)
            st.text(info)

            tipo = st.selectbox("Tipo", ["alimento","medicamento"])

            if tipo == "medicamento":
                if st.button("Analizar medicamento"):
                    st.warning(analizar_medicamento(producto))

            else:
                if st.button("Evaluar salud"):
                    st.success(evaluar_producto(producto, info))

            if st.button("Guardar en historial"):
                guardar_scan(codigo, producto, info, tipo)
                st.success("Guardado")

        else:
            st.warning("No detectado")

# HISTORIAL
with tabs[2]:
    st.dataframe(listar_scans())

# DASHBOARD
with tabs[3]:
    st.info(prediccion())

# IA CHAT
with tabs[4]:
    if "chat" not in st.session_state:
        st.session_state.chat = []

    p = st.text_input("Pregunta")

    if st.button("Enviar"):
        r = chat(p)
        st.session_state.chat.append(("Tú", p))
        st.session_state.chat.append(("IA", r))

    for rol, msg in st.session_state.chat:
        st.markdown(f"**{rol}:** {msg}")

# EXTRAS
st.markdown("[WhatsApp](https://wa.me/123456789)")
st.markdown("[Gmail](mailto:test@gmail.com)")

if st.button("Generar PDF"):
    generar_pdf()
    st.success("PDF generado")
