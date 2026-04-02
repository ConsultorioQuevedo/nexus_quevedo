import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
import urllib.parse
from fpdf import FPDF
from sklearn.linear_model import LinearRegression
import numpy as np
import logging

# --- Configuración de Logs ---
logging.basicConfig(filename="error.log", level=logging.ERROR)

# --- 1. SEGURIDAD Y LOGIN ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
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

# --- 2. BASE DE DATOS (ARQUITECTURA COMPLETA) ---
def init_db():
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tablas independientes con 'userid' para multiusuario
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, userid TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, userid TEXT, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, userid TEXT, fecha TEXT, doctor TEXT, nota TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, userid TEXT, monto REAL, tipo TEXT, categoria TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- 3. COMUNICACIÓN Y REPORTES ---
def enviar_whatsapp(mensaje):
    msg_encoded = urllib.parse.quote(mensaje)
    url = f"https://wa.me/?text={msg_encoded}"
    st.markdown(f'**[📲 Enviar por WhatsApp]({url})**', unsafe_allow_html=True)

def enviar_gmail(destinatario, mensaje):
    asunto = urllib.parse.quote("Reporte Nexus Quevedo")
    cuerpo = urllib.parse.quote(mensaje)
    url = f"https://mail.google.com/mail/?view=cm&fs=1&to={destinatario}&su={asunto}&body={cuerpo}"
    st.markdown(f'**[📧 Abrir en Gmail]({url})**', unsafe_allow_html=True)

def generar_pdf_estudio(img_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "Nexus Quevedo - Reporte de Estudio Médico", ln=1, align='C')
    with open("temp_scan.png", "wb") as f:
        f.write(img_file.getbuffer())
    pdf.image("temp_scan.png", x=10, y=30, w=180)
    pdf.output("estudio_nexus.pdf")
    return "estudio_nexus.pdf"

