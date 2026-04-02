import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
from fpdf import FPDF
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
        # Registro automático del primer usuario para facilitar el acceso inicial
        if username and password:
            cursor.execute('INSERT INTO users (username, password) VALUES (?,?)', (username, hash_password(password)))
            conn.commit()
            return True
        return False

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
        monto_f = float(monto)
        if monto_f < 0:
            st.error("El monto no puede ser negativo.")
            return None
        return monto_f
    except ValueError:
        if monto: # Solo muestra error si el usuario intentó escribir algo
            st.error("Por favor ingrese un número válido.")
        return None

# -------------------------
# IA Predictiva
# -------------------------
def predecir_glucosa(data):
    if len(data) > 3:
        X = np.arange(len(data)).reshape(-1,1)
        y = data['valor'].values
        model = LinearRegression().fit(X, y)
        pred = model.predict([[len(data) + 1]])
        return pred[0]
    return None

def predecir_gastos(data):
    if len(data) > 3:
        X = np.arange(len(data)).reshape(-1,1)
        y = data['monto'].values
        model = LinearRegression().fit(X, y)
        pred = model.predict([[len(data) + 1]])
        return pred[0]
    return None

# -------------------------
# Interfaz principal
# -------------------------
def main():
    st.set_page_config(page_title="Nexus Quevedo", layout="wide")
    st.markdown("<style> .stMetric {background-color:#f9f9f9; border-radius:10px; padding:10px; border: 1px solid #ddd;} </style>", unsafe_allow_html=True)

    # Login en la barra lateral
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if not check_login(username, password):
        st.title("🚀 Bienvenidos a Nexus Quevedo")
        st.warning("Ingrese sus credenciales en el menú lateral para continuar.")
        return

    st.title("📊 Nexus Quevedo - Asistente Personal")
    menu = st.sidebar.radio("Menú", ["Salud", "Finanzas", "Citas"])

    if menu == "Salud":
        st.subheader("🩸 Monitoreo de Glucosa")
        val = st.number_input("Valor Glucosa (mg/dL):", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            try:
                cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, estado))
                conn.commit()
                st.success("Registro guardado exitosamente.")
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        if not g_data.empty:
            st.dataframe(g_data, use_container_width=True)
            pred = predecir_glucosa(g_data)
            if pred:
                st.info(f"🤖 **IA Predictiva:** Su glucosa estimada para la próxima toma es de **{pred:.1f} mg/dL**.")
            
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o', color='#ff4b4b')
            ax.set_title("Tendencia de Niveles de Glucosa")
            st.pyplot(fig)

        st.divider()
        st.subheader("💊 Medicamentos")
        n_med = st.text_input("Nombre del Medicamento:")
        d_med = st.text_input("Dosis (ej. 500mg):")
        h_med = st.time_input("Hora de la toma:")
        if st.button("Registrar Medicamento"):
            try:
                cursor.execute('INSERT INTO meds (nombre, dosis, hora) VALUES (?,?,?)', (n_med, d_med, str(h_med)))
                conn.commit()
                st.success("Medicamento registrado en su esquema.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        if not m_data.empty:
            st.table(m_data)

    elif menu == "Finanzas":
        st.subheader("💰 Control Financiero Inteligente")
        monto_input = st.text_input("Monto (RD$):")
        monto_val = validar_monto(monto_input)
        tipo = st.selectbox("Tipo de Movimiento:", ["Ingreso", "Gasto"])
        categoria = st.selectbox("Categoría:", ["Comida", "Salud", "Servicios", "Otros"])
        
        if st.button("Registrar Movimiento") and monto_val is not None:
            try:
                cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (monto_val, tipo, categoria))
                conn.commit()
                st.success("Movimiento financiero registrado.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        f_data = pd.read_sql_query('SELECT * FROM finanzas', conn)
        if not f_data.empty:
            st.dataframe(f_data, use_container_width=True)
            pred_f = predecir_gastos(f_data[f_data['tipo'] == 'Gasto'])
            if pred_f:
                st.info(f"🤖 **IA Predictiva:** Próximo gasto estimado según tendencia: **RD$ {pred_f:.2f}**.")
            
            gastos_cat = f_data[f_data['tipo'] == "Gasto"].groupby("categoria")['monto'].sum()
            if not gastos_cat.empty:
                fig, ax = plt.subplots()
                ax.pie(gastos_cat, labels=gastos_cat.index, autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
                st.pyplot(fig)

    elif menu == "Citas":
        st.subheader("📅 Agenda de Citas Médicas")
        f_c = st.date_input("Fecha de la Cita:")
        d_c = st.text_input("Doctor o Especialidad:")
        if st.button("Agendar Cita"):
            try:
                cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(f_c), d_c))
                conn.commit()
                st.success("Cita agendada correctamente.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        if not c_data.empty:
            st.write(c_data)
            hoy = datetime.date.today()
            for index, row in c_data.iterrows():
                try:
                    fecha_cita = datetime.datetime.strptime(row['fecha'], "%Y-%m-%d").date()
                    dias_restantes = (fecha_cita - hoy).days
                    if dias_restantes == 2:
                        st.warning(f"🔔 **Recordatorio:** Sr. Quevedo, tiene una cita en 2 días con: {row['doctor']}.")
                    elif dias_restantes == 0:
                        st.error(f"🚨 **¡Es hoy!** Cita programada para hoy con: {row['doctor']}.")
                except:
                    continue

if __name__ == "__main__":
    main()
