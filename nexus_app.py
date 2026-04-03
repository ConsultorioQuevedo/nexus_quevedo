import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE BASE DE DATOS ---
conn = sqlite3.connect('gestion_total.db', check_same_thread=False)
c = conn.cursor()

def crear_tablas():
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, tipo TEXT, monto REAL, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS salud (id INTEGER PRIMARY KEY, tipo TEXT, valor REAL, nota TEXT, fecha TEXT)')
    conn.commit()

crear_tablas()

# --- INTERFAZ PRINCIPAL ---
st.title("Sistema de Gestión: Finanzas & Salud")
menu = ["Finanzas", "Salud", "Escaneo y Documentos"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- SECCIÓN FINANZAS ---
if choice == "Finanzas":
    st.header("📊 Gestión de Finanzas")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo", ["Ingreso", "Gasto", "Presupuesto"])
        monto = st.number_input("Monto", min_value=0.0)
        if st.button("Agregar Registro"):
            c.execute('INSERT INTO finanzas (tipo, monto, fecha) VALUES (?,?,?)', 
                      (tipo, monto, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Dato guardado")

    # Mostrar Datos y Cálculos
    df_fin = pd.read_sql_query('SELECT * FROM finanzas', conn)
    
    ingresos = df_fin[df_fin['tipo'] == 'Ingreso']['monto'].sum()
    gastos = df_fin[df_fin['tipo'] == 'Gasto']['monto'].sum()
    balance = ingresos - gastos
    
    st.metric("Balance Total", f"${balance:,.2f}")
    st.table(df_fin)

    if st.button("Eliminar Último Registro"):
        c.execute('DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)')
        conn.commit()
        st.rerun()

# --- SECCIÓN SALUD ---
elif choice == "Salud":
    st.header("🩺 Control de Salud")
    
    sub_salud = st.tabs(["Glucosa", "Medicamentos", "Citas"])
    
    with sub_salud[0]:
        nivel = st.number_input("Nivel de Glucosa (mg/dL)", min_value=0)
        if st.button("Registrar Glucosa"):
            c.execute('INSERT INTO salud (tipo, valor, fecha) VALUES (?,?,?)', 
                      ("Glucosa", nivel, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
        
        # Semáforo
        if nivel > 0:
            if nivel < 140:
                st.success(f"🟢 Normal: {nivel}")
            elif 140 <= nivel <= 160:
                st.warning(f"🟡 Precaución: {nivel}")
            else:
                st.error(f"🔴 Alerta: {nivel}")

        # Gráfico
        df_glucosa = pd.read_sql_query("SELECT valor, fecha FROM salud WHERE tipo='Glucosa'", conn)
        if not df_glucosa.empty:
            st.line_chart(df_glucosa.set_index('fecha'))

# --- SECCIÓN ESCANEO (CONCEPTUAL) ---
elif choice == "Escaneo y Documentos":
    st.header("📄 Documentación y Escaneo")
    archivo = st.file_uploader("Cargar documento para escanear (OCR)", type=['jpg', 'png', 'pdf'])
    
    if archivo:
        st.image(archivo, caption="Documento listo para procesar")
        st.info("Aquí se integraría la librería Tesseract para extraer texto.")
    
    st.subheader("Acciones Externas")
    st.link_button("Enviar por WhatsApp", "https://wa.me/tu_numero")
    st.link_button("Abrir Gmail", "https://mail.google.com")
