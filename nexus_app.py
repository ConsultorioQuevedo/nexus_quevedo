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

# --- 1. SEGURIDAD Y ACCESO ---
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

# --- 2. BASE DE DATOS (TODOS LOS MÓDULOS) ---
def init_db():
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    # Independencia Total: Tablas para cada entidad de su diagrama
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user_id TEXT, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, doctor TEXT, nota TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user_id TEXT, monto REAL, tipo TEXT, categoria TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- 3. MOTOR DE REPORTES Y COMUNICACIÓN ---
def enviar_whatsapp(mensaje):
    msg_encoded = urllib.parse.quote(mensaje)
    url = f"https://wa.me/?text={msg_encoded}"
    st.markdown(f'**[📲 Compartir por WhatsApp]({url})**', unsafe_allow_html=True)

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

    # Estética Dark Mode Profesional
    st.markdown("""
        <style>
        .stButton>button {width: 100%; border-radius: 8px; background-color: #2e2e2e; color: white;}
        .stMetric {background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #444;}
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

    # Menú Principal según su Arquitectura
    menu = st.sidebar.radio("Navegación", ["🩺 Salud Inteligente", "💰 Finanzas", "📅 Agenda de Citas", "📦 Documentos y Backup"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.loggedin = False
        st.rerun()

    # --- MÓDULO SALUD ---
    if menu == "🩺 Salud Inteligente":
        st.header("🩺 Gestión de Salud")
        tab1, tab2 = st.tabs(["🩸 Glucosa e IA", "💊 Medicamentos"])
        
        with tab1:
            col_in, col_viz = st.columns([1, 2])
            with col_in:
                val = st.number_input("Valor Glucosa (mg/dL):", min_value=0)
                if st.button("Guardar Glucosa"):
                    fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                    est = "🟢 NORMAL" if val <= 125 else "🔴 ALERTA"
                    cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)', 
                                   (st.session_state.userid, fec, val, est))
                    conn.commit()
                    st.success("Registrado")

            df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
            with col_viz:
                st.dataframe(df_g.tail(10), use_container_width=True)
                if len(df_g) >= 5:
                    X = np.arange(len(df_g)).reshape(-1, 1)
                    y = df_g['valor'].values
                    model = LinearRegression().fit(X, y)
                    pred = model.predict([[len(df_g) + 1]])
                    st.metric("🤖 IA: Próxima Tendencia", f"{pred[0]:.1f} mg/dL")

        with tab2:
            st.subheader("💊 Control de Medicamentos")
            n_med = st.text_input("Nombre:")
            d_med = st.text_input("Dosis:")
            h_med = st.time_input("Hora:")
            if st.button("Registrar Medicina"):
                cursor.execute('INSERT INTO meds (user_id, nombre, dosis, hora) VALUES (?,?,?,?)',
                               (st.session_state.userid, n_med, d_med, str(h_med)))
                conn.commit()
                st.rerun()
            df_m = pd.read_sql_query('SELECT * FROM meds WHERE user_id=?', conn, params=(st.session_state.userid,))
            st.table(df_m)

    # --- MÓDULO FINANZAS ---
    elif menu == "💰 Finanzas":
        st.header("💰 Control Financiero")
        monto = st.number_input("Monto (RD$):", min_value=0.0)
        tipo = st.selectbox("Tipo:", ["Gasto", "Ingreso"])
        cat = st.selectbox("Categoría:", ["Salud", "Comida", "Hogar", "Servicios", "Otros"])
        if st.button("Registrar Movimiento"):
            cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)',
                           (st.session_state.userid, monto, tipo, cat))
            conn.commit()
            st.success("Guardado")
        
        df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(df_f, use_container_width=True)

    # --- MÓDULO CITAS ---
    elif menu == "📅 Agenda de Citas":
        st.header("📅 Citas Médicas")
        doc = st.text_input("Especialista:")
        f_cita = st.date_input("Fecha:")
        nota = st.text_area("Notas:")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (user_id, fecha, doctor, nota) VALUES (?,?,?,?)',
                           (st.session_state.userid, str(f_cita), doc, nota))
            conn.commit()
            st.success("Cita Agendada")
        df_c = pd.read_sql_query('SELECT * FROM citas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(df_c)

    # --- MÓDULO DOCUMENTOS & BACKUP ---
    elif menu == "📦 Documentos y Backup":
        st.header("📦 Escáner y Seguridad")
        archivo = st.file_uploader("📸 Subir imagen de estudio (Escáner)", type=['png', 'jpg', 'jpeg'])
        if archivo and st.button("📄 Generar PDF Profesional"):
            path = generar_pdf_estudio(archivo)
            with open(path, "rb") as f:
                st.download_button("📥 Descargar Reporte PDF", f, file_name="Estudio_Nexus.pdf")

        st.divider()
        st.subheader("🗑️ Independencia de Datos (Borrado por ID)")
        t_borrar = st.selectbox("Tabla:", ["glucosa", "finanzas", "meds", "citas"])
        id_borrar = st.number_input("ID a eliminar:", min_value=0)
        if st.button("Eliminar Permanentemente"):
            cursor.execute(f'DELETE FROM {t_borrar} WHERE id=? AND user_id=?', (id_borrar, st.session_state.userid))
            conn.commit()
            st.warning(f"ID {id_borrar} borrado de {t_borrar}")
            st.rerun()

if __name__ == "__main__":
    main()
