import streamlit as st
import pandas as pd
import sqlite3
import datetime
import numpy as np
import requests
import openai
from fpdf import FPDF
import plotly.express as px
from PIL import Image
from pyzbar.pyzbar import decode
from sklearn.linear_model import LinearRegression

# -------------------------
# CONFIG & SEGURIDAD
# -------------------------
# Reemplaza con tu clave real
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
# DB INITIALIZATION
# -------------------------
def init():
    run('''CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, nota TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS medicamentos(id INTEGER PRIMARY KEY, fecha TEXT, nombre TEXT, dosis TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS citas(id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, especialidad TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS finanzas(id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL, categoria TEXT)''')
    run('''CREATE TABLE IF NOT EXISTS escaneos(id INTEGER PRIMARY KEY, fecha TEXT, codigo TEXT, producto TEXT, tipo TEXT)''')

init()

# -------------------------
# FUNCIONES DE APOYO
# -------------------------
def balance_total():
    res = run("SELECT tipo, monto FROM finanzas")
    if not res: return 0.0
    df = pd.DataFrame(res, columns=["tipo", "monto"])
    ingresos = df[df.tipo == "ingreso"]["monto"].sum()
    gastos = df[df.tipo == "gasto"]["monto"].sum()
    return ingresos - gastos

def color_glucosa_logic(val):
    if 90 <= val <= 130: return "background-color: #d4edda" # Verde
    elif 130 < val <= 160: return "background-color: #fff3cd" # Amarillo
    elif val > 160: return "background-color: #f8d7da" # Rojo
    return ""

# -------------------------
# UI - SIDEBAR
# -------------------------
with st.sidebar:
    st.title("🚀 Nexus Control")
    st.metric("Balance Actual", f"${balance_total():,.2f}")
    st.divider()
    st.link_button("💬 WhatsApp", "https://web.whatsapp.com")
    st.link_button("📧 Gmail", "https://mail.google.com")
    
    if st.button("🗑️ Borrar TODO el historial financiero"):
        if st.checkbox("Confirmar acción irreversible"):
            run("DELETE FROM finanzas")
            st.rerun()

# -------------------------
# TABS PRINCIPALES
# -------------------------
tabs = st.tabs(["📊 Dashboard", "🩸 Salud", "💊 Meds", "📅 Citas", "💸 Finanzas", "🔍 Escáner", "🤖 IA Chat"])

# --- DASHBOARD ---
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    c1.metric("Balance", f"${balance_total():,.2f}")
    
    ultima_g = run("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1")
    if ultima_g:
        c2.metric("Última Glucosa", f"{ultima_g[0][0]} mg/dL")
    
    prox_cita = run("SELECT fecha, doctor FROM citas WHERE fecha >= ? ORDER BY fecha ASC LIMIT 1", (str(datetime.date.today()),))
    if prox_cita:
        c3.metric("Próxima Cita", f"{prox_cita[0][1]}", help=f"Fecha: {prox_cita[0][0]}")

# --- SALUD (GLUCOSA) ---
with tabs[1]:
    col_in, col_hist = st.columns([1, 2])
    with col_in:
        val = st.number_input("Medición (mg/dL)", min_value=0.0, value=130.0, key="input_glu")
        nota = st.text_input("Nota (ej. Ayuna)", key="nota_glu")
        if st.button("Registrar Medición"):
            run("INSERT INTO glucosa VALUES(NULL,?,?,?)", 
                (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), val, nota))
            st.rerun()

    with col_hist:
        res_g = run("SELECT * FROM glucosa ORDER BY id DESC")
        if res_g:
            df_g = pd.DataFrame(res_g, columns=["id", "fecha", "valor", "nota"])
            # El fix de .map() para evitar el AttributeError
            st.dataframe(df_g.style.map(color_glucosa_logic, subset=["valor"]), use_container_width=True)
            
            with st.expander("Gestionar Registros de Salud"):
                for i, row in df_g.iterrows():
                    cols = st.columns([3, 1])
                    cols[0].write(f"{row['fecha']} - {row['valor']} mg/dL")
                    if cols[1].button("Borrar", key=f"del_g_{row['id']}"):
                        run("DELETE FROM glucosa WHERE id=?", (row['id'],))
                        st.rerun()

