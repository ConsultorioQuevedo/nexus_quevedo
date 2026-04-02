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

# --- Configuración de Logs ---
logging.basicConfig(filename="error.log", level=logging.ERROR)

# --- Seguridad: Login persistente ---
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
        cursor.execute('INSERT INTO users (username, password) VALUES (?,?)', (username, hash_password(password)))
        conn.commit()
        return True

# --- Base de datos ---
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

# --- Funciones auxiliares ---
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
        if monto: st.error("Ingrese un número válido.")
        return None

# --- IA Predictiva ---
def predecir_valores(data, columna):
    if len(data) >= 10:
        X = np.arange(len(data)).reshape(-1,1)
        y = data[columna].values
        model = LinearRegression().fit(X,y)
        pred = model.predict([[len(data)+1]])
        return f"{pred[0]:.1f} ± 5"
    return None

# --- Interfaz principal ---
def main():
    st.set_page_config(page_title="Nexus Quevedo", layout="wide")

    # Gestión de Sesión
    if "loggedin" not in st.session_state:
        st.session_state.loggedin = False

    if not st.session_state.loggedin:
        st.sidebar.title("🔐 Login")
        u = st.sidebar.text_input("Usuario")
        p = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Ingresar"):
            if check_login(u, p):
                st.session_state.loggedin = True
                st.session_state.userid = u
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

    # MODULO SALUD
    if menu == "Salud":
        st.subheader("🩸 Glucosa")
        val = st.number_input("Valor Glucosa:", min_value=0)
        if st.button("Guardar Glucosa"):
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            cursor.execute('INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)',
                           (st.session_state.userid, fec, val, obtener_semaforo(val)))
            conn.commit()
            st.success("Guardado")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(g_data)
        
        bid = st.number_input("ID a borrar:", min_value=0, key="bg")
        if st.button("Borrar Registro"):
            cursor.execute('DELETE FROM glucosa WHERE id=? AND user_id=?', (bid, st.session_state.userid))
            conn.commit()
            st.rerun()

        if not g_data.empty:
            p = predecir_valores(g_data, "valor")
            if p: st.info(f"🤖 IA: Predicción próxima toma: {p}")

    # MODULO FINANZAS
    elif menu == "Finanzas":
        st.subheader("💰 Finanzas")
        m_in = st.text_input("Monto (RD$):")
        m_val = validar_monto(m_in)
        tipo = st.selectbox("Tipo:", ["Ingreso","Gasto"])
        cat = st.selectbox("Categoría:", ["Comida","Salud","Servicios","Otros"])
        if st.button("Registrar") and m_val:
            cursor.execute('INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)',
                           (st.session_state.userid, m_val, tipo, cat))
            conn.commit()
            st.success("Registrado")
        
        f_data = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.dataframe(f_data)

    # MODULO CITAS
    elif menu == "Citas":
        st.subheader("📅 Citas")
        f_c = st.date_input("Fecha")
        d_c = st.text_input("Doctor")
        if st.button("Agendar"):
            cursor.execute('INSERT INTO citas (user_id, fecha, doctor) VALUES (?,?,?)',
                           (st.session_state.userid, str(f_c), d_c))
            conn.commit()
            st.success("Cita agendada")
        
        c_data = pd.read_sql_query('SELECT * FROM citas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(c_data)

if __name__ == "__main__":
    main()
