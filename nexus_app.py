import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import base64

# --- 1. CONFIGURACIÓN DE SEGURIDAD DE LA BASE DE DATOS ---
# Usamos una función que asegura que la tabla 'usuarios' existe antes de cualquier otra cosa
def inicializar_sistema_seguro():
    conn = sqlite3.connect('nexus_pro_soberano.db', check_same_thread=False)
    c = conn.cursor()
    try:
        # Crear tablas siguiendo el diagrama de flujo
        c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL, estado TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user TEXT, nombre TEXT, dosis TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, doctor TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, cat TEXT, fecha TEXT)')
        conn.commit()
    except Exception as e:
        st.error(f"Error técnico de base de datos: {e}")
    return conn, c

conn, c = inicializar_sistema_seguro()

# --- 2. ESTILO Y UI ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #0E1117; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #238636; color: white; }
    </style>
    """, unsafe_allow_html=True)

def encriptar(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 3. SISTEMA DE ACCESO (LOGIN) ---
if 'login' not in st.session_state:
    st.session_state['login'] = False
    st.session_state['user'] = ""

if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO - Control Total")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Acceso")
        u_login = st.text_input("Usuario", key="u_log")
        p_login = st.text_input("Contraseña", type='password', key="p_log")
        if st.button("Entrar al Sistema"):
            # Verificación blindada
            c.execute('SELECT password FROM usuarios WHERE user = ?', (u_login,))
            res = c.fetchone()
            if res and res[0] == encriptar(p_login):
                st.session_state['login'] = True
                st.session_state['user'] = u_login
                st.rerun()
            else:
                st.error("Credenciales no válidas.")

    with col_b:
        st.subheader("Nuevo Registro")
        u_reg = st.text_input("Nombre de Usuario", key="u_reg")
        p_reg = st.text_input("Definir Contraseña", type='password', key="p_reg")
        if st.button("Crear mi Cuenta"):
            if u_reg and p_reg:
                try:
                    c.execute('INSERT INTO usuarios (user, password) VALUES (?,?)', (u_reg, encriptar(p_reg)))
                    conn.commit()
                    st.success("Cuenta creada. Ya puede entrar por la izquierda.")
                except:
                    st.warning("Ese nombre de usuario ya está ocupado.")

# --- 4. PANEL SOBERANO (DASHBOARD) ---
else:
    st.sidebar.title(f"Soberano: {st.session_state['user']}")
    menu = st.sidebar.radio("Módulos del Diagrama", ["💰 Finanzas", "🏥 Salud e IA", "📸 Escáner/PDF", "Salir"])

    if menu == "💰 Finanzas":
        st.header("Presupuesto e Inteligencia Financiera")
        m = st.number_input("Monto (RD$):", min_value=0.0)
        t = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
        if st.button("Registrar Transacción"):
            f = datetime.datetime.now().strftime("%Y-%m-%d")
            c.execute('INSERT INTO finanzas (user, monto, tipo, fecha) VALUES (?,?,?,?)', (st.session_state['user'], m, t, f))
            conn.commit()
            st.success("Dato guardado.")

        # Cálculo de Balance en tiempo real
        df_f = pd.read_sql_query('SELECT monto, tipo FROM finanzas WHERE user=?', conn, params=(st.session_state['user'],))
        ing = df_f[df_f['tipo']=='Ingreso']['monto'].sum()
        gas = df_f[df_f['tipo']=='Gasto']['monto'].sum()
        balance = ing - gas
        
        st.metric("Presupuesto Disponible", f"RD$ {balance:,.2f}", delta=f"{balance:,.2f}")
        if balance < 0: st.error("DÉFICIT: Sus gastos superan sus ingresos.")

    elif menu == "🏥 Salud e IA":
        tab1, tab2, tab3 = st.tabs(["Glucosa", "Meds", "Citas"])
        
        with tab1:
            gluc = st.number_input("Glucosa:", min_value=0.0)
            if st.button("Guardar Glucosa"):
                f = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                c.execute('INSERT INTO glucosa (user, fecha, valor) VALUES (?,?,?)', (st.session_state['user'], f, gluc))
                conn.commit()
            
            # Semáforo Inteligente
            if gluc > 0:
                if 70 <= gluc <= 125: st.success("🟢 NORMAL")
                elif 126 <= gluc <= 160: st.warning("🟡 PRECAUCIÓN")
                else: st.error("🔴 ALERTA CRÍTICA")

        with tab2:
            n_m = st.text_input("Medicamento")
            if st.button("Añadir"):
                c.execute('INSERT INTO meds (user, nombre) VALUES (?,?)', (st.session_state['user'], n_m))
                conn.commit()
            st.write(pd.read_sql_query('SELECT nombre FROM meds WHERE user=?', conn, params=(st.session_state['user'],)))

    elif menu == "📸 Escáner/PDF":
        up = st.file_uploader("Subir Análisis", type=['pdf'])
        if up:
            b64 = base64.b64encode(up.read()).decode('utf-8')
            st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf">', unsafe_allow_html=True)

    elif menu == "Salir":
        st.session_state['login'] = False
        st.rerun()