# --- MEDICAMENTOS ---
with tabs[2]:
    n_med = st.text_input("Nombre del Medicamento")
    d_med = st.text_input("Dosis / Horario")
    if st.button("Guardar Medicamento"):
        run("INSERT INTO medicamentos VALUES(NULL,?,?,?)", (str(datetime.date.today()), n_med, d_med))
        st.rerun()
    
    res_m = run("SELECT * FROM medicamentos")
    if res_m:
        for m in res_m:
            cols = st.columns([4, 1])
            cols[0].write(f"💊 {m[2]} - {m[3]}")
            if cols[1].button("Eliminar", key=f"del_m_{m[0]}"):
                run("DELETE FROM medicamentos WHERE id=?", (m[0],))
                st.rerun()

# --- CITAS ---
with tabs[3]:
    f_cita = st.date_input("Fecha de Cita")
    doc = st.text_input("Doctor / Clínica")
    esp = st.text_input("Especialidad")
    if st.button("Agendar Cita"):
        run("INSERT INTO citas VALUES(NULL,?,?,?)", (str(f_cita), doc, esp))
        st.rerun()
    
    res_c = run("SELECT * FROM citas ORDER BY fecha ASC")
    if res_c:
        df_c = pd.DataFrame(res_c, columns=["id", "fecha", "doctor", "especialidad"])
        st.dataframe(df_c[["fecha", "doctor", "especialidad"]], use_container_width=True)
        for c in res_c:
            if st.button(f"Borrar Cita con {c[2]}", key=f"del_c_{c[0]}"):
                run("DELETE FROM citas WHERE id=?", (c[0],))
                st.rerun()

# --- FINANZAS ---
with tabs[4]:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        t_fin = st.radio("Tipo de Movimiento", ["ingreso", "gasto"], horizontal=True)
        m_fin = st.number_input("Monto total", min_value=0.0)
        cat_fin = st.selectbox("Categoría", ["Salud", "Comida", "Sueldo", "Hogar", "Otros"])
        if st.button("Registrar Movimiento"):
            run("INSERT INTO finanzas VALUES(NULL,?,?,?,?)", 
                (datetime.datetime.now().strftime("%Y-%m-%d"), t_fin, m_fin, cat_fin))
            st.rerun()
    
    with col_f2:
        res_f = run("SELECT * FROM finanzas ORDER BY id DESC")
        if res_f:
            df_f = pd.DataFrame(res_f, columns=["id", "fecha", "tipo", "monto", "cat"])
            st.dataframe(df_f[["fecha", "tipo", "monto", "cat"]], use_container_width=True)
            for f in res_f:
                if st.button(f"Borrar ${f[3]} ({f[4]})", key=f"del_f_{f[0]}"):
                    run("DELETE FROM finanzas WHERE id=?", (f[0],))
                    st.rerun()

# --- ESCÁNER ---
with tabs[5]:
    st.write("### Escáner de Productos")
    cam = st.camera_input("Capturar código de barras")
    if cam:
        img = Image.open(cam)
        decoded = decode(np.array(img))
        if decoded:
            code = decoded[0].data.decode("utf-8")
            st.info(f"Código detectado: {code}")
            # Intento de búsqueda en API externa
            try:
                r = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{code}.json", timeout=5).json()
                if r.get("status") == 1:
                    p_name = r["product"].get("product_name", "Producto desconocido")
                    st.success(f"Encontrado: {p_name}")
                else:
                    st.warning("Producto no encontrado en OpenFoodFacts")
            except:
                st.error("No se pudo conectar con el servidor de búsqueda")
        else:
            st.warning("No se detectó ningún código claro")

# --- IA CHAT ---
with tabs[6]:
    st.write("### Consulta a Nexus AI")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("¿Qué quieres saber de tus datos?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                # Se le puede pasar contexto de la DB aquí si se desea
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Eres Nexus AI, asistente de salud y finanzas."}] + st.session_state.messages
                )["choices"][0]["message"]["content"]
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except:
                st.error("Error al conectar con OpenAI. Revisa tu API Key.")
