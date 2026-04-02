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
openai.api_key = "TUAPIKEYAQUI"
st.set_page_config(page_title="Nexus AI Personal", layout="wide")

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
# FUNCIONES DE BORRADO
# -------------------------
def eliminar_registro(tabla, id_registro):
    run(f"DELETE FROM {tabla} WHERE id = ?", (id_registro,))
    st.rerun()

# -------------------------
# UI - SIDEBAR
# -------------------------
with st.sidebar:
    st.title("🚀 Nexus Control")
    st.divider()
    st.link_button("💬 WhatsApp", "https://web.whatsapp.com")
    st.link_button("📧 Gmail", "https://mail.google.com")

# -------------------------
# TABS PRINCIPALES
# -------------------------
tabs = st.tabs(["🩸 Salud", "💊 Meds", "📅 Citas", "💸 Finanzas", "🔍 Escáner", "🤖 IA Chat"])

# --- SALUD (GLUCOSA) CON BORRADO ---
with tabs[0]:
    c1, c2 = st.columns([1, 2])
    with c1:
        val = st.number_input("Medición (mg/dL)", min_value=0.0, step=1.0)
        nota = st.text_input("Nota (ej. Ayunas)")
        if st.button("Registrar Glucosa"):
            run("INSERT INTO glucosa VALUES(NULL,?,?,?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), val, nota))
            st.rerun()
    
    with c2:
        df_g = pd.DataFrame(run("SELECT * FROM glucosa ORDER BY id DESC"), columns=["id", "fecha", "valor", "nota"])
        if not df_g.empty:
            st.write("### Historial de Glucosa")
            for i, row in df_g.iterrows():
                col_data, col_btn = st.columns([4, 1])
                col_data.write(f"**{row['fecha']}**: {row['valor']} mg/dL ({row['nota']})")
                if col_btn.button("🗑️ Borrar", key=f"del_glu_{row['id']}"):
                    eliminar_registro("glucosa", row['id'])

# --- MEDICAMENTOS CON BORRADO ---
with tabs[1]:
    n = st.text_input("Medicamento")
    d = st.text_input("Dosis")
    if st.button("Añadir Med"):
        run("INSERT INTO medicamentos VALUES(NULL,?,?,?)", (datetime.date.today(), n, d))
        st.rerun()
    
    df_m = pd.DataFrame(run("SELECT * FROM medicamentos"), columns=["id", "fecha", "nombre", "dosis"])
    for i, row in df_m.iterrows():
        col_m1, col_m2 = st.columns([4, 1])
        col_m1.write(f"💊 {row['nombre']} - {row['dosis']}")
        if col_m2.button("🗑️", key=f"del_med_{row['id']}"):
            eliminar_registro("medicamentos", row['id'])

# --- CITAS CON BORRADO ---
with tabs[2]:
    f_cita = st.date_input("Fecha")
    doc = st.text_input("Doctor")
    esp = st.text_input("Especialidad")
    if st.button("Agendar"):
        run("INSERT INTO citas VALUES(NULL,?,?,?)", (str(f_cita), doc, esp))
        st.rerun()
    
    df_c = pd.DataFrame(run("SELECT * FROM citas"), columns=["id", "fecha", "doctor", "especialidad"])
    for i, row in df_c.iterrows():
        col_c1, col_c2 = st.columns([4, 1])
        col_c1.write(f"📅 {row['fecha']} | {row['doctor']} ({row['especialidad']})")
        if col_c2.button("🗑️", key=f"del_cita_{row['id']}"):
            eliminar_registro("citas", row['id'])

# --- FINANZAS CON BORRADO ---
with tabs[3]:
    tipo = st.radio("Tipo", ["ingreso", "gasto"], horizontal=True)
    monto = st.number_input("Monto ($)", min_value=0.0)
    cat = st.selectbox("Categoría", ["Salud", "Comida", "Sueldo", "Otros"])
    if st.button("Guardar Movimiento"):
        run("INSERT INTO finanzas VALUES(NULL,?,?,?,?)", (datetime.datetime.now().strftime("%Y-%m-%d"), tipo, monto, cat))
        st.rerun()
    
    df_f = pd.DataFrame(run("SELECT * FROM finanzas ORDER BY id DESC"), columns=["id", "fecha", "tipo", "monto", "cat"])
    for i, row in df_f.iterrows():
        col_f1, col_f2 = st.columns([4, 1])
        color = "🟢" if row['tipo'] == "ingreso" else "🔴"
        col_f1.write(f"{color} {row['fecha']} | {row['cat']} | ${row['monto']}")
        if col_f2.button("🗑️", key=f"del_fin_{row['id']}"):
            eliminar_registro("finanzas", row['id'])

# --- ESCÁNER ---
with tabs[4]:
    cam = st.camera_input("Escanear")
    # ... (Misma lógica de escaneo que el código anterior)

# --- IA CHAT ---
with tabs[5]:
    # ... (Misma lógica de chat que el código anterior)
    st.write("Chat disponible")
