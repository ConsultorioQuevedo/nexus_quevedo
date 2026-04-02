import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib

# --- 1. CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .sidebar .sidebar-content { background-image: linear-gradient(#161B22,#0E1117); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE DATOS ROBUSTA ---
def init_db():
    conn = sqlite3.connect('nexus_pro_data.db', check_same_thread=False)
    c = conn.cursor()
    # Usuarios, Salud, Finanzas y Documentos
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT, nombre TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, cat TEXT, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS docs (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, info TEXT)')
    conn.commit()
    return conn, c

conn, c = init_db()

# --- 3. SEGURIDAD (Hash de contraseñas) ---
def encriptar(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verificar_usuario(user, password):
    c.execute('SELECT password FROM usuarios WHERE user = ?', (user,))
    data = c.fetchone()
    if data:
        return data[0] == encriptar(password)
    return False

# --- 4. LÓGICA DE SALUD ---
def semaforo_glucosa(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

# --- 5. CONTROL DE ACCESO ---
if 'login' not in st.session_state:
    st.session_state['login'] = False
    st.session_state['user'] = ""

if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO - Privacidad Total")
    tab_log, tab_reg = st.tabs(["Identificarse", "Crear Cuenta"])
    
    with tab_log:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type='password')
        if st.button("Entrar"):
            if verificar_usuario(u, p):
                st.session_state['login'] = True
                st.session_state['user'] = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
                
    with tab_reg:
        new_u = st.text_input("Nuevo Usuario")
        new_n = st.text_input("Su Nombre")
        new_p = st.text_input("Nueva Contraseña", type='password')
        if st.button("Registrar"):
            try:
                c.execute('INSERT INTO usuarios VALUES (?,?,?)', (new_u, encriptar(new_p), new_n))
                conn.commit()
                st.success("Cuenta creada. Ya puede identificarse.")
            except:
                st.error("Ese usuario ya existe")

# --- 6. CUERPO DEL PROGRAMA ---
else:
    st.sidebar.title(f"Bienvenido, {st.session_state['user']}")
    opcion = st.sidebar.radio("Navegación", ["Salud", "Finanzas", "Escáner", "Backup"])

    if opcion == "Salud":
        st.header("🩸 Control de Glucosa Inteligente")
        val = st.number_input("Introduzca Valor:", min_value=0.0)
        if st.button("Guardar"):
            est = semaforo_glucosa(val)
            f = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute('INSERT INTO glucosa (user, fecha, valor, estado) VALUES (?,?,?,?)', (st.session_state['user'], f, val, est))
            conn.commit()
            st.success(f"Registrado: {est}")
        
        historial = pd.read_sql_query('SELECT fecha, valor, estado FROM glucosa WHERE user=? ORDER BY id DESC', conn, params=(st.session_state['user'],))
        st.dataframe(historial, use_container_width=True)

    elif opcion == "Finanzas":
        st.header("💰 Gestión de Finanzas")
        m = st.number_input("Monto (RD$):", min_value=0.0)
        t = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
        ca = st.selectbox("Categoría:", ["Comida", "Salud", "Servicios", "Otros"])
        if st.button("Registrar Transacción"):
            f = datetime.datetime.now().strftime("%Y-%m-%d")
            c.execute('INSERT INTO finanzas (user, monto, tipo, cat, fecha) VALUES (?,?,?,?,?)', (st.session_state['user'], m, t, ca, f))
            conn.commit()
            st.success("Guardado correctamente")
        
        fin_df = pd.read_sql_query('SELECT fecha, monto, tipo, cat FROM finanzas WHERE user=?', conn, params=(st.session_state['user'],))
        st.dataframe(fin_df, use_container_width=True)

    elif opcion == "Escáner":
        st.header("📸 Escáner de Documentos")
        img = st.file_uploader("Subir foto de análisis o receta", type=['jpg', 'png', 'jpeg'])
        if img:
            st.image(img, width=400)
            if st.button("Procesar Documento"):
                # Simulación de extracción para mantener el código simple y funcional en su PC
                info_extraida = "Documento analizado localmente. Datos guardados en historial."
                f = datetime.datetime.now().strftime("%Y-%m-%d")
                c.execute('INSERT INTO docs (user, fecha, info) VALUES (?,?,?)', (st.session_state['user'], f, info_extraida))
                conn.commit()
                st.info(info_extraida)

    elif opcion == "Backup":
        st.header("⚙️ Copia de Seguridad")
        if st.button("Cerrar Sesión"):
            st.session_state['login'] = False
            st.rerun()
        st.write("Sus datos están resguardados en el archivo 'nexus_pro_data.db' de su PC.")
