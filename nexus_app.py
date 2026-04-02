import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import matplotlib.pyplot as plt

# --- Inicializar base de datos ---
def init_db():
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, hora TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, monto REAL, tipo TEXT, categoria TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS escaneo (id INTEGER PRIMARY KEY, fecha TEXT, archivo TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Funciones de Utilidad ---
def obtener_semaforo(v):
    if 90 <= v <= 125: 
        return "🟢 NORMAL"
    if 126 <= v <= 160: 
        return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

def generarpdf(img, nombre_archivo="documento_nexus.pdf"):
    img_path = "captura.jpg"
    with open(img_path, "wb") as f:
        f.write(img.getbuffer())
    pdf = FPDF()
    pdf.add_page()
    pdf.image(img_path, x=10, y=10, w=180)
    pdf.output(nombre_archivo, "F")
    return nombre_archivo

def exportar_backup():
    data_glucosa = pd.read_sql_query('SELECT * FROM glucosa', conn)
    data_meds = pd.read_sql_query('SELECT * FROM meds', conn)
    data_citas = pd.read_sql_query('SELECT * FROM citas', conn)
    data_fin = pd.read_sql_query('SELECT * FROM finanzas', conn)
    
    file_name = "backup_nexus.xlsx"
    with pd.ExcelWriter(file_name) as writer:
        data_glucosa.to_excel(writer, sheet_name="Glucosa", index=False)
        data_meds.to_excel(writer, sheet_name="Medicamentos", index=False)
        data_citas.to_excel(writer, sheet_name="Citas", index=False)
        data_fin.to_excel(writer, sheet_name="Finanzas", index=False)
    
    with open(file_name, "rb") as f:
        st.download_button("📥 Descargar Backup Excel", f, file_name=file_name)

# --- Módulo: Finanzas ---
def mostrar_finanzas():
    st.subheader("Gestión Financiera")
    presupuesto = st.number_input("Presupuesto mensual (RD$):", min_value=0.0, format="%.2f", step=100.0)
    
    if st.button("Guardar Presupuesto"):
        cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (presupuesto, "Presupuesto", "General"))
        conn.commit()
        st.success(f"Presupuesto registrado: RD$ {presupuesto:,.2f}")
    
    monto = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f", step=1.0)
    tipo = st.selectbox("Tipo de movimiento:", ["Ingreso", "Gasto"])
    categoria = st.selectbox("Categoría:", ["Comida", "Salud", "Servicios", "Otros"])
    
    if st.button("Registrar Movimiento"):
        cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (monto, tipo, categoria))
        conn.commit()
        st.success(f"{tipo} registrado: RD$ {monto:,.2f}")
    
    data = pd.read_sql_query('SELECT * FROM finanzas', conn)
    st.dataframe(data)
    
    borrar_id = st.number_input("ID a borrar en Finanzas:", min_value=0, step=1, key="del_fin")
    if st.button("Borrar Registro de Finanzas"):
        cursor.execute('DELETE FROM finanzas WHERE id=?', (borrar_id,))
        conn.commit()
        st.success("Registro eliminado")
        st.rerun()

    if not data.empty:
        ingresos = data[data['tipo'] == "Ingreso"]['monto'].sum()
        gastos = data[data['tipo'] == "Gasto"]['monto'].sum()
        presupuesto_total = data[data['tipo'] == "Presupuesto"]['monto'].sum()
        balance = ingresos - gastos
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ingresos", f"RD$ {ingresos:,.2f}")
        col2.metric("Gastos", f"RD$ {gastos:,.2f}")
        col3.metric("Balance", f"RD$ {balance:,.2f}")
        col4.metric("Presupuesto", f"RD$ {presupuesto_total:,.2f}")
        
        if balance < presupuesto_total and presupuesto_total > 0:
            st.warning("⚠️ El balance está por debajo del presupuesto. IA recomienda reducir gastos.")
        else:
            st.info("✅ Balance dentro del presupuesto.")
            
        gastos_por_cat = data[data['tipo'] == "Gasto"].groupby("categoria")['monto'].sum()
        if not gastos_por_cat.empty:
            fig, ax = plt.subplots()
            ax.pie(gastos_por_cat, labels=gastos_por_cat.index, autopct='%1.1f%%')
            st.pyplot(fig)

# --- Módulo: Salud ---
def mostrar_salud():
    t_gluc, t_meds, t_citas, t_scan = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas", "📸 Escáner"])
    
    with t_gluc:
        val = st.number_input("Valor Glucosa:", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, estado))
            conn.commit()
            st.success("Registro guardado")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        st.write(g_data)
        
        borrar_id_g = st.number_input("ID a borrar en Glucosa:", min_value=0, step=1, key="del_glu")
        if st.button("Borrar Registro Glucosa"):
            cursor.execute('DELETE FROM glucosa WHERE id=?', (borrar_id_g,))
            conn.commit()
            st.success("Registro eliminado")
            st.rerun()

        if not g_data.empty:
            prom = g_data['valor'].mean()
            if prom > 140:
                st.warning(f"🤖 IA Salud: Promedio de glucosa {prom:.1f} está elevado. Considere ajustar dieta.")
            else:
                st.info(f"🤖 IA Salud: Promedio de glucosa {prom:.1f} dentro de rango saludable.")
            
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o')
            ax.set_title("Tendencia de Glucosa")
            st.pyplot(fig)

    with t_meds:
        n_med = st.text_input("Medicamento:")
        d_med = st.text_input("Dosis:")
        h_med = st.time_input("Hora de tomarlo:")
        if st.button("Registrar Medicamento"):
            cursor.execute('INSERT INTO meds (nombre, dosis, hora) VALUES (?,?,?)', (n_med, d_med, str(h_med)))
            conn.commit()
            st.success("Medicamento registrado")
            
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.write(m_data)
        
        borrar_id_m = st.number_input("ID a borrar en Medicamentos:", min_value=0, step=1, key="del_med")
        if st.button("Borrar Registro Medicamento"):
            cursor.execute('DELETE FROM meds WHERE id=?', (borrar_id_m,))
            conn.commit()
            st.rerun()

    with t_citas:
        f_c = st.date_input("Fecha de Cita")
        d_c = st.text_input("Nombre del Doctor")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(f_c), d_c))
            conn.commit()
            st.success("Cita agendada")
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)

# --- App Principal ---
st.set_page_config(page_title="NEXUS PRO", layout="wide")
st.title("NEXUS PRO - Gestión Inteligente")

menu = st.sidebar.selectbox("Módulo:", ["Finanzas", "Salud"])
if menu == "Finanzas":
    mostrar_finanzas()
else:
    mostrar_salud()

if st.sidebar.button("📦 Generar Backup Completo"):
    exportar_backup()
