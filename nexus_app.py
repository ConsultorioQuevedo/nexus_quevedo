import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import os

# ==========================================
# 1. BASE DE DATOS (PERSISTENCIA)
# ==========================================
def init_db():
    # Corregido: check_same_thread (con guion bajo)
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, monto REAL, tipo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS escaneo (id INTEGER PRIMARY KEY, fecha TEXT, archivo TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================
def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

def generar_pdf(img_file, nombre_archivo="escaneo.pdf"):
    # Corregido: Manejo de imagen para PDF
    pdf = FPDF()
    pdf.add_page()
    # Guardamos temporalmente para que FPDF la lea
    with open("temp_img.jpg", "wb") as f:
        f.write(img_file.getbuffer())
    pdf.image("temp_img.jpg", x=10, y=10, w=180)
    pdf.output(nombre_archivo, "F")
    return nombre_archivo

# ==========================================
# 3. MÓDULOS DE INTERFAZ
# ==========================================
def mostrar_finanzas():
    st.subheader("Gestión Financiera")
    # Corregido: number_input (con guion bajo)
    monto = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f", step=1.0)
    tipo = st.selectbox("Tipo de movimiento:", ["Ingreso", "Gasto"])
    if st.button("Registrar Movimiento"):
        cursor.execute('INSERT INTO finanzas (monto, tipo) VALUES (?,?)', (monto, tipo))
        conn.commit()
        st.success(f"{tipo} registrado: RD$ {monto:,.2f}")
    # Corregido: read_sql_query (con guion bajo)
    st.write(pd.read_sql_query('SELECT * FROM finanzas', conn))

def mostrar_salud():
    # Corregido: nombres de variables t_gluc, t_meds, etc.
    t_gluc, t_meds, t_citas, t_scan = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas", "📸 Escáner"])
    
    with t_gluc:
        val = st.number_input("Valor Glucosa:", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, estado))
            conn.commit()
            st.success("Registro guardado")
        st.write(pd.read_sql_query('SELECT * FROM glucosa', conn))

    with t_meds:
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        if st.button("Registrar Medicamento"):
            cursor.execute('INSERT INTO meds (nombre, dosis) VALUES (?,?)', (nmed, dmed))
            conn.commit()
        st.write(pd.read_sql_query('SELECT * FROM meds', conn))

    with t_citas:
        fc = st.date_input("Fecha")
        dc = st.text_input("Doctor")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(fc), dc))
            conn.commit()
        st.write(pd.read_sql_query('SELECT * FROM citas', conn))

    with t_scan:
        if st.checkbox("Abrir Escáner"):
            img = st.camera_input("Escanee documento")
            if img:
                pdf_file = generar_pdf(img, "documento.pdf")
                cursor.execute('INSERT INTO escaneo (fecha, archivo) VALUES (?,?)',
                               (datetime.datetime.now().strftime("%d/%m %H:%M"), pdf_file))
                conn.commit()
                st.success("Documento escaneado y guardado como PDF")

def generar_reportes():
    gdata = pd.read_sql_query('SELECT * FROM glucosa', conn)
    cdata = pd.read_sql_query('SELECT * FROM citas', conn)
    reporte = "📑 Reporte Nexus\n\n"
    reporte += "🩸 Glucosa:\n"
    for i , r in gdata.iterrows():
        reporte += f"- {r['fecha']}: {r['valor']} ({r['estado']})\n"
    reporte += "\n📅 Citas:\n"
    for i , c in cdata.iterrows():
        reporte += f"- {c['fecha']}: {c['doctor']}\n"
    
    st.text_area("Vista previa del reporte:", reporte, height=200)
    rep_enc = urllib.parse.quote(reporte)
    
    # WhatsApp y Gmail
    st.markdown(f'[📲 Enviar a WhatsApp](https://wa.me/?text={rep_enc})')
    gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Reporte+Nexus&body={rep_enc}"
    st.markdown(f'[📧 Enviar por Gmail]({gmail_url})')

# ==========================================
# 4. EJECUCIÓN PRINCIPAL
# ==========================================
def main():
    # Corregido: set_page_config
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    st.title("📊 Dashboard Principal - Finanzas & Salud Inteligente")
    
    t_fin, t_salud, t_rep = st.tabs(["💰 Finanzas", "🩺 Salud", "📤 Reportes"])
    
    with t_fin: mostrar_finanzas()
    with t_salud: mostrar_salud()
    with t_rep: generar_reportes()
    
    # Inteligencia Artificial
    g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
    if not g_data.empty:
        prom = g_data['valor'].mean()
        if prom > 140:
            st.warning(f"🤖 IA: Promedio de glucosa {prom:.1f}, está elevado. Considere ajustar dieta.")
        else:
            st.info(f"🤖 IA: Promedio de glucosa {prom:.1f}, dentro de rango saludable.")

if __name__ == "__main__":
    main()
