import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
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
        # Si el usuario no existe, se crea (Lógica original del Sr. Quevedo)
        cursor.execute('INSERT INTO users (username, password) VALUES (?,?)', (username, hash_password(password)))
        conn.commit()
        return True

# ---------------------------------------------------------
# BASE DE DATOS (Independencia total de registros)
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
# IA PREDICTIVA (Módulo de Inteligencia scikit-learn)
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
    st.set_page_config(page_title="Nexus Quevedo", layout="wide")
    st.markdown("<style> .stMetric {background-color:#f9f9f9; border-radius:10px; padding:10px;} </style>", unsafe_allow_html=True)

    # Login Lateral
    st.sidebar.title("🔐 Acceso Nexus")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if not username or not password:
        st.info("🛡️ Bienvenida a Nexus Pro. Por favor, identifíquese para acceder a sus datos.")
        return

    if not check_login(username, password):
        st.error("Acceso denegado.")
        return

    st.title(f"📊 Panel de Control - {username}")
    menu = st.sidebar.radio("Navegación Modular", ["Salud", "Finanzas", "Citas Médicas", "Respaldo"])

    # --- MÓDULO SALUD ---
    if menu == "Salud":
        st.subheader("🩸 Monitor de Glucosa")
        col1, col2 = st.columns(2)
        with col1:
            val = st.number_input("Valor Glucosa (mg/dL):", min_value=0, step=1)
            if st.button("Guardar Glucosa"):
                estado = obtener_semaforo(val)
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, estado))
                conn.commit()
                st.success("Dato registrado permanentemente.")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        st.dataframe(g_data, use_container_width=True)
        
        if not g_data.empty:
            with col2:
                pred = predecir_glucosa(g_data)
                if pred:
                    st.metric("🤖 Predicción Mañana", f"{pred:.1f} mg/dL")
                fig, ax = plt.subplots()
                ax.plot(g_data['fecha'], g_data['valor'], marker='o', color='#ff4b4b')
                plt.xticks(rotation=45)
                st.pyplot(fig)

        st.divider()
        st.subheader("💊 Gestión de Medicamentos")
        nmed = st.text_input("Nombre del Medicamento:")
        dmed = st.text_input("Dosis (ej: 500mg):")
        h_med = st.time_input("Hora de toma:")
        if st.button("Registrar Medicamento"):
            cursor.execute('INSERT INTO meds (nombre, dosis, hora) VALUES (?,?,?)', (nmed, dmed, str(h_med)))
            conn.commit()
            st.success("Medicamento añadido a la lista.")
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.table(m_data)

    # --- MÓDULO FINANZAS ---
    elif menu == "Finanzas":
        st.subheader("💰 Control Financiero")
        m_input = st.text_input("Monto en RD$:")
        m_val = validar_monto(m_input)
        t_mov = st.selectbox("Tipo de Movimiento:", ["Ingreso", "Gasto"])
        c_mov = st.selectbox("Categoría:", ["Comida", "Salud", "Servicios", "Hogar", "Otros"])
        
        if st.button("Procesar Transacción") and m_val is not None:
            cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (m_val, t_mov, c_mov))
            conn.commit()
            st.success("Movimiento guardado en la base de datos.")
        
        f_data = pd.read_sql_query('SELECT * FROM finanzas', conn)
        st.dataframe(f_data, use_container_width=True)
        
        if not f_data.empty:
            pred_f = predecir_gastos(f_data)
            if pred_f:
                st.info(f"🤖 Basado en su historial, el próximo gasto estimado es de RD$ {pred_f:.2f}")

    # --- MÓDULO CITAS ---
    elif menu == "Citas Médicas":
        st.subheader("📅 Agenda de Citas")
        f_c = st.date_input("Fecha programada:")
        d_c = st.text_input("Especialista / Centro:")
        if st.button("Confirmar Cita"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(f_c), d_c))
            conn.commit()
            st.success("Cita agendada correctamente.")
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)

    # --- MÓDULO RESPALDO ---
    elif menu == "Respaldo":
        st.subheader("📤 Exportación de Seguridad")
        st.write("Sus datos están persistidos en `nexuspro.db`. Use esta sección para generar backups futuros.")

if __name__ == "__main__":
    main()
