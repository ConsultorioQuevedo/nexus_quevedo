import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np

# -------------------------
# Seguridad: Login
# -------------------------
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
        cursor.execute('INSERT INTO users (username, password) VALUES (?,?)', (username, hash_password(password)))
        conn.commit()
        return True

# -------------------------
# Base de datos
# -------------------------
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

# -------------------------
# Funciones auxiliares
# -------------------------
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

# -------------------------
# IA Predictiva
# -------------------------
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

# -------------------------
# Interfaz principal
# -------------------------
def main():
    # Corrección: set_page_config (con guiones bajos)
    st.set_page_config(page_title="Nexus Quevedo", layout="wide")
    st.markdown("<style> .stMetric {background-color:#f9f9f9; border-radius:10px; padding:10px;} </style>", unsafe_allow_html=True)

    # Login
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if not username or not password:
        st.warning("Ingrese sus credenciales para continuar.")
        return

    if not check_login(username, password):
        st.error("Contraseña incorrecta.")
        return

    st.title("📊 Nexus Quevedo - Asistente Personal")

    menu = st.sidebar.radio("Menú", ["Salud", "Finanzas", "Citas", "Backup"])

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
        
        # Corrección: read_sql_query (con guiones bajos)
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        st.write(g_data)
        
        if not g_data.empty:
            pred = predecir_glucosa(g_data)
            if pred:
                st.info(f"🤖 Predicción: su glucosa mañana podría ser {pred:.1f}")
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o')
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
        
        # Corrección: read_sql_query
        f_data = pd.read_sql_query('SELECT * FROM finanzas', conn)
        st.write(f_data)
        
        if not f_data.empty:
            pred = predecir_gastos(f_data)
            if pred:
                st.info(f"🤖 Predicción: próximo gasto estimado RD$ {pred:.2f}")

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

    elif menu == "Backup":
        st.subheader("📤 Exportación")
        st.info("Función de respaldo lista para implementación de descarga de base de datos.")

if __name__ == "__main__":
    main()
