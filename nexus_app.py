import streamlit as st
import pandas as pd
import sqlite3
import datetime
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

# --- Semáforo glucosa ---
def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

# --- Exportar backup completo ---
def exportar_backup():
    try:
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
    except Exception as e:
        st.error(f"Error al exportar: {e}")

# --- Salud ---
def mostrar_salud():
    t_gluc, t_meds, t_citas = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])
    
    with t_gluc:
        val = st.number_input("Valor Glucosa:", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, estado))
            conn.commit()
            st.success("Registro guardado")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        st.dataframe(g_data, use_container_width=True)
        
        borrar_id = st.number_input("ID a borrar en Glucosa:", min_value=0, step=1, key="del_gluc")
        if st.button("Borrar Registro Glucosa"):
            cursor.execute('DELETE FROM glucosa WHERE id=?', (borrar_id,))
            conn.commit()
            st.rerun()

    with t_meds:
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        h_med = st.time_input("Hora de tomarlo:")
        if st.button("Registrar Medicamento"):
            cursor.execute('INSERT INTO meds (nombre, dosis, hora) VALUES (?,?,?)', (nmed, dmed, str(h_med)))
            conn.commit()
            st.success("Medicamento registrado")
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.table(m_data)

    with t_citas:
        f_c = st.date_input("Fecha de Cita")
        d_c = st.text_input("Doctor/Especialidad")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(f_c), d_c))
            conn.commit()
            st.success("Cita agendada")
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)

# --- Finanzas ---
def mostrar_finanzas():
    st.subheader("Gestión Financiera")
    monto = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f")
    tipo = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
    cat = st.selectbox("Categoría:", ["Comida", "Salud", "Servicios", "Otros"])
    
    if st.button("Registrar Movimiento"):
        cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (monto, tipo, cat))
        conn.commit()
        st.success("Transacción registrada")
    
    f_data = pd.read_sql_query('SELECT * FROM finanzas', conn)
    st.dataframe(f_data, use_container_width=True)

# --- Interfaz Principal ---
def main():
    st.set_page_config(page_title="Nexus Quevedo Pro", layout="wide")
    st.title("📊 Nexus Quevedo - Control Total")
    
    menu = st.sidebar.radio("Navegación", ["Salud", "Finanzas", "Backup"])
    
    if menu == "Salud":
        mostrar_salud()
    elif menu == "Finanzas":
        mostrar_finanzas()
    elif menu == "Backup":
        exportar_backup()

if __name__ == "__main__":
    main()
