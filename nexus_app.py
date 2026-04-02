import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import smtplib
from email.mime.text import MIMEText
# Nota: Para WhatsApp local sin complicaciones, usamos Twilio (requiere pip install twilio)
from twilio.rest import Client 

# --- 1. CONFIGURACIÓN DE CREDENCIALES (Complete aquí) ---
GMAIL_USER = "su_correo@gmail.com"
GMAIL_PASS = "su_contraseña_de_aplicacion"
TWILIO_SID = "su_sid_de_twilio"
TWILIO_TOKEN = "su_token_de_twilio"
TWILIO_PHONE = "whatsapp:+14155238886" # Número de Twilio
SU_WHATSAPP = "whatsapp:+1809XXXXXXX"  # Su número real

# --- 2. CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. BASE DE DATOS Y SEGURIDAD ---
def init_db():
    conn = sqlite3.connect('nexus_pro_total.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, cat TEXT, fecha TEXT)')
    conn.commit()
    return conn, c

conn, c = init_db()

def encriptar(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 4. INTEGRACIONES (GMAIL Y WHATSAPP) ---
def enviar_alerta_total(mensaje):
    # Enviar Gmail
    try:
        msg = MIMEText(mensaje)
        msg['Subject'] = 'NEXUS PRO: Alerta de Salud'
        msg['From'] = GMAIL_USER
        msg['To'] = GMAIL_USER
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
    except: pass

    # Enviar WhatsApp (Twilio)
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(body=mensaje, from_=TWILIO_PHONE, to=SU_WHATSAPP)
    except: pass

# --- 5. LÓGICA DE NEGOCIO ---
def semaforo_glucosa(v):
    if 90 <= v <= 125: return "🟢 NORMAL", "Todo bajo control."
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN", "Nivel elevado. Revisa tu dieta."
    return "🔴 ALERTA CRÍTICA", "¡Atención! Nivel fuera de rango seguro."

# --- 6. CONTROL DE ACCESO ---
if 'login' not in st.session_state: st.session_state['login'] = False

if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type='password')
    if st.button("Entrar"):
        c.execute('SELECT password FROM usuarios WHERE user = ?', (u,))
        data = c.fetchone()
        if data and data[0] == encriptar(p):
            st.session_state['login'], st.session_state['user'] = True, u
            st.rerun()
        elif not data: # Auto-registro para el primer uso
            c.execute('INSERT INTO usuarios VALUES (?,?)', (u, encriptar(p)))
            conn.commit()
            st.success("Usuario creado. Presione Entrar de nuevo.")
else:
    menu = st.sidebar.radio("NEXUS PRO", ["🩸 Salud", "💰 Finanzas", "📸 Escáner", "Cerrar Sesión"])

    if menu == "🩸 Salud":
        st.header("Control de Glucosa con Alertas")
        val = st.number_input("Valor (mg/dL):", min_value=0.0)
        if st.button("Registrar y Notificar"):
            est, msg_alerta = semaforo_glucosa(val)
            f = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute('INSERT INTO glucosa (user, fecha, valor, estado) VALUES (?,?,?,?)', (st.session_state['user'], f, val, est))
            conn.commit()
            
            if "🔴" in est:
                enviar_alerta_total(f"ALERTA NEXUS PRO: Glucosa en {val} mg/dL ({est}). {msg_alerta}")
            st.subheader(f"Resultado: {est}")
            st.info(msg_alerta)

    elif menu == "💰 Finanzas":
        st.header("Presupuesto Inteligente")
        m = st.number_input("Monto (RD$):", min_value=0.0)
        t = st.selectbox("Operación:", ["Ingreso", "Gasto"])
        ca = st.selectbox("Categoría:", ["Salud", "Comida", "Vivienda", "Otros"])
        
        if st.button("Ejecutar Transacción"):
            f = datetime.datetime.now().strftime("%Y-%m-%d")
            c.execute('INSERT INTO finanzas (user, monto, tipo, cat, fecha) VALUES (?,?,?,?,?)', (st.session_state['user'], m, t, ca, f))
            conn.commit()
            st.success("Actualizado.")

        # Lógica de Balance (Resta Gastos de Ingresos)
        df_f = pd.read_sql_query('SELECT monto, tipo FROM finanzas WHERE user=?', conn, params=(st.session_state['user'],))
        ingresos = df_f[df_f['tipo'] == 'Ingreso']['monto'].sum()
        gastos = df_f[df_f['tipo'] == 'Gasto']['monto'].sum()
        balance = ingresos - gastos
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Ingresos", f"RD$ {ingresos:,.2f}")
        col2.metric("Total Gastos", f"RD$ {gastos:,.2f}", delta=f"-{gastos:,.2f}", delta_color="inverse")
        col3.metric("Presupuesto Disponible", f"RD$ {balance:,.2f}", delta=f"{balance:,.2f}")

    elif menu == "Cerrar Sesión":
        st.session_state['login'] = False
        st.rerun()
