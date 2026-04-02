import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import base64

# --- 1. CONEXIÓN REFORZADA (Anti-Errores) ---
def ejecutar_consulta(sql, params=()):
    """Función maestra para evitar bloqueos de base de datos"""
    with sqlite3.connect('nexus_pro_data.db', check_same_thread=False) as conn:
        c = conn.cursor()
        # ASEGURAR TABLAS ANTES DE CUALQUER COSA
        c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, fecha TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user TEXT, nombre TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, doctor TEXT)')
        
        # Ejecutar la consulta solicitada
        if sql:
            c.execute(sql, params)
            if sql.strip().upper().startswith("SELECT"):
                return c.fetchone() if "LIMIT 1" in sql or "WHERE user =" in sql else c.fetchall()
            conn.commit()
    return None

def encriptar(p): return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. ESTILO PROFESIONAL ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #0E1117; }
    </style>""", unsafe_allow_html=True)

# --- 3. LÓGICA DE ACCESO (PANTALLA DE ENTRADA) ---
if 'login' not in st.session_state:
    st.session_state['login'] = False
    st.session_state['user'] = ""

if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO - Acceso Soberano")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Entrar")
        u = st.text_input("Usuario", key="u_login")
        p = st.text_input("Clave", type='password', key="p_login")
        if st.button("Iniciar Sesión"):
            # Usamos la función blindada para que no falle la línea 55/60
            data = ejecutar_consulta('SELECT password FROM usuarios WHERE user = ?', (u,))
            if data and data[0] == encriptar(p):
                st.session_state['login'], st.session_state['user'] = True, u
                st.rerun()
            else: st.error("Credenciales incorrectas o usuario inexistente.")

    with col2:
        st.subheader("Registro")
        nu = st.text_input("Nuevo Usuario", key="nu_reg")
        np = st.text_input("Nueva Clave", type='password', key="np_reg")
        if st.button("Crear Cuenta"):
            try:
                ejecutar_consulta('INSERT INTO usuarios VALUES (?,?)', (nu, encriptar(np)))
                st.success("Cuenta creada. Ya puede entrar.")
            except: st.error("El usuario ya existe.")

# --- 4. DASHBOARD (Basado en su Diagrama de Flujo) ---
else:
    st.sidebar.title(f"Soberano: {st.session_state['user']}")
    menu = st.sidebar.radio("Navegación", ["💰 Finanzas", "🏥 Salud e IA", "📸 Visor PDF", "Cerrar Sesión"])

    if menu == "💰 Finanzas":
        st.header("Presupuesto e Inteligencia Financiera")
        m = st.number_input("Monto RD$:", min_value=0.0)
        t = st.selectbox("Operación:", ["Ingreso", "Gasto"])
        if st.button("Registrar Transacción"):
            f = datetime.datetime.now().strftime("%Y-%m-%d")
            ejecutar_consulta('INSERT INTO finanzas (user, monto, tipo, fecha) VALUES (?,?,?,?)', (st.session_state['user'], m, t, f))
            st.success("Registrado.")

        # Cálculo de Resta (Ingresos - Gastos)
        with sqlite3.connect('nexus_pro_data.db') as conn:
            df_f = pd.read_sql_query('SELECT monto, tipo FROM finanzas WHERE user=?', conn, params=(st.session_state['user'],))
        
        bal = df_f[df_f['tipo']=='Ingreso']['monto'].sum() - df_f[df_f['tipo']=='Gasto']['monto'].sum()
        st.metric("Presupuesto Disponible", f"RD$ {bal:,.2f}", delta=f"{bal:,.2f}")

    elif menu == "🏥 Salud e IA":
        st.header("Módulo de Salud Inteligente")
        gluc = st.number_input("Valor Glucosa:", min_value=0.0)
        if st.button("Guardar Glucosa"):
            f = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            ejecutar_consulta('INSERT INTO glucosa (user, fecha, valor) VALUES (?,?,?)', (st.session_state['user'], f, gluc))
            if 70 <= gluc <= 125: st.success("🟢 NORMAL")
            elif 126 <= gluc <= 160: st.warning("🟡 PRECAUCIÓN")
            else: st.error("🔴 ALERTA CRÍTICA")

    elif menu == "📸 Visor PDF":
        up = st.file_uploader("Subir Análisis", type=['pdf'])
        if up:
            b64 = base64.b64encode(up.read()).decode('utf-8')
            st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf">', unsafe_allow_html=True)

    elif menu == "Cerrar Sesión":
        st.session_state['login'] = False
        st.rerun()
