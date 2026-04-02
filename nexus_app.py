import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import requests
import openai
from fpdf import FPDF
from PIL import Image
import pytesseract
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression

# 🔐 API KEY
openai.api_key = "TU_API_KEY_AQUI"

# -------------------------
# CONFIG UI MODERNO
# -------------------------
st.set_page_config(page_title="Nexus AI", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1rem;}
.card {
    padding: 20px;
    border-radius: 15px;
    background-color: #1e1e1e;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# DB
# -------------------------
DB = "nexus_moderno.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def run(q,p=()):
    with conn() as c:
        cur=c.cursor()
        cur.execute(q,p)
        c.commit()
        return cur.fetchall()

def init():
    run("CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)")
    run("CREATE TABLE IF NOT EXISTS medicamentos(id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, dosis TEXT)")
    run("CREATE TABLE IF NOT EXISTS citas(id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)")
    run("CREATE TABLE IF NOT EXISTS finanzas(id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL)")
    run("CREATE TABLE IF NOT EXISTS escaneos(id INTEGER PRIMARY KEY, fecha TEXT, codigo TEXT, producto TEXT)")

init()

# -------------------------
# FUNCIONES
# -------------------------
def guardar_glucosa(v):
    run("INSERT INTO glucosa VALUES(NULL,?,?)",(datetime.datetime.now(),v))

def listar_glucosa():
    return pd.DataFrame(run("SELECT * FROM glucosa"),columns=["id","fecha","valor"])

def guardar_medicamento(n,d):
    run("INSERT INTO medicamentos VALUES(NULL,?,?,?)",(datetime.datetime.now(),n,d))

def listar_meds():
    return pd.DataFrame(run("SELECT * FROM medicamentos"),columns=["id","fecha","nombre","dosis"])

def guardar_cita(f,d):
    run("INSERT INTO citas VALUES(NULL,?,?)",(f,d))

def listar_citas():
    return pd.DataFrame(run("SELECT * FROM citas"),columns=["id","fecha","doctor"])

def guardar_finanza(t,m):
    run("INSERT INTO finanzas VALUES(NULL,?,?,?)",(datetime.datetime.now(),t,m))

def listar_finanzas():
    return pd.DataFrame(run("SELECT * FROM finanzas"),columns=["id","fecha","tipo","monto"])

def balance():
    df=listar_finanzas()
    if df.empty: return 0
    return df[df.tipo=="ingreso"].monto.sum()-df[df.tipo=="gasto"].monto.sum()

def escanear_codigo(img):
    decoded=decode(np.array(img))
    if decoded:
        return decoded[0].data.decode("utf-8")
    return None

def buscar_producto(codigo):
    try:
        data=requests.get(f"https://world.openfoodfacts.org/api/v0/product/{codigo}.json").json()
        if data["status"]==1:
            p=data["product"]
            nombre=p.get("product_name","Desconocido")
            cal=p.get("nutriments",{}).get("energy-kcal_100g","N/A")
            return f"{nombre} ({cal} kcal)"
        return "No encontrado"
    except:
        return "Error"

def prediccion():
    df=listar_glucosa()
    if len(df)<5: return "Datos insuficientes"
    df["t"]=range(len(df))
    model=LinearRegression()
    model.fit(df[["t"]],df["valor"])
    return f"Predicción: {model.predict([[len(df)]])[0]:.1f}"

def chat(p):
    r=openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":p}]
    )
    return r["choices"][0]["message"]["content"]

# -------------------------
# UI
# -------------------------
st.title("🧠 Nexus AI - Sistema Inteligente")

tabs=st.tabs(["Dashboard","Salud","Finanzas","Escáner","IA","Reportes"])

# DASHBOARD
with tabs[0]:
    col1,col2=st.columns(2)
    with col1:
        st.metric("💰 Balance", balance())
    with col2:
        st.metric("🩺 Promedio glucosa",
                  listar_glucosa()["valor"].mean() if not listar_glucosa().empty else 0)
    st.info(prediccion())

# SALUD
with tabs[1]:
    st.subheader("Glucosa")
    v=st.number_input("Valor mg/dL")
    if st.button("Guardar glucosa"):
        guardar_glucosa(v)
        st.rerun()

    df=listar_glucosa()
    if not df.empty:
        st.line_chart(df["valor"])

    st.subheader("Medicamentos")
    n=st.text_input("Nombre")
    d=st.text_input("Dosis")
    if st.button("Guardar medicamento"):
        guardar_medicamento(n,d)
        st.rerun()
    st.dataframe(listar_meds())

    st.subheader("Citas")
    f=st.date_input("Fecha")
    doc=st.text_input("Doctor")
    if st.button("Guardar cita"):
        guardar_cita(str(f),doc)
        st.rerun()
    st.dataframe(listar_citas())

# FINANZAS
with tabs[2]:
    t=st.selectbox("Tipo",["ingreso","gasto"])
    m=st.number_input("Monto")
    if st.button("Guardar movimiento"):
        guardar_finanza(t,m)
        st.rerun()
    st.dataframe(listar_finanzas())
    st.metric("Balance actual", balance())

# ESCÁNER
with tabs[3]:
    img=st.camera_input("Escanear código")
    if img:
        image=Image.open(img)
        codigo=escanear_codigo(image)
        if codigo:
            producto=buscar_producto(codigo)
            st.success(producto)
            run("INSERT INTO escaneos VALUES(NULL,?,?,?)",
                (datetime.datetime.now(),codigo,producto))
        else:
            st.warning("No detectado")

# IA
with tabs[4]:
    if "chat" not in st.session_state:
        st.session_state.chat=[]

    p=st.text_input("Pregunta")
    if st.button("Enviar"):
        r=chat(p)
        st.session_state.chat.append(("Tú",p))
        st.session_state.chat.append(("IA",r))

    for rol,msg in st.session_state.chat:
        st.markdown(f"**{rol}:** {msg}")

# REPORTES + COMUNICACIÓN
with tabs[5]:
    if st.button("Generar PDF"):
        pdf=FPDF()
        pdf.add_page()
        pdf.set_font("Arial",size=12)
        pdf.cell(200,10,"Reporte Nexus",ln=True)
        pdf.output("reporte.pdf")
        st.success("PDF generado")

    st.markdown("### 📲 Compartir")
    st.markdown("[WhatsApp](https://wa.me/123456789)")
    st.markdown("[Gmail](mailto:test@gmail.com)")
