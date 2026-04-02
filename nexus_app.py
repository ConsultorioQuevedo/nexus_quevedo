import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import matplotlib.pyplot as plt
import os

def init_db():
    # Corregido: check_same_thread
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, monto REAL, tipo TEXT, categoria TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS escaneo (id INTEGER PRIMARY KEY, fecha TEXT, archivo TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

def generarpdf(img, nombre_archivo="documento_nexus.pdf"):
    img_path = "captura.jpg"
    with open(img_path, "wb") as f:
        f.write(img.getbuffer())
    pdf = FPDF()
    pdf.add_page()
    pdf.image(img_path, x=10, y=10, w=180)
    pdf.output(nombre_archivo, "F")
    if os.path.exists(img_path):
        os.remove(img_path)
    return nombre_archivo

def exportar_backup():
    data_glucosa = pd.read_sql_query('SELECT * FROM glucosa', conn)
    data_meds = pd.read_sql_query('SELECT * FROM meds', conn)
    data_citas = pd.read_sql_query('SELECT * FROM citas', conn)
    data_fin = pd.read_sql_query('SELECT * FROM finanzas', conn)
    
    # Usamos CSV para máxima compatibilidad y simplicidad en la limpieza
    data_glucosa.to_csv("backup_glucosa.csv", index=False)
    with open("backup_glucosa.csv", "rb") as f:
        st.download_button("📥 Descargar Backup Glucosa (CSV)", f, file_name="backup_glucosa.csv")

def mostrar_finanzas():
    st.subheader("📊 Gestión Financiera Pro")
    presupuesto = st.number_input("Presupuesto mensual (RD$):", min_value=0.0, format="%.2f", step=100.0)
    if st.button("Guardar Presupuesto"):
        cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (presupuesto, "Presupuesto","General"))
        conn.commit()
        st.success(f"Presupuesto registrado: RD$ {presupuesto:,.2f}")
    
    monto = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f", step=1.0)
    tipo = st.selectbox("Tipo de movimiento:", ["Ingreso", "Gasto"])
    categoria = st.selectbox("Categoría:", ["Comida","Salud","Servicios","Otros"])
    if st.button("Registrar Movimiento"):
        cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (monto, tipo, categoria))
        conn.commit()
        st.success(f"{tipo} registrado: RD$ {monto:,.2f}")
    
    data = pd.read_sql_query('SELECT * FROM finanzas', conn)
    st.write(data)
    
    borrar_id = st.number_input("ID a borrar en Finanzas:", min_value=0, step=1, key="fin_del")
    if st.button("Borrar Registro"):
        cursor.execute('DELETE FROM finanzas WHERE id=?', (borrar_id,))
        conn.commit()
        st.rerun()

    ingresos = data[data['tipo']=="Ingreso"]['monto'].sum()
    gastos = data[data['tipo']=="Gasto"]['monto'].sum()
    presupuesto_total = data[data['tipo']=="Presupuesto"]['monto'].sum()
    balance = ingresos - gastos
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos", f"RD$ {ingresos:,.2f}")
    c2.metric("Gastos", f"RD$ {gastos:,.2f}")
    c3.metric("Balance", f"RD$ {balance:,.2f}")
    c4.metric("Presupuesto", f"RD$ {presupuesto_total:,.2f}")
    
    if not data.empty:
        gastos_cat = data[data['tipo']=="Gasto"].groupby("categoria")['monto'].sum()
        if not gastos_cat.empty:
            fig, ax = plt.subplots()
            ax.pie(gastos_cat, labels=gastos_cat.index, autopct='%1.1f%%', startangle=90)
            ax.set_title("Distribución de Gastos")
            st.pyplot(fig)

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
        
        if not g_data.empty:
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o', color='red')
            ax.set_title("Tendencia de Glucosa")
            plt.xticks(rotation=45)
            st.pyplot(fig)

    with t_meds:
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        if st.button("Registrar"):
            cursor.execute('INSERT INTO meds (nombre, dosis) VALUES (?,?)', (nmed, dmed))
            conn.commit()
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.write(m_data)
        if not m_data.empty:
            st.info(f"💊 Recordatorio: {m_data.iloc[-1]['nombre']} ({m_data.iloc[-1]['dosis']})")

    with t_citas:
        fc = st.date_input("Fecha de Cita")
        dc = st.text_input("Doctor/Especialidad")
        if st.button("Agendar"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(fc), dc))
            conn.commit()
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)
        
        hoy = datetime.date.today()
        for _, row in c_data.iterrows():
            try:
                f_cita = datetime.datetime.strptime(row['fecha'], "%Y-%m-%d").date()
                dias = (f_cita - hoy).days
                if 0 <= dias <= 2:
                    st.warning(f"📅 Cita próxima en {dias} días con: {row['doctor']}")
            except: pass

    with t_scan:
        if st.checkbox("Activar Cámara"):
            img = st.camera_input("Capturar")
            if img:
                p_file = generarpdf(img)
                st.success("PDF Generado")
                with open(p_file, "rb") as f:
                    st.download_button("📥 Descargar", f, file_name=p_file)

def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    st.title("🛡️ NEXUS PRO - Panel de Control Sr. Quevedo")
    
    menu = st.sidebar.selectbox("Menú", ["Dashboard", "Backup"])
    
    if menu == "Dashboard":
        t_fin, t_salud = st.tabs(["💰 Finanzas", "🩺 Salud"])
        with t_fin: mostrar_finanzas()
        with t_salud: mostrar_salud()
    else:
        st.subheader("Soberanía de Datos")
        exportar_backup()

if __name__ == "__main__":
    main()
