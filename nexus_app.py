import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import base64
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURACIÓN Y ESTILO (Montserrat/Poppins) ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #0E1117; }
    .stMetric { background-color: #161B22; padding: 15px; border-radius: 10px; border: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS (Backend & DB Logic) ---
def init_db():
    conn = sqlite3.connect('nexus_pro_soberano.db', check_same_thread=False)
    c = conn.cursor()
    # Usuarios
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)')
    # Salud (Independencia Total)
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user TEXT, nombre TEXT, dosis TEXT, hora TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, doctor TEXT, motivo TEXT)')
    # Finanzas
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, cat TEXT, fecha TEXT)')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- 3. MOTOR DE IA & LÓGICA PREDICTIVA ---
def motor_ia_salud(valor):
    if valor < 70: return "🔴 ALERTA: Hipoglucemia", "Urgente: Consuma carbohidratos rápido."
    if 70 <= valor <= 125: return "🟢 NORMAL", "Excelente control."
    if 126 <= valor <= 160: return "🟡 PRECAUCIÓN", "Nivel elevado. Revise su última comida."
    return "🔴 ALERTA CRÍTICA", "¡Atención! Contacte a su médico inmediatamente."

def motor_ia_finanzas(balance):
    if balance < 0: return "⚠️ Déficit Detectado", "Sus gastos superan sus ingresos. Ajuste su presupuesto."
    return "✅ Salud Financiera", "Tiene saldo a favor para ahorro o inversión."

# --- 4. SEGURIDAD ---
def encriptar(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 5. INTERFAZ DASHBOARD PRINCIPAL ---
if 'login' not in st.session_state: st.session_state['login'] = False

if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO - Acceso Inteligente")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type='password')
    if st.button("Iniciar"):
        c.execute('SELECT password FROM usuarios WHERE user = ?', (u,))
        data = c.fetchone()
        if data and data[0] == encriptar(p):
            st.session_state['login'], st.session_state['user'] = True, u
            st.rerun()
        elif not data:
            c.execute('INSERT INTO usuarios VALUES (?,?)', (u, encriptar(p)))
            conn.commit()
            st.success("Cuenta creada. Inicie sesión.")
else:
    # --- BARRA LATERAL (Navegación del Diagrama) ---
    st.sidebar.header(f"Bienvenido, {st.session_state['user']}")
    menu = st.sidebar.radio("Dashboard Principal", ["💰 Finanzas", "🏥 Salud", "📸 Escáner & PDF", "🚪 Salir"])

    # --- MÓDULO FINANZAS ---
    if menu == "💰 Finanzas":
        st.header("Módulo de Finanzas e Ingresos")
        col1, col2 = st.columns([1, 2])
        with col1:
            monto = st.number_input("Monto (RD$):", min_value=0.0)
            tipo = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
            cat = st.selectbox("Categoría:", ["Comida", "Salud", "Servicios", "Inversión"])
            if st.button("Registrar Transacción"):
                f = datetime.datetime.now().strftime("%Y-%m-%d")
                c.execute('INSERT INTO finanzas (user, monto, tipo, cat, fecha) VALUES (?,?,?,?,?)', (st.session_state['user'], monto, tipo, cat, f))
                conn.commit()
        
        with col2:
            df_f = pd.read_sql_query('SELECT monto, tipo FROM finanzas WHERE user=?', conn, params=(st.session_state['user'],))
            ing = df_f[df_f['tipo']=='Ingreso']['monto'].sum()
            gas = df_f[df_f['tipo']=='Gasto']['monto'].sum()
            bal = ing - gas
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos", f"{ing:,.2f}")
            c2.metric("Gastos", f"{gas:,.2f}")
            c3.metric("Presupuesto Actual", f"{bal:,.2f}")
            
            # PREDICCIÓN FINANCIERA (Motor IA)
            st.subheader("💡 Predicción Financiera")
            estado, consejo = motor_ia_finanzas(bal)
            st.info(f"**{estado}:** {consejo}")

    # --- MÓDULO SALUD ---
    elif menu == "🏥 Salud":
        st.header("Módulo de Salud Inteligente")
        t1, t2, t3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])
        
        with t1:
            val = st.number_input("Nivel de Glucosa:", min_value=0.0)
            if st.button("Guardar Glucosa"):
                f = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                est, _ = motor_ia_salud(val)
                c.execute('INSERT INTO glucosa (user, fecha, valor, estado) VALUES (?,?,?,?)', (st.session_state['user'], f, val, est))
                conn.commit()
            
            # MOTOR IA SALUD
            est_ia, cons_ia = motor_ia_salud(val)
            st.metric("Estado (Semáforo)", est_ia)
            st.warning(cons_ia)

        with t2:
            n_med = st.text_input("Nombre Medicamento")
            d_med = st.text_input("Dosis")
            if st.button("Agregar"):
                c.execute('INSERT INTO meds (user, nombre, dosis) VALUES (?,?,?)', (st.session_state['user'], n_med, d_med))
                conn.commit()
            st.table(pd.read_sql_query('SELECT nombre, dosis FROM meds WHERE user=?', conn, params=(st.session_state['user'],)))

        with t3:
            f_cita = st.date_input("Fecha Cita")
            doc = st.text_input("Doctor")
            if st.button("Agendar"):
                c.execute('INSERT INTO citas (user, fecha, doctor) VALUES (?,?,?)', (st.session_state['user'], str(f_cita), doc))
                conn.commit()
            st.dataframe(pd.read_sql_query('SELECT fecha, doctor FROM citas WHERE user=?', conn, params=(st.session_state['user'],)))

    # --- ESCÁNER & PDF ---
    elif menu == "📸 Escáner & PDF":
        st.header("Escáner y Visor de Documentos")
        up = st.file_uploader("Subir Análisis (PDF)", type=['pdf'])
        if up:
            base64_pdf = base64.b64encode(up.read()).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)
            st.success("Documento cargado correctamente en el sistema.")

    elif menu == "🚪 Salir":
        st.session_state['login'] = False
        st.rerun()
