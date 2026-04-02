import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import base64

# --- 1. CONEXIÓN Y CREACIÓN FORZADA (Lógica del Diagrama) ---
def get_db_connection():
    conn = sqlite3.connect('nexus_pro_data.db', check_same_thread=False)
    c = conn.cursor()
    # ESTO ARREGLA EL ERROR: Crea las tablas ANTES de cualquier SELECT
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user TEXT, nombre TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, doctor TEXT)')
    conn.commit()
    return conn, c

conn, c = get_db_connection()

def encriptar(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. GESTIÓN DE SESIÓN ---
if 'login' not in st.session_state:
    st.session_state['login'] = False
    st.session_state['user'] = ""

# --- 3. PANTALLA DE ACCESO (Línea 55 Protegida) ---
if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO - Acceso Soberano")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Entrar")
        u = st.text_input("Usuario", key="l_user")
        p = st.text_input("Clave", type='password', key="l_pass")
        
        if st.button("Iniciar Sesión"):
            # Verificación de seguridad para evitar que el SELECT falle
            try:
                c.execute('SELECT password FROM usuarios WHERE user = ?', (u,))
                data = c.fetchone()
                if data and data[0] == encriptar(p):
                    st.session_state['login'] = True
                    st.session_state['user'] = u
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            except sqlite3.OperationalError:
                # Si por alguna razón falla, forzamos la creación y avisamos
                get_db_connection()
                st.warning("Sistema sincronizando... intente entrar de nuevo.")

    with col2:
        st.subheader("Registro")
        nu = st.text_input("Nuevo Usuario", key="r_user")
        np = st.text_input("Nueva Clave", type='password', key="r_pass")
        if st.button("Crear Cuenta"):
            try:
                c.execute('INSERT INTO usuarios VALUES (?,?)', (nu, encriptar(np)))
                conn.commit()
                st.success("Cuenta creada con éxito.")
            except:
                st.error("El usuario ya existe.")

# --- 4. DASHBOARD (Solo si entró) ---
else:
    st.sidebar.success(f"Usuario: {st.session_state['user']}")
    menu = st.sidebar.radio("Navegación", ["💰 Finanzas", "🏥 Salud", "📸 Visor PDF", "Cerrar Sesión"])

    if menu == "💰 Finanzas":
        st.header("Presupuesto e Ingresos")
        m = st.number_input("Monto RD$:", min_value=0.0)
        t = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
        if st.button("Registrar"):
            f = datetime.datetime.now().strftime("%Y-%m-%d")
            c.execute('INSERT INTO finanzas (user, monto, tipo, fecha) VALUES (?,?,?,?)', (st.session_state['user'], m, t, f))
            conn.commit()
        
        df_f = pd.read_sql_query('SELECT monto, tipo FROM finanzas WHERE user=?', conn, params=(st.session_state['user'],))
        bal = df_f[df_f['tipo']=='Ingreso']['monto'].sum() - df_f[df_f['tipo']=='Gasto']['monto'].sum()
        st.metric("Presupuesto Disponible", f"RD$ {bal:,.2f}")

    elif menu == "🏥 Salud":
        st.header("Salud Inteligente")
        gluc = st.number_input("Nivel de Glucosa:", min_value=0.0)
        if st.button("Guardar Glucosa"):
            f = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute('INSERT INTO glucosa (user, fecha, valor) VALUES (?,?,?)', (st.session_state['user'], f, gluc))
            conn.commit()
            if 70 <= gluc <= 125: st.success("🟢 NORMAL")
            elif 126 <= gluc <= 160: st.warning("🟡 PRECAUCIÓN")
            else: st.error("🔴 ALERTA")

    elif menu == "Cerrar Sesión":
        st.session_state['login'] = False
        st.rerun()
