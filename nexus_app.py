import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import logging

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
        # Si el usuario no existe, lo crea (para su primer acceso)
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

    # Login persistente
    if "loggedin" not in st.session_state:
        st.session_state.loggedin = False

    if not st.session_state.loggedin:
        st.sidebar.title("🔐 Login")
        username = st.sidebar.text_input("Usuario")
        password = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Ingresar"):
            if check_login(username, password):
                st.session_state.loggedin = True
                st.session_state.userid = username
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
        return
    else:
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.loggedin = False
            st.rerun()

    st.title(f"📊 Nexus Quevedo - Asistente de {st.session_state.userid}")

    menu = st.sidebar.radio("Menú", ["Salud", "Finanzas", "Citas"])

    # --- SALUD ---
    if menu == "Salud":
        st.subheader("🩸 Glucosa")
        val = st.number_input("Valor Glucosa:", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            try:
                cursor.execute(
                    'INSERT INTO glucosa (user_id, fecha, valor, estado) VALUES (?,?,?,?)',
                    (st.session_state.userid, fec, val, estado)
                )
                conn.commit()
                st.success("Registro guardado")
            except Exception as e:
                logging.error(e)
                st.error("Error al guardar")

        df_g = pd.read_sql_query('SELECT * FROM glucosa WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(df_g)

        borrar_id = st.number_input("ID a borrar en Glucosa:", min_value=0, step=1, key="del_glu")
        if st.button("Borrar Registro Glucosa"):
            cursor.execute('DELETE FROM glucosa WHERE id=? AND user_id=?', (borrar_id, st.session_state.userid))
            conn.commit()
            st.success("Registro eliminado")
            st.rerun()

        if not df_g.empty:
            pred = predecir_valores(df_g, "valor")
            if pred:
                st.info(f"🤖 Predicción: su glucosa mañana podría ser {pred}")
            fig, ax = plt.subplots()
            ax.plot(df_g['fecha'], df_g['valor'], marker='o')
            plt.xticks(rotation=45)
            st.pyplot(fig)

        st.divider()
        st.subheader("💊 Medicamentos")
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        h_med = st.time_input("Hora de tomarlo:")
        if st.button("Registrar Medicamento"):
            cursor.execute(
                'INSERT INTO meds (user_id, nombre, dosis, hora) VALUES (?,?,?,?)',
                (st.session_state.userid, nmed, dmed, str(h_med))
            )
            conn.commit()
            st.success("Medicamento registrado")

        df_m = pd.read_sql_query('SELECT * FROM meds WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(df_m)

    # --- FINANZAS ---
    elif menu == "Finanzas":
        st.subheader("💰 Finanzas")
        monto_input = st.text_input("Monto (RD$):")
        monto_val = validar_monto(monto_input)
        tipo = st.selectbox("Tipo:", ["Ingreso","Gasto"])
        categoria = st.selectbox("Categoría:", ["Comida","Salud","Servicios","Otros"])
        
        if st.button("Registrar Movimiento") and monto_val is not None:
            cursor.execute(
                'INSERT INTO finanzas (user_id, monto, tipo, categoria) VALUES (?,?,?,?)',
                (st.session_state.userid, monto_val, tipo, categoria)
            )
            conn.commit()
            st.success("Movimiento registrado")

        df_f = pd.read_sql_query('SELECT * FROM finanzas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(df_f)

    # --- CITAS ---
    elif menu == "Citas":
        st.subheader("📅 Citas")
        fc = st.date_input("Fecha")
        dc = st.text_input("Doctor")
        if st.button("Agendar Cita"):
            cursor.execute(
                'INSERT INTO citas (user_id, fecha, doctor) VALUES (?,?,?)',
                (st.session_state.userid, str(fc), dc)
            )
            conn.commit()
            st.success("Cita registrada")

        df_c = pd.read_sql_query('SELECT * FROM citas WHERE user_id=?', conn, params=(st.session_state.userid,))
        st.write(df_c)

        hoy = datetime.date.today()
        for index, row in df_c.iterrows():
            try:
                fecha_cita = datetime.datetime.strptime(row['fecha'], "%Y-%m-%d").date()
                if (fecha_cita - hoy).days == 2:
                    st.warning(f"📅 Recordatorio: Cita en 2 días con {row['doctor']}.")
            except:
                pass

if __name__ == "__main__":
    main()
