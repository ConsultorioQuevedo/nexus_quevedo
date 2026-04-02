import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
from fpdf import FPDF
from sklearn.linear_model import LinearRegression
import numpy as np

# ---------------------------------------------------------
# SEGURIDAD: LOGIN (Mantiene su lógica de cifrado intacta)
# ---------------------------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)')
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

# ---------------------------------------------------------
# BASE DE DATOS (Persistencia Total de Registros)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, monto REAL, tipo TEXT, categoria TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ---------------------------------------------------------
# FUNCIONES AUXILIARES Y SEMÁFORO
# ---------------------------------------------------------
def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

def validar_monto(monto):
    try:
        monto = float(monto)
        if monto < 0:
            st.error("El monto no puede ser negativo.")
            return None
        return monto
    except ValueError:
        st.error("Por favor ingrese un número válido.")
        return None

# ---------------------------------------------------------
# IA PREDICTIVA (Módulo de Inteligencia Artificial)
# ---------------------------------------------------------
def predecir_glucosa(data):
    if len(data) > 3:
        X = np.arange(len(data)).reshape(-1,1)
        y = data['valor'].values
        model = LinearRegression().fit(X,y)
        pred = model.predict([[len(data)+1]])
        return pred[0]
    return None

def predecir_gastos(data):
    if len(data) > 3:
        X = np.arange(len(data)).reshape(-1,1)
        y = data['monto'].values
        model = LinearRegression().fit(X,y)
        pred = model.predict([[len(data)+1]])
        return pred[0]
    return None

# ---------------------------------------------------------
# INTERFAZ PRINCIPAL - NEXUS QUEVEDO PRO
# ---------------------------------------------------------
def main():
    # Configuración de página con guion bajo (st.set_page_config)
    st.set_page_config(page_title="Nexus Quevedo", layout="wide")
    st.markdown("<style> .stMetric {background-color:#f9f9f9; border-radius:10px; padding:10px;} </style>", unsafe_allow_html=True)

    # Login Lateral
    st.sidebar.title("🔐 Acceso Nexus")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if not username or not password:
        st.info("🛡️ Identifíquese para acceder a Multiservicios Anael.")
        return

    if not check_login(username, password):
        st.error("Credenciales incorrectas.")
        return

    st.title(f"📊 Nexus Quevedo - Panel de {username}")
    menu = st.sidebar.radio("Menú", ["Salud", "Finanzas", "Citas", "Backup"])

    # --- MÓDULO SALUD ---
    if menu == "Salud":
        st.subheader("🩸 Glucosa")
        val = st.number_input("Valor Glucosa:", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            try:
                cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, estado))
                conn.commit()
                st.success("Registro guardado")
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        st.write(g_data)
        
        if not g_data.empty:
            pred = predecir_glucosa(g_data)
            if pred:
                st.info(f"🤖 Predicción: su glucosa mañana podría ser {pred:.1f}")
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o', color='red')
            plt.xticks(rotation=45)
            st.pyplot(fig)

        st.subheader("💊 Medicamentos")
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        h_med = st.time_input("Hora de tomarlo:")
        if st.button("Registrar Medicamento"):
            try:
                cursor.execute('INSERT INTO meds (nombre, dosis, hora) VALUES (?,?,?)', (nmed, dmed, str(h_med)))
                conn.commit()
                st.success("Medicamento registrado")
            except Exception as e:
                st.error(f"Error: {e}")
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.write(m_data)

    # --- MÓDULO FINANZAS ---
    elif menu == "Finanzas":
        st.subheader("💰 Finanzas")
        monto_input = st.text_input("Monto (RD$):")
        monto_val = validar_monto(monto_input)
        tipo = st.selectbox("Tipo:", ["Ingreso","Gasto"])
        categoria = st.selectbox("Categoría:", ["Comida","Salud","Servicios","Otros"])
        
        if st.button("Registrar Movimiento") and monto_val is not None:
            try:
                cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (monto_val, tipo, categoria))
                conn.commit()
                st.success("Movimiento registrado")
            except Exception as e:
                st.error(f"Error: {e}")
        
        f_data = pd.read_sql_query('SELECT * FROM finanzas', conn)
        st.write(f_data)
        
        if not f_data.empty:
            pred_f = predecir_gastos(f_data)
            if pred_f:
                st.info(f"🤖 Predicción: próximo gasto estimado RD$ {pred_f:.2f}")

    # --- MÓDULO CITAS ---
    elif menu == "Citas":
        st.subheader("📅 Citas")
        f_c = st.date_input("Fecha")
        d_c = st.text_input("Doctor")
        if st.button("Agendar Cita"):
            try:
                cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(f_c), d_c))
                conn.commit()
                st.success("Cita registrada")
            except Exception as e:
                st.error(f"Error: {e}")
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)

    # --- MÓDULO BACKUP ---
    elif menu == "Backup":
        st.subheader("📤 Exportación")
        st.write("Datos protegidos en nexuspro.db.")

if __name__ == "__main__":
    main()
