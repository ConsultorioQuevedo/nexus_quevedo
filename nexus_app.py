import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
from fpdf import FPDF
from sklearn.linear_model import LinearRegression
import numpy as np
import logging
import smtplib

# -------------------------
# Configuración de Logs
# -------------------------
logging.basicConfig(filename="error.log", level=logging.ERROR)

# -------------------------
# Seguridad: Login persistente
# -------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)')
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

# -------------------------
# Base de datos
# -------------------------
def init_db():
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user_id TEXT, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user_id TEXT, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user_id TEXT, monto REAL, tipo TEXT, categoria TEXT)')
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
        m_val = float(monto)
        if m_val < 0:
            st.error("El monto no puede ser negativo.")
            return None
        return m_val
    except ValueError:
        if monto: st.error("Por favor ingrese un número válido.")
        return None

# -------------------------
# IA Predictiva
# -------------------------
def predecir_valores(data, columna):
    if len(data) >= 10:
        X = np.arange(len(data)).reshape(-1,1)
        y = data[columna].values
        model = LinearRegression().fit(X,y)
        pred = model.predict([[len(data)+1]])
        intervalo = 5
        return f"{pred[0]:.1f} ± {intervalo}"
    return None

# -------------------------
# Interfaz principal
# -------------------------
def main():
    st.set_page_config(page_title="Nexus Quevedo", layout="wide")

    # Manejo de Sesión Persistente
    if "loggedin" not in st.session_state:
        st.session_state.loggedin = False

    if not st.session_state.loggedin:
        st.sidebar.title("🔐 Login")
        user_in = st.sidebar.text_input("Usuario")
        pass_in = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Ingresar"):
            if check_login(user_in, pass_in):
                st.session_state.loggedin = True
                st.session_state.userid = user_in
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return
    else:
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.loggedin = False
            st.rerun()

    st.title(f"📊 Nexus Quevedo - Hola, {st.session_state.userid}")
    menu = st.sidebar.radio("Menú", ["Salud", "Finanzas", "Citas"])

    # --- Módulo Salud ---
    if menu == "Salud":
        st.subheader("🩸 Glucosa")
        val = st.number_input("Valor Glucosa:", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)',
                           (st.session_state.userid, fec, val, estado))
            conn.commit()
            st.success("Registro guardado")

        g_data = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(g_data, use_container_width=True)
        
        borrar_id = st.number_input("ID a borrar (Glucosa):", min_value=0, step=1, key="del_glu")
        if st.button("Eliminar Registro Glucosa"):
            cursor.execute('DELETE FROM glucosa WHERE id=? AND user_id=?', (borrar_id, st.session_state.userid))
            conn.commit()
            st.rerun()

        if not g_data.empty:
            pred = predecir_valores(g_data, "valor")
            if pred: st.info(f"🤖 IA Predictiva: Su glucosa estimada es {pred}")
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o', color='red')
            st.pyplot(fig)

    # --- Módulo Finanzas ---
    elif menu == "Finanzas":
        st.subheader("💰 Finanzas")
        monto_in = st.text_input("Monto (RD$):")
        monto_val = validar_monto(monto_in)
        tipo = st.selectbox("Tipo:", ["Ingreso","Gasto"])
        categoria = st.selectbox("Categoría:", ["Comida","Salud","Servicios","Otros"])
        
        if st.button("Registrar Movimiento") and monto_val is not None:
            cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)',
                           (st.session_state.userid, monto_val, tipo, categoria))
            conn.commit()
            st.success("Movimiento registrado")

        f_data = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(f_data, use_container_width=True)
        
        borrar_f = st.number_input("ID a borrar (Finanzas):", min_value=0, step=1, key="del_fin")
        if st.button("Eliminar Registro Finanzas"):
            cursor.execute('DELETE FROM finanzas WHERE id=? AND user_id=?', (borrar_f, st.session_state.userid))
            conn.commit()
            st.rerun()

    # --- Módulo Citas ---
    elif menu == "Citas":
        st.subheader("📅 Citas Médicas")
        f_c = st.date_input("Fecha")
        d_c = st.text_input("Doctor")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (user_id, fecha, doctor) VALUES (?,?,?)',
                           (st.session_state.userid, str(f_c), d_c))
            conn.commit()
            st.success("Cita agendada")

        c_data = pd.read_sql_query('SELECT * FROM citas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(c_data)
        
        borrar_c = st.number_input("ID a borrar (Citas):", min_value=0, step=1, key="del_cit")
        if st.button("Eliminar Cita"):
            cursor.execute('DELETE FROM citas WHERE id=? AND user_id=?', (borrar_c, st.session_state.userid))
            conn.commit()
            st.rerun()

if __name__ == "__main__":
    main()
