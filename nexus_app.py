import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import requests
import openai
from fpdf import FPDF
import matplotlib.pyplot as plt
from PIL import Image
import pytesseract
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression

# -------------------------
# CONFIG
# -------------------------
openai.api_key = "TUAPIKEYAQUI"

st.set_page_config(page_title="Nexus AI COMPLETO", layout="wide")

DB = "nexusfullfinal.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def run(q, p=()):
    with conn() as c:
        cur = c.cursor()
        cur.execute(q, p)
        c.commit()
        return cur.fetchall()

# -------------------------
# DB INITIALIZATION
# -------------------------
def init():
    run('''CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)''')
    run('''CREATE TABLE IF NOT EXISTS medicamentos(id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, dosis TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS citas(id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS finanzas(id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL)''')
    run('''CREATE TABLE IF NOT EXISTS escaneos(id INTEGER PRIMARY KEY, fecha TEXT, codigo TEXT, producto TEXT, tipo TEXT)''')

init()

# -------------------------
# FUNCIONES SALUD Y FINANZAS
# -------------------------
def guardar_glucosa(v):
    run("INSERT INTO glucosa VALUES(NULL,?,?)", (datetime.datetime.now(), v))

def listar_glucosa():
    return pd.DataFrame(run("SELECT * FROM glucosa"), columns=["id", "fecha", "valor"])

def guardar_medicamento(n, d):
    run("INSERT INTO medicamentos VALUES(NULL,?,?,?)", (datetime.datetime.now(), n, d))

def listar_meds():
    return pd.DataFrame(run("SELECT * FROM medicamentos"), columns=["id", "fecha", "nombre", "dosis"])

def guardar_cita(f, d):
    run("INSERT INTO citas VALUES(NULL,?,?)", (f, d))

def listar_citas():
    return pd.DataFrame(run("SELECT * FROM citas"), columns=["id", "fecha", "doctor"])

def guardar_finanza(t, m):
    run("INSERT INTO finanzas VALUES(NULL,?,?,?)", (datetime.datetime.now(), t, m))

def listar_finanzas():
    return pd.DataFrame(run("SELECT * FROM finanzas"), columns=["id", "fecha", "tipo", "monto"])

def balance():
    df = listar_finanzas()
    if df.empty: 
        return 0
    return df[df.tipo == "ingreso"].monto.sum() - df[df.tipo == "gasto"].monto.sum()

# -------------------------
# ESCÁNER
# -------------------------
def escanear_codigo(img):
    decoded = decode(np.array(img))
    if decoded:
        return decoded[0].data.decode("utf-8")
    return None

def buscar_producto(codigo):
    try:
        data = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{codigo}.json").json()
        if data["status"] == 1:
            p = data["product"]
            nombre = p.get("product_name", "Desconocido")
            calorias = p.get("nutriments", {}).get("energy-kcal_100g", "N/A")
            return f"{nombre} - {calorias} kcal"
        return "No encontrado"
    except:
        return "Error"

# -------------------------
# IA
# -------------------------
def prediccion():
    df = listar_glucosa()
    if len(df) < 5: 
        return "Datos insuficientes"
    df["t"] = range(len(df))
    model = LinearRegression()
    model.fit(df[["t"]], df["valor"])
    return f"Predicción: {model.predict([[len(df)]])[0]:.1f}"

def chat(p):
    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": p}]
    )
    return r["choices"][0]["message"]["content"]

# -------------------------
# SEMÁFORO GLUCOSA
# -------------------------
def color_glucosa(valor):
    if 90 <= valor <= 130:
        return "background-color: lightgreen"
    elif 130 < valor <= 160:
        return "background-color: yellow"
    elif valor > 160:
        return "background-color: red"
    else:
        return "background-color: lightgray"

# -------------------------
# UI STREAMLIT
# -------------------------
st.title("🧠 Nexus AI COMPLETO")

tabs = st.tabs([
    "Glucosa",
    "Medicamentos",
    "Citas",
    "Finanzas",
    "Escáner",
    "Dashboard",
    "IA Chat"
])

# TABS: GLUCOSA
with tabs[0]:
    v = st.number_input("Valor")
    if st.button("Guardar glucosa"):
        guardar_glucosa(v)
        st.rerun()
    
    df = listar_glucosa()
    if not df.empty:
        st.dataframe(df.style.applymap(color_glucosa, subset=["valor"]))
        
        # Gráfico con colores
        colors = df["valor"].apply(lambda x: 
            "green" if 90 <= x <= 130 else 
            "yellow" if 130 < x <= 160 else 
            "red")
        
        plt.figure(figsize=(8, 4))
        plt.scatter(df["fecha"], df["valor"], c=colors)
        plt.plot(df["fecha"], df["valor"], color="blue", alpha=0.3)
        st.pyplot(plt)

# TABS: MEDICAMENTOS
with tabs[1]:
    n = st.text_input("Nombre")
    d = st.text_input("Dosis")
    if st.button("Guardar medicamento"):
        guardar_medicamento(n, d)
        st.rerun()
    st.dataframe(listar_meds())

# TABS: CITAS
with tabs[2]:
    f = st.date_input("Fecha")
    doc = st.text_input("Doctor")
    if st.button("Guardar cita"):
        guardar_cita(str(f), doc)
        st.rerun()
    st.dataframe(listar_citas())

# TABS: FINANZAS
with tabs[3]:
    t = st.selectbox("Tipo", ["ingreso", "gasto"])
    m = st.number_input("Monto")
    if st.button("Guardar finanza"):
        guardar_finanza(t, m)
        st.rerun()
    st.dataframe(listar_finanzas())
    st.metric("Balance", balance())

# TABS: ESCÁNER
with tabs[4]:
    img = st.camera_input("Escanear código")
    if img:
        image = Image.open(img)
        codigo = escanear_codigo(image)
        if codigo:
            producto = buscar_producto(codigo)
            st.success(producto)
            if st.button("Guardar"):
                run("INSERT INTO escaneos VALUES(NULL,?,?,?,?)",
                    (datetime.datetime.now(), codigo, producto, "scan"))
        else:
            st.warning("No detectado")

# TABS: DASHBOARD
with tabs[5]:
    st.info(prediccion())
    st.metric("Balance Total", balance())

# TABS: IA CHAT
with tabs[6]:
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
st.sidebar.markdown("### Accesos Rápidos")
st.sidebar.markdown("[WhatsApp](https://web.whatsapp.com)")
st.sidebar.markdown("[Gmail](https://mail.google.com)")

if st.button("Generar PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte Nexus AI", ln=True, align='C')
    pdf.output("reporte.pdf")
    st.success("PDF generado con éxito")
