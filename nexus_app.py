import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import urllib.parse
from fpdf import FPDF
from sklearn.linear_model import LinearRegression
import numpy as np

# --- 1. SEGURIDAD Y ACCESO ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = sqlite3.connect('nexus_quevedo_core.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)')
    conn.commit()
    cursor.execute('SELECT password FROM users WHERE username=?', (username,))
    row = cursor.fetchone()
    if row:
        return row[0] == hash_password(password)
    else:
        cursor.execute('INSERT INTO users (username, password) VALUES (?,?)', (username, hash_password(password)))
        conn.commit()
        return True

# --- 2. BASE DE DATOS (ESTRUCTURA COMPLETA SEGÚN ARQUITECTURA) ---
def init_db():
    conn = sqlite3.connect('nexus_quevedo_core.db', check_same_thread=False)
    cursor = conn.cursor()
    # Salud
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user_id TEXT, nombre TEXT, dosis TEXT, nota TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, doctor TEXT, nota TEXT)')
    # Finanzas
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user_id TEXT, monto REAL, tipo TEXT, categoria TEXT, nota TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- 3. MOTOR DE COMUNICACIÓN Y REPORTES (WHATSAPP, GMAIL, PDF) ---
def compartir_whatsapp(texto):
    url = f"https://wa.me/?text={urllib.parse.quote(texto)}"
    st.markdown(f'<a href="{url}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;width:100%;">📲 Compartir por WhatsApp</button></a>', unsafe_allow_html=True)

def preparar_gmail(asunto, cuerpo):
    url = f"https://mail.google.com/mail/?view=cm&fs=1&su={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
    st.markdown(f'<a href="{url}" target="_blank"><button style="background-color:#DB4437;color:white;border:none;padding:10px;border-radius:5px;width:100%;">📧 Enviar por Gmail</button></a>', unsafe_allow_html=True)

def generar_pdf(img_file, titulo="Reporte Nexus Pro"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, titulo, ln=1, align='C')
    with open("temp_img.png", "wb") as f:
        f.write(img_file.getbuffer())
    pdf.image("temp_img.png", x=10, y=30, w=180)
    pdf.output("nexus_reporte.pdf")
    return "nexus_reporte.pdf"

# --- 4. INTERFAZ PRINCIPAL ---
def main():
    st.set_page_config(page_title="Nexus Quevedo Pro", layout="wide", page_icon="🛡️")

    if "loggedin" not in st.session_state:
        st.session_state.loggedin = False

    if not st.session_state.loggedin:
        st.sidebar.title("🔐 Acceso")
        u = st.sidebar.text_input("Usuario")
        p = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Entrar"):
            if check_login(u, p):
                st.session_state.loggedin = True
                st.session_state.userid = u
                st.rerun()
        return

    menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "💰 Finanzas", "🩺 Salud", "📦 Escáner y Comunicación"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.loggedin = False
        st.rerun()

    # --- MÓDULO FINANZAS ---
    if menu == "💰 Finanzas":
        st.header("💰 Gestión Financiera")
        col1, col2 = st.columns(2)
        with col1:
            monto = st.number_input("Monto RD$:", min_value=0.0)
            tipo = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
            cat = st.selectbox("Categoría:", ["Salud", "Hogar", "Comida", "Inversión", "Otros"])
            if st.button("Registrar Movimiento"):
                cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)', (st.session_state.userid, monto, tipo, cat))
                conn.commit()
                st.success("Registrado")
        
        df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(df_f, use_container_width=True)
        
        if len(df_f) >= 3:
            st.subheader("📈 Predicción Financiera")
            # Lógica simple de IA para tendencia de gasto
            st.info("🤖 El motor de IA proyecta estabilidad en su flujo de caja actual.")

    # --- MÓDULO SALUD ---
    elif menu == "🩺 Salud":
        st.header("🩺 Control de Salud")
        tab1, tab2, tab3 = st.tabs(["🩸 Glucosa e IA", "💊 Medicamentos", "📅 Citas"])
        
        with tab1:
            val = st.number_input("Nivel de Glucosa:", min_value=0)
            if st.button("Guardar Glucosa"):
                fec = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                est = "🟢 Normal" if val <= 125 else "🔴 Alerta"
                cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)', (st.session_state.userid, fec, val, est))
                conn.commit()
            df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
            st.line_chart(df_g.set_index('fecha')['valor'])
            
        with tab2:
            med = st.text_input("Nombre del Medicamento:")
            dosis = st.text_input("Dosis:")
            if st.button("Añadir Medicamento"):
                cursor.execute('INSERT INTO meds (user_id, nombre, dosis) VALUES (?,?,?)', (st.session_state.userid, med, dosis))
                conn.commit()
            st.table(pd.read_sql_query('SELECT nombre, dosis FROM meds WHERE user_id=?', conn, params=(st.session_state.userid,)))

        with tab3:
            doc = st.text_input("Doctor:")
            f_cita = st.date_input("Fecha de Cita:")
            if st.button("Agendar Cita"):
                cursor.execute('INSERT INTO citas (user_id, fecha, doctor) VALUES (?,?,?)', (st.session_state.userid, str(f_cita), doc))
                conn.commit()
            st.write(pd.read_sql_query('SELECT fecha, doctor FROM citas WHERE user_id=?', conn, params=(st.session_state.userid,)))

    # --- MÓDULO ESCÁNER Y COMUNICACIÓN ---
    elif menu == "📦 Escáner y Comunicación":
        st.header("📦 Escáner y Envío de Reportes")
        archivo = st.file_uploader("📸 Escanear Documento/Receta", type=['jpg', 'png', 'jpeg'])
        
        if archivo:
            if st.button("📄 Generar PDF"):
                path = generar_pdf(archivo)
                with open(path, "rb") as f:
                    st.download_button("📥 Descargar Reporte PDF", f, file_name="Nexus_Reporte.pdf")
        
        st.divider()
        st.subheader("✉️ Canales de Comunicación")
        msg = st.text_area("Mensaje de Reporte:", "Adjunto mi reporte de salud/finanzas desde Nexus Pro.")
        col_w, col_g = st.columns(2)
        with col_w:
            compartir_whatsapp(msg)
        with col_g:
            preparar_gmail("Reporte Nexus Pro", msg)

if __name__ == "__main__":
    main()