# --- 4. INTERFAZ PRINCIPAL ---
def main():
    st.set_page_config(page_title="Nexus Quevedo Pro", layout="wide", page_icon="🛡️")

    # Estética CSS Premium
    st.markdown("""
        <style>
        .stButton>button {width: 100%; border-radius: 5px; height: 3em; background-color: #2e2e2e; color: white;}
        .stMetric {background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333;}
        </style>
        """, unsafe_allow_html=True)

    if "loggedin" not in st.session_state:
        st.session_state.loggedin = False

    if not st.session_state.loggedin:
        st.sidebar.title("🔐 Acceso Nexus")
        u = st.sidebar.text_input("Usuario")
        p = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Ingresar"):
            if check_login(u, p):
                st.session_state.loggedin = True
                st.session_state.userid = u
                st.rerun()
        return
    else:
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.loggedin = False
            st.rerun()

    st.title(f"🛡️ Panel Nexus - {st.session_state.userid}")
    menu = st.sidebar.radio("Navegación", ["🩺 Salud", "💰 Finanzas", "📅 Citas", "📦 Documentos & Backup"])

    # --- MÓDULO SALUD ---
    if menu == "🩺 Salud":
        st.header("🩺 Monitoreo de Salud")
        tab1, tab2 = st.tabs(["🩸 Glucosa", "💊 Medicamentos"])
        
        with tab1:
            col_in, col_viz = st.columns([1, 2])
            with col_in:
                val = st.number_input("Valor Glucosa:", min_value=0)
                if st.button("Guardar Glucosa"):
                    fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                    est = "🟢 NORMAL" if val <= 125 else "🔴 ALERTA"
                    cursor.execute('INSERT INTO glucosa (userid, fecha, valor, estado) VALUES (?,?,?,?)', 
                                   (st.session_state.userid, fec, val, est))
                    conn.commit()
                    st.success("Registrado")

            df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE userid=?', conn, params=(st.session_state.userid,))
            with col_viz:
                st.dataframe(df_g.tail(10), use_container_width=True)
                if len(df_g) >= 5:
                    X = np.arange(len(df_g)).reshape(-1, 1)
                    y = df_g['valor'].values
                    model = LinearRegression().fit(X, y)
                    pred = model.predict([[len(df_g) + 1]])
                    st.metric("🤖 Predicción IA", f"{pred[0]:.1f} mg/dL")

        with tab2:
            st.subheader("💊 Control de Medicamentos")
            n_med = st.text_input("Nombre del Medicamento:")
            d_med = st.text_input("Dosis (ej. 500mg):")
            h_med = st.time_input("Hora de toma:")
            if st.button("Registrar Medicina"):
                cursor.execute('INSERT INTO meds (userid, nombre, dosis, hora) VALUES (?,?,?,?)',
                               (st.session_state.userid, n_med, d_med, str(h_med)))
                conn.commit()
                st.success("Medicina guardada")
            df_m = pd.read_sql_query('SELECT * FROM meds WHERE userid=?', conn, params=(st.session_state.userid,))
            st.table(df_m)

    # --- MÓDULO FINANZAS ---
    elif menu == "💰 Finanzas":
        st.header("💰 Gestión de Finanzas")
        monto = st.number_input("Monto (RD$):", min_value=0.0)
        tipo = st.selectbox("Tipo:", ["Gasto", "Ingreso"])
        cat = st.selectbox("Categoría:", ["Comida", "Salud", "Servicios", "Hogar", "Otros"])
        if st.button("Registrar Transacción"):
            cursor.execute('INSERT INTO finanzas (userid, monto, tipo, categoria) VALUES (?,?,?,?)',
                           (st.session_state.userid, monto, tipo, cat))
            conn.commit()
            st.success("Movimiento registrado")
        
        df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE userid=?', conn, params=(st.session_state.userid,))
        st.dataframe(df_f, use_container_width=True)

    # --- MÓDULO CITAS ---
    elif menu == "📅 Citas":
        st.header("📅 Citas Médicas")
        doc = st.text_input("Doctor / Especialidad:")
        fecha_c = st.date_input("Fecha de la cita:")
        nota = st.text_area("Notas / Preparación:")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (userid, fecha, doctor, nota) VALUES (?,?,?,?)',
                           (st.session_state.userid, str(fecha_c), doc, nota))
            conn.commit()
            st.success("Cita agendada")
        df_c = pd.read_sql_query('SELECT * FROM citas WHERE userid=?', conn, params=(st.session_state.userid,))
        st.write(df_c)

    # --- MÓDULO DOCUMENTOS & BACKUP ---
    elif menu == "📦 Documentos & Backup":
        st.header("📦 Reportes y Seguridad")
        st.subheader("📸 Escáner a PDF")
        archivo = st.file_uploader("Subir imagen de estudio", type=['png', 'jpg', 'jpeg'])
        if archivo and st.button("Generar PDF Médico"):
            path = generar_pdf_estudio(archivo)
            with open(path, "rb") as f:
                st.download_button("📥 Descargar PDF", f, file_name="Estudio_Quevedo.pdf")

        st.divider()
        st.subheader("🗑️ Borrado por ID (Independencia Total)")
        tabla_del = st.selectbox("Seleccionar Tabla:", ["glucosa", "finanzas", "meds", "citas"])
        id_del = st.number_input("ID del registro a eliminar:", min_value=0)
        if st.button("Eliminar Registro Permanentemente"):
            cursor.execute(f'DELETE FROM {tabla_del} WHERE id=? AND userid=?', (id_del, st.session_state.userid))
            conn.commit()
            st.warning(f"ID {id_del} eliminado de {tabla_del}")

        st.divider()
        if st.button("📥 Generar Backup Excel Total"):
            df_all = pd.read_sql_query('SELECT * FROM glucosa WHERE userid=?', conn, params=(st.session_state.userid,))
            df_all.to_excel("Nexus_Backup.xlsx", index=False)
            with open("Nexus_Backup.xlsx", "rb") as f:
                st.download_button("📥 Descargar Excel", f, file_name="Backup_Nexus_Quevedo.xlsx")

if __name__ == "__main__":
    main()
