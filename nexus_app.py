import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import base64

# --- 1. CONEXIÓN BLINDADA ---
# Esta función asegura que la tabla exista SIEMPRE antes de entrar al Login
def inicializar_db_segura():
    conn = sqlite3.connect('nexus_pro_data.db', check_same_thread=False)
    c = conn.cursor()
    # CRÍTICO: Crear tablas primero para evitar el error de la línea 60
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (user TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, valor REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, user TEXT, nombre TEXT, dosis TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, user TEXT, fecha TEXT, doctor TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, user TEXT, monto REAL, tipo TEXT, fecha TEXT)')
    conn.commit()
    return conn, c

# Ejecutar la conexión al cargar el programa
conn, c = inicializar_db_segura()

def encriptar(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

# --- 2. LÓGICA DE ACCESO ---
if 'login' not in st.session_state:
    st.session_state['login'] = False
    st.session_state['user'] = ""

if not st.session_state['login']:
    st.title("🛡️ NEXUS PRO - Acceso")
    
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.subheader("Entrar")
        u = st.text_input("Usuario", key="user_login")
        p = st.text_input("Contraseña", type='password', key="pass_login")
        
        if st.button("Iniciar Sesión"):
            # Aquí ya no fallará porque la tabla se creó arriba
            c.execute('SELECT password FROM usuarios WHERE user = ?', (u,))
            data = c.fetchone()
            if data and data[0] == encriptar(p):
                st.session_state['login'] = True
                st.session_state['user'] = u
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")

    with col_der:
        st.subheader("Crear Cuenta Nueva")
        new_u = st.text_input("Nuevo Usuario", key="new_u")
        new_p = st.text_input("Nueva Clave", type='password', key="new_p")
        if st.button("Registrar"):
            try:
                c.execute('INSERT INTO usuarios VALUES (?,?)', (new_u, encriptar(new_p)))
                conn.commit()
                st.success("Cuenta creada. Ya puede iniciar sesión.")
            except:
                st.warning("Ese usuario ya existe.")
