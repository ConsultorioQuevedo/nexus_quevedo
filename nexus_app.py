import streamlit as st
import pandas as pd
import sqlite3
import datetime
from fpdf import FPDF
import numpy as np
import requests
from openai import OpenAI  # Versión moderna
from PIL import Image
import pytesseract
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression
import io

# -------------------------
# CONFIG & SEGURIDAD
# -------------------------
st.set_page_config(page_title="Nexus AI GOD", layout="wide")

# Conectamos con la llave de forma segura
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except:
    st.error("Falta la API KEY en los Secrets de Streamlit.")

DB = "nexus_god.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def run_query(q, p=()):
    with get_conn() as c:
        cur = c.cursor()
        cur.execute(q, p)
        c.commit()
        return cur.fetchall()

# -------------------------
# BASE DE DATOS
# -------------------------
def init_db():
    run_query('''CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)''')
    run_query('''CREATE TABLE IF NOT EXISTS medicamentos(id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, dosis TEXT)''')
    run_query('''CREATE TABLE IF NOT EXISTS citas(id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)''')
    run_query('''CREATE TABLE IF NOT EXISTS escaneos(id INTEGER PRIMARY KEY, fecha TEXT, codigo TEXT, producto TEXT, info TEXT, tipo TEXT)''')

init_db()

# -------------------------
# FUNCIONES DE NEGOCIO
# -------------------------
def guardar_glucosa(v):
    run_query("INSERT INTO glucosa VALUES(NULL,?,?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), v))

def listar_glucosa():
    rows = run_query("SELECT * FROM glucosa")
    return pd.DataFrame(rows, columns=["id","fecha","valor"]) if rows else pd.DataFrame(columns=["id","fecha","valor"])

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
            info = f"Calorías: {calorias} kcal. Ingredientes: {ingredientes[:150]}..."
            return f"{nombre} ({marca})", info
        return "Producto no encontrado", ""
    except:
        return "Error de conexión", ""

# -------------------------
# INTELIGENCIA ARTIFICIAL (Moderna)
# -------------------------
def chat_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def evaluar_salud(producto, info):
    df = listar_glucosa()
    contexto = f"Glucosa reciente: {df.tail(5)['valor'].tolist()}" if not df.empty else "Sin datos previos."
    prompt = f"Producto: {producto}\nInfo: {info}\n{contexto}\n¿Es recomendable este producto para mi salud? Responde breve."
    return chat_ai(prompt)

# -------------------------
# INTERFAZ (UI)
# -------------------------
st.title("🧠 Nexus AI GOD MODE")

tabs = st.tabs(["Glucosa", "Escáner", "Historial", "Dashboard", "Asistente"])

with tabs[0]:
    v = st.number_input("Glucosa mg/dL", min_value=0.0, key="input_glucosa")
    if st.button("Guardar Glucosa", key="btn_glucosa"):
        guardar_glucosa(v)
        st.success("Registrado")
        st.rerun()
    st.dataframe(listar_glucosa(), use_container_width=True)

with tabs[1]:
    img_file = st.camera_input("Escanea código de barras", key="cam_nexus")
    if img_file:
        image = Image.open(img_file)
        decoded = decode(np.array(image))
        if decoded:
            codigo = decoded[0].data.decode("utf-8")
            st.success(f"Código detectado: {codigo}")
            prod, info = buscar_producto(codigo)
            st.subheader(prod)
            st.write(info)
            
            tipo = st.radio("Clasificar como:", ["Alimento", "Medicamento"], key="tipo_scan")
            if st.button("Analizar con IA", key="btn_ia_scan"):
                res = evaluar_salud(prod, info)
                st.info(res)
        else:
            st.warning("No se detectó código. Intenta centrarlo más.")

with tabs[3]:
    st.header("Análisis Predictivo")
    df_p = listar_glucosa()
    if len(df_p) > 4:
        df_p["t"] = range(len(df_p))
        model = LinearRegression()
        model.fit(df_p[["t"]], df_p["valor"])
        pred = model.predict([[len(df_p)]])[0]
        st.metric("Predicción Próxima", f"{pred:.1f} mg/dL")
    else:
        st.info("Necesitas al menos 5 registros para predecir tendencias.")

with tabs[4]:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    query = st.text_input("Hazme una pregunta sobre tu salud:", key="chat_input")
    if st.button("Preguntar", key="btn_chat"):
        respuesta = chat_ai(query)
        st.session_state.messages.append(("Tú", query))
        st.session_state.messages.append(("Nexus", respuesta))
    
    for user, msg in st.session_state.messages[::-1]:
        st.write(f"**{user}:** {msg}")

# -------------------------
# EXPORTAR (Sin errores de servidor)
# -------------------------
st.sidebar.markdown("---")
if st.sidebar.button("Generar Reporte PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(40, 10, "Reporte Nexus AI")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    
    df_pdf = listar_glucosa()
    for _, row in df_pdf.iterrows():
        pdf.cell(0, 10, f"Fecha: {row['fecha']} | Valor: {row['valor']} mg/dL", ln=True)
    
    # Esto hace que el PDF se descargue en tu PC
    pdf_output = pdf.output(dest='S').encode('latin-1')
    st.sidebar.download_button(label="📥 Descargar PDF", data=pdf_output, file_name="reporte_nexus.pdf", mime="application/pdf")
