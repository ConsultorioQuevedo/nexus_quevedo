import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
import urllib.parse
import os
from fpdf import FPDF
from sklearn.linear_model import LinearRegression
import numpy as np

# --- 1. SEGURIDAD Y ACCESO ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = sqlite3.connect('nexus_quevedo_pro.db', check_same_thread=False)
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

# --- 2. FUNCIÓN DE AUTO-REPARACIÓN Y BASE DE DATOS ---
def init_db():
    # Cambiamos el nombre a 'nexus_quevedo_pro.db' para forzar una base de datos limpia
    # Esto evita tener que borrar archivos manualmente en Streamlit Cloud.
    db_name = 'nexus_quevedo_pro.db'
    conn = sqlite3.connect(db_name, check_same_thread=False)
    cursor = conn.cursor()
    
    # Creamos todas las tablas de su arquitectura profesional
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user_id TEXT, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, doctor TEXT, nota TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user_id TEXT, monto REAL, tipo TEXT, categoria TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- 3. MOTOR DE REPORTES (PDF) ---
def generar_pdf_estudio(img_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "Nexus Pro - Reporte de Estudio Médico", ln=1, align='C')
    with open("temp_scan.png", "wb") as f:
        f.write(img_file.getbuffer())
    pdf.image("temp_scan.png", x=10, y=30, w=180)
    pdf.output("reporte_nexus.pdf")
    return "reporte_nexus.pdf"

# --- 4. INTERFAZ PRINCIPAL (DASHBOARD) ---
def main():
    st.set_page_config(page_title="Nexus Quevedo Pro", layout="wide", page_icon="🛡️")

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

    # Menú de Navegación Profesional
    st.sidebar.title(f"👤 {st.session_state.userid}")
    menu = st.sidebar.radio("Menú", ["🩺 Salud e IA", "💰 Finanzas", "📅 Citas Médicas", "📦 Escáner y Docs"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.loggedin = False
        st.rerun()

    # --- MÓDULO SALUD e IA ---
    if menu == "🩺 Salud e IA":
        st.header("🩺 Control de Salud")
        col_in, col_viz = st.columns([1, 2])
        
        with col_in:
            val = st.number_input("Valor Glucosa (mg/dL):", min_value=0)
            if st.button("Guardar Glucosa"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                est = "🟢 NORMAL" if val <= 125 else "🔴 ALERTA"
                cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)', 
                               (st.session_state.userid, fec, val, est))
                conn.commit()
                st.success("Dato guardado correctamente")

        df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
        with col_viz:
            st.subheader("Historial Reciente")
            st.dataframe(df_g.tail(10), use_container_width=True)
            if len(df_g) >= 5:
                X = np.arange(len(df_g)).reshape(-1, 1)
                y = df_g['valor'].values
                model = LinearRegression().fit(X, y)
                pred = model.predict([[len(df_g) + 1]])
                st.metric("🤖 Predicción IA (Próxima)", f"{pred[0]:.1f} mg/dL")

        st.divider()
        st.subheader("💊 Medicamentos")
        nmed = st.text_input("Nombre de Medicina:")
        dmed = st.text_input("Dosis:")
        if st.button("Registrar Medicina"):
            cursor.execute('INSERT INTO meds (user_id, nombre, dosis) VALUES (?,?,?)', (st.session_state.userid, nmed, dmed))
            conn.commit()
            st.rerun()
        df_m = pd.read_sql_query('SELECT * FROM meds WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.table(df_m)

    # --- MÓDULO FINANZAS ---
    elif menu == "💰 Finanzas":
        st.header("💰 Gestión de Finanzas")
        monto = st.number_input("Monto (RD$):", min_value=0.0)
        cat = st.selectbox("Categoría:", ["Salud", "Comida", "Hogar", "Otros"])
        if st.button("Registrar Gasto"):
            cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)',
                           (st.session_state.userid, monto, "Gasto", cat))
            conn.commit()
            st.success("Gasto registrado")
        
        df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(df_f, use_container_width=True)

    # --- MÓDULO CITAS ---
    elif menu == "📅 Citas Médicas":
        st.header("📅 Agenda de Citas")
        doc = st.text_input("Doctor/Especialista:")
        fec_c = st.date_input("Fecha de Cita:")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (user_id, fecha, doctor) VALUES (?,?,?)', (st.session_state.userid, str(fec_c), doc))
            conn.commit()
            st.success("Cita agendada")
        df_c = pd.read_sql_query('SELECT * FROM citas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(df_c)

    # --- MÓDULO DOCUMENTOS ---
    elif menu == "📦 Escáner y Docs":
        st.header("📦 Escáner a PDF")
        archivo = st.file_uploader("Subir foto de estudio", type=['jpg', 'png', 'jpeg'])
        if archivo and st.button("📄 Convertir a PDF Profesional"):
            path = generar_pdf_estudio(archivo)
            with open(path, "rb") as f:
                st.download_button("📥 Descargar Reporte", f, file_name="Reporte_Nexus.pdf")
        
        st.divider()
        st.subheader("🗑️ Gestión de Registros (Borrado)")
        t_del = st.selectbox("Seleccionar Módulo:", ["glucosa", "finanzas", "meds", "citas"])
        id_del = st.number_input("ID a eliminar:", min_value=0)
        if st.button("Eliminar Registro"):
            cursor.execute(f'DELETE FROM {t_del} WHERE id=? AND user_id=?', (id_del, st.session_state.userid))
            conn.commit()
            st.warning(f"Registro {id_del} eliminado.")
            st.rerun()

if __name__ == "__main__":
    main()
