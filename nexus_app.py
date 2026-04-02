import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import urllib.parse
from fpdf import FPDF
from sklearn.linear_model import LinearRegression
import numpy as np

# --- 1. SEGURIDAD ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = sqlite3.connect('nexus_total_pro.db', check_same_thread=False)
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

# --- 2. BASE DE DATOS UNIFICADA (Lógica Pro) ---
def init_db():
    conn = sqlite3.connect('nexus_total_pro.db', check_same_thread=False)
    cursor = conn.cursor()
    # Módulo Finanzas (Ingresos, Gastos y Presupuesto)
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user_id TEXT, monto REAL, tipo TEXT, categoria TEXT, fecha TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS presupuestos (id INTEGER PRIMARY KEY, user_id TEXT, categoria TEXT, limite REAL)')
    # Módulo Salud
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user_id TEXT, nombre TEXT, dosis TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, doctor TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- 3. MOTOR DE COMUNICACIÓN Y PDF ---
def enviar_whatsapp(texto):
    msg = urllib.parse.quote(texto)
    st.markdown(f'''<a href="https://wa.me/?text={msg}" target="_blank"><button style="background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px;">📲 WhatsApp</button></a>''', unsafe_allow_html=True)

def generar_pdf_estudio(img_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "Reporte Nexus Pro - Multiservicios Anael", ln=1, align='C')
    with open("temp.png", "wb") as f: f.write(img_file.getbuffer())
    pdf.image("temp.png", x=10, y=30, w=180)
    pdf.output("reporte.pdf")
    return "reporte.pdf"

# --- 4. INTERFAZ DASHBOARD PRINCIPAL ---
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

    menu = st.sidebar.radio("Navegación", ["💰 Finanzas e Ingresos", "🩺 Salud e IA", "📅 Citas y Agenda", "📦 Escáner y Envío"])
    
    # --- MÓDULO FINANZAS (PRESUPUESTO INCLUIDO) ---
    if menu == "💰 Finanzas e Ingresos":
        st.header("💰 Gestión Financiera Inteligente")
        t1, t2 = st.tabs(["📊 Ingresos & Gastos", "🎯 Definir Presupuesto"])
        
        with t2:
            st.subheader("Configurar Presupuesto Mensual")
            cat_p = st.selectbox("Categoría Presupuesto:", ["Salud", "Comida", "Hogar", "Servicios"])
            limite = st.number_input("Límite de Gasto (RD$):", min_value=0.0)
            if st.button("Establecer Presupuesto"):
                cursor.execute('INSERT INTO presupuestos (user_id, categoria, limite) VALUES (?,?,?)', (st.session_state.userid, cat_p, limite))
                conn.commit()
                st.success(f"Presupuesto para {cat_p} guardado.")

        with t1:
            col1, col2 = st.columns(2)
            with col1:
                monto = st.number_input("Monto (RD$):", min_value=0.0)
                tipo = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
                cat = st.selectbox("Categoría:", ["Comida", "Salud", "Hogar", "Servicios", "Otros"])
                if st.button("Registrar Movimiento"):
                    fec = datetime.datetime.now().strftime("%Y-%m-%d")
                    cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria, fecha) VALUES (?,?,?,?,?)', (st.session_state.userid, monto, tipo, cat, fec))
                    conn.commit()
                    st.success("Registrado.")

            # Comparativa vs Presupuesto
            df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
            df_p = pd.read_sql_query('SELECT * FROM presupuestos WHERE user_id=?', conn, params=(st.session_state.userid,))
            st.write("### Resumen vs Presupuesto")
            st.dataframe(df_f)

    # --- MÓDULO SALUD e IA ---
    elif menu == "🩺 Salud e IA":
        st.header("🩺 Salud Inteligente")
        val = st.number_input("Glucosa:", min_value=0)
        if st.button("Guardar"):
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            est = "🟢 NORMAL" if val <= 125 else "🔴 ALERTA"
            cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)', (st.session_state.userid, fec, val, est))
            conn.commit()
        
        df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.line_chart(df_g['valor'])
        if len(df_g) >= 5:
            X = np.arange(len(df_g)).reshape(-1, 1); y = df_g['valor'].values
            model = LinearRegression().fit(X, y); pred = model.predict([[len(df_g) + 1]])
            st.info(f"🤖 Predicción IA: {pred[0]:.1f} mg/dL")

    # --- MÓDULO ESCÁNER Y ENVÍO ---
    elif menu == "📦 Escáner y Envío":
        st.header("📦 Documentos y Comunicación")
        archivo = st.file_uploader("Subir estudio", type=['jpg', 'png', 'jpeg'])
        if archivo and st.button("📄 Generar PDF"):
            path = generar_pdf_estudio(archivo)
            with open(path, "rb") as f: st.download_button("📥 Descargar", f, file_name="Reporte.pdf")
        
        st.divider()
        txt = st.text_area("Mensaje:", "Reporte Nexus Pro enviado.")
        col_w, col_g = st.columns(2)
        with col_w: enviar_whatsapp(txt)
        with col_g: 
            st.markdown(f'<a href="https://mail.google.com/mail/?view=cm&fs=1&body={txt}" target="_blank"><button style="background-color:#DB4437; color:white; border:none; padding:10px; border-radius:5px;">📧 Gmail</button></a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
