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

# --- Configuración de Logs para Depuración ---
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
        # Registro automático del primer usuario
        cursor.execute('INSERT INTO users (username, password) VALUES (?,?)', (username, hash_password(password)))
        conn.commit()
        return True

# --- 2. BASE DE DATOS (PILAR DE PERSISTENCIA) ---
def init_db():
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tablas con user_id para independencia total
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user_id TEXT, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user_id TEXT, monto REAL, tipo TEXT, categoria TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- 3. COMUNICACIÓN (WHATSAPP Y GMAIL) ---
def enviar_whatsapp(mensaje):
    msg_encoded = urllib.parse.quote(mensaje)
    url = f"https://wa.me/?text={msg_encoded}"
    st.markdown(f'''<a href="{url}" target="_blank" style="text-decoration:none;">
                <button style="background-color:#25D366; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">
                📲 Enviar por WhatsApp</button></a>''', unsafe_allow_html=True)

def enviar_gmail(destinatario, mensaje):
    asunto = urllib.parse.quote("Reporte Nexus Quevedo")
    cuerpo = urllib.parse.quote(mensaje)
    # Link directo a Gmail Web
    url = f"https://mail.google.com/mail/?view=cm&fs=1&to={destinatario}&su={asunto}&body={cuerpo}"
    st.markdown(f'''<a href="{url}" target="_blank" style="text-decoration:none;">
                <button style="background-color:#D44638; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">
                📧 Enviar por Gmail</button></a>''', unsafe_allow_html=True)

# --- 4. REPORTES (PDF Y EXCEL) ---
def generar_pdf(img_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "Nexus Quevedo - Reporte de Estudio", ln=1, align='C')
    with open("temp_scan.png", "wb") as f:
        f.write(img_file.getbuffer())
    pdf.image("temp_scan.png", x=10, y=30, w=180)
    pdf.output("estudio_nexus.pdf")
    return "estudio_nexus.pdf"

# --- 5. INTELIGENCIA ARTIFICIAL ---
def predecir_salud(data):
    if len(data) >= 5:
        X = np.arange(len(data)).reshape(-1, 1)
        y = data['valor'].values
        model = LinearRegression().fit(X, y)
        pred = model.predict([[len(data) + 1]])
        return f"{pred[0]:.1f}"
    return None

# --- 6. INTERFAZ PRINCIPAL (ESTÉTICA PREMIUM) ---
def main():
    st.set_page_config(page_title="Nexus Quevedo", layout="wide", page_icon="🛡️")

    # Estilo CSS para Dark Mode y Botones
    st.markdown("""<style> .stButton>button {width: 100%; border-radius: 5px; height: 3em;} 
                .stMetric {background-color: #1e1e1e; padding: 15px; border-radius: 10px;} </style>""", unsafeallowhtml=True)

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
        st.info("Nexus Pro: Privacidad y Soberanía de Datos.")
        return

    # Barra Lateral
    st.sidebar.title(f"👤 {st.session_state.userid}")
    menu = st.sidebar.radio("Menú Principal", ["🩺 Salud", "💰 Finanzas", "📅 Citas", "📦 Reportes & Escáner"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.loggedin = False
        st.rerun()

    # --- MÓDULO SALUD ---
    if menu == "🩺 Salud":
        st.header("🩸 Monitoreo de Glucosa")
        col_in, col_viz = st.columns([1, 2])
        
        with col_in:
            val = st.number_input("Valor Glucosa (mg/dL):", min_value=0)
            if st.button("Guardar Registro"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                estado = "🟢 NORMAL" if 70 <= val <= 125 else "🟡 PRECAUCIÓN" if val <= 160 else "🔴 ALERTA"
                cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)', 
                               (st.session_state.userid, fec, val, estado))
                conn.commit()
                st.success("Dato guardado en SQLite.")

        df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
        
        with col_viz:
            if not df_g.empty:
                st.dataframe(df_g.tail(5), use_container_width=True)
                p = predecir_salud(df_g)
                if p:
                    st.metric("Predicción IA (Próxima)", f"{p} mg/dL")
        
        st.divider()
        st.subheader("📲 Comunicación Rápida")
        if not df_g.empty:
            ultimo = df_g.iloc[-1]
            msg = f"Sr. Quevedo - Reporte: Glucosa {ultimo['valor']} mg/dL ({ultimo['estado']}) - {ultimo['fecha']}"
            c1, c2 = st.columns(2)
            with c1: enviar_whatsapp(msg)
            with c2: 
                doc_mail = st.text_input("Email Destino:", "doctor@ejemplo.com")
                enviar_gmail(doc_mail, msg)

    # --- MÓDULO FINANZAS ---
    elif menu == "💰 Finanzas":
        st.header("💰 Gestión de Finanzas")
        monto = st.number_input("Monto (RD$):", min_value=0.0)
        tipo = st.selectbox("Tipo:", ["Gasto", "Ingreso"])
        cat = st.selectbox("Categoría:", ["Salud", "Alimentos", "Servicios", "Hogar", "Otros"])
        
        if st.button("Registrar Movimiento"):
            cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)',
                           (st.session_state.userid, monto, tipo, cat))
            conn.commit()
            st.success("Transacción registrada con éxito.")
        
        df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.table(df_f.tail(10))

    # --- MÓDULO REPORTES & PDF ---
    elif menu == "📦 Reportes & Escáner":
        st.header("📦 Generador de Reportes PDF")
        st.write("Suba una foto de su estudio médico para convertirla a un PDF profesional.")
        archivo = st.file_uploader("Cámara / Archivo", type=['jpg', 'jpeg', 'png'])
        
        if archivo:
            st.image(archivo, caption="Vista previa", width=300)
            if st.button("Convertir a PDF"):
                path = generar_pdf(archivo)
                with open(path, "rb") as f:
                    st.download_button("📥 Descargar PDF Médico", f, file_name="Estudio_Quevedo.pdf")

        st.divider()
        st.subheader("📤 Backup del Sistema")
        if st.button("Exportar todo a Excel"):
            df_all = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
            df_all.to_excel("Backup_Nexus.xlsx", index=False)
            with open("Backup_Nexus.xlsx", "rb") as f:
                st.download_button("📥 Descargar Excel", f, file_name="Backup_Nexus.xlsx")

if __name__ == "__main__":
    main()
