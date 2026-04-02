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

# --- Seguridad: Login persistente ---
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

# --- Base de datos ---
def init_db():
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user_id TEXT, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user_id TEXT, monto REAL, tipo TEXT, categoria TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Funciones de Comunicación y Exportación ---
def enviar_whatsapp(mensaje):
    msg_encoded = urllib.parse.quote(mensaje)
    url = f"https://wa.me/?text={msg_encoded}"
    st.markdown(f'<a href="{url}" target="_blank">📲 Enviar Reporte por WhatsApp</a>', unsafe_allow_html=True)

def generar_pdf_estudio(img_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte Médico - Nexus Quevedo", ln=1, align='C')
    # Guardar temporalmente para el PDF
    with open("temp_img.png", "wb") as f:
        f.write(img_file.getbuffer())
    pdf.image("temp_img.png", x=10, y=30, w=180)
    pdf.output("reporte_nexus.pdf")
    return "reporte_nexus.pdf"

def exportar_excel(u_id):
    df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(u_id,))
    df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(u_id,))
    with pd.ExcelWriter("Nexus_Backup.xlsx") as writer:
        df_g.to_excel(writer, sheet_name="Salud", index=False)
        df_f.to_excel(writer, sheet_name="Finanzas", index=False)
    return "Nexus_Backup.xlsx"

# --- IA y Auxiliares ---
def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

def predecir_valores(data, columna):
    if len(data) >= 5: # Bajé a 5 para que lo pruebes más rápido
        X = np.arange(len(data)).reshape(-1,1)
        y = data[columna].values
        model = LinearRegression().fit(X,y)
        pred = model.predict([[len(data)+1]])
        return f"{pred[0]:.1f} ± 5"
    return None

# --- Interfaz Principal ---
def main():
    st.set_page_config(page_title="Nexus Quevedo", layout="wide")

    if "loggedin" not in st.session_state:
        st.session_state.loggedin = False

    if not st.session_state.loggedin:
        st.sidebar.title("🔐 Login")
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

    st.title(f"🛡️ Nexus Quevedo - Panel de {st.session_state.userid}")
    menu = st.sidebar.radio("Menú", ["Salud", "Finanzas", "Citas", "Reportes & Backup"])

    # --- SALUD ---
    if menu == "Salud":
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🩸 Glucosa")
            val = st.number_input("Valor Glucosa:", min_value=0)
            if st.button("Guardar"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)',
                               (st.session_state.userid, fec, val, obtener_semaforo(val)))
                conn.commit()
                st.success("Registrado")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(g_data, use_container_width=True)
        
        if not g_data.empty:
            p = predecir_valores(g_data, "valor")
            if p: st.info(f"🤖 IA: Predicción próxima toma: {p}")
            
            # Botón WhatsApp para salud
            ultimo = g_data.iloc[-1]
            if st.button("Enviar última glucosa por WhatsApp"):
                msg = f"Reporte Nexus: Glucosa {ultimo['valor']} mg/dL ({ultimo['estado']}) el {ultimo['fecha']}"
                enviar_whatsapp(msg)

    # --- FINANZAS ---
    elif menu == "Finanzas":
        st.subheader("💰 Gestión de Gastos")
        m_in = st.number_input("Monto (RD$):", min_value=0.0)
        tipo = st.selectbox("Tipo:", ["Gasto", "Ingreso"])
        cat = st.selectbox("Categoría:", ["Salud", "Comida", "Servicios", "Otros"])
        if st.button("Registrar Movimiento"):
            cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)',
                           (st.session_state.userid, m_in, tipo, cat))
            conn.commit()
            st.success("Finanza guardada")
        
        f_data = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(f_data)

    # --- REPORTES & BACKUP ---
    elif menu == "Reportes & Backup":
        st.subheader("📦 Exportación y Documentos")
        
        # Escáner / PDF
        st.write("### 📸 Generar PDF de Estudio")
        archivo = st.file_uploader("Subir imagen de estudio", type=['png', 'jpg', 'jpeg'])
        if archivo and st.button("Convertir a PDF"):
            pdf_path = generar_pdf_estudio(archivo)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Descargar PDF Médico", f, file_name=pdf_path)

        st.divider()
        
        # Backup Excel
        st.write("### 📥 Backup Completo")
        if st.button("Generar Backup en Excel"):
            ex_path = exportar_excel(st.session_state.userid)
            with open(ex_path, "rb") as f:
                st.download_button("📥 Descargar Excel", f, file_name=ex_path)

        st.divider()
        
        # Email (Simulado/Gmail link)
        st.write("### 📧 Reporte por Email")
        email_dest = st.text_input("Correo del Doctor:")
        if st.button("Preparar Email"):
            asunto = urllib.parse.quote("Reporte Nexus Quevedo")
            cuerpo = urllib.parse.quote("Adjunto envío mi reporte de salud generado por Nexus Pro.")
            st.markdown(f'<a href="mailto:{email_dest}?subject={asunto}&body={cuerpo}">✉️ Abrir Gmail/Outlook</a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
