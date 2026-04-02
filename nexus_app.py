import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import base64

# --- 1. CONFIGURACIÓN E INTERFAZ (Estilo Profesional) ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #0E1117; }
    .stMetric { background-color: #161B22; padding: 15px; border-radius: 10px; border: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BACKEND & BASE DE DATOS (Auto-Reparable) ---
def conectar_db():
    conn = sqlite3.connect('nexus_pro_data.db', check_same_thread=False)
    c = conn.cursor()
    # Crear todas las tablas del Diagrama de Flujo de inmediato
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user TEXT, nombre TEXT, dosis TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, doctor TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, cat TEXT, fecha TEXT)')
    conn.commit()
    return conn, c

conn, c = conectar_db()

# --- 3. MOTOR DE IA (Lógica Predictiva del Diagrama) ---
def motor_ia_salud(v):
    if v == 0: return "Esperando datos...", "Introduzca su nivel de glucosa."
    if 70 <= v <= 125: return "🟢 NORMAL", "Excelente control de salud."
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN", "Nivel elevado. Revise su dieta."
    return "🔴 ALERTA CRÍTICA", "Consulte a su médico inmediatamente."

def motor_ia_finanzas(ing, gas):
    bal = ing - gas
    if bal < 0: return f"RD$ {bal:,.2f}", "🔴 DÉFICIT: Gastos superan ingresos."
    return f"RD$ {bal:,.2f}", "🟢 SALUDABLE: Presupuesto con saldo a favor."

def encriptar(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 4. ACCESO Y LOGIN ---
if 'login' not in st.session_state: st.session_state['login'] = False

if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO - Acceso Soberano")
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("Identificarse")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type='password')
        if st.button("Entrar"):
            c.execute('SELECT password FROM usuarios WHERE user = ?', (u,))
            data = c.fetchone()
            if data and data[0] == encriptar(p):
                st.session_state['login'], st.session_state['user'] = True, u
                st.rerun()
            else: st.error("Usuario o clave incorrectos.")

    with col_r:
        st.subheader("Registrar Nueva Cuenta")
        nu = st.text_input("Nuevo Usuario")
        np = st.text_input("Nueva Contraseña", type='password')
        if st.button("Crear Cuenta"):
            try:
                c.execute('INSERT INTO usuarios VALUES (?,?)', (nu, encriptar(np)))
                conn.commit()
                st.success("Cuenta creada con éxito.")
            except: st.error("El usuario ya existe.")

# --- 5. DASHBOARD PRINCIPAL (Lógica de Diagrama) ---
else:
    st.sidebar.header(f"Soberano: {st.session_state['user']}")
    menu = st.sidebar.radio("MENÚ", ["💰 Finanzas", "🏥 Salud Inteligente", "📸 Visor PDF", "Cerrar Sesión"])

    if menu == "💰 Finanzas":
        st.header("Módulo de Finanzas & Presupuesto")
        col_ing, col_res = st.columns([1, 2])
        
        with col_ing:
            monto = st.number_input("Monto RD$:", min_value=0.0)
            tipo = st.selectbox("Operación:", ["Ingreso", "Gasto"])
            if st.button("Registrar"):
                f = datetime.datetime.now().strftime("%Y-%m-%d")
                c.execute('INSERT INTO finanzas (user, monto, tipo, fecha) VALUES (?,?,?,?)', (st.session_state['user'], monto, tipo, f))
                conn.commit()
        
        with col_res:
            df_f = pd.read_sql_query('SELECT monto, tipo FROM finanzas WHERE user=?', conn, params=(st.session_state['user'],))
            ing = df_f[df_f['tipo']=='Ingreso']['monto'].sum()
            gas = df_f[df_f['tipo']=='Gasto']['monto'].sum()
            bal_val, ia_msg = motor_ia_finanzas(ing, gas)
            
            st.metric("Presupuesto Disponible", bal_val, help=ia_msg)
            st.info(ia_msg)

    elif menu == "🏥 Salud Inteligente":
        st.header("Módulo de Salud & IA")
        t_gluc, t_meds, t_citas = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])
        
        with t_gluc:
            v_gluc = st.number_input("Valor Glucosa:", min_value=0.0)
            if st.button("Guardar Glucosa"):
                f = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute('INSERT INTO glucosa (user, fecha, valor) VALUES (?,?,?)', (st.session_state['user'], f, v_gluc))
                conn.commit()
            
            est_ia, cons_ia = motor_ia_salud(v_gluc)
            st.metric("Motor de IA: Estado", est_ia)
            st.warning(cons_ia)

        with t_meds:
            n_m = st.text_input("Medicamento")
            d_m = st.text_input("Dosis")
            if st.button("Añadir Med"):
                c.execute('INSERT INTO meds (user, nombre, dosis) VALUES (?,?,?)', (st.session_state['user'], n_m, d_m))
                conn.commit()
            st.table(pd.read_sql_query('SELECT nombre, dosis FROM meds WHERE user=?', conn, params=(st.session_state['user'],)))

        with t_citas:
            f_c = st.date_input("Fecha")
            d_c = st.text_input("Doctor")
            if st.button("Agendar"):
                c.execute('INSERT INTO citas (user, fecha, doctor) VALUES (?,?,?)', (st.session_state['user'], str(f_c), d_c))
                conn.commit()
            st.dataframe(pd.read_sql_query('SELECT fecha, doctor FROM citas WHERE user=?', conn, params=(st.session_state['user'],)))

    elif menu == "📸 Visor PDF":
        st.header("Escáner & Visor de Documentos")
        up = st.file_uploader("Subir Análisis (PDF)", type=['pdf'])
        if up:
            b64 = base64.b64encode(up.read()).decode('utf-8')
            pdf_html = f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf">'
            st.markdown(pdf_html, unsafe_allow_html=True)

    elif menu == "Cerrar Sesión":
        st.session_state['login'] = False
        st.rerun()
