import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import os

def init_db():
    # Corregido: check_same_thread
    conn = sqlite3.connect('nexuspro.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, monto REAL, tipo TEXT)')
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

def mostrar_finanzas():
    st.subheader("Gestión Financiera")
    presupuesto = st.number_input("Presupuesto mensual (RD$):", min_value=0.0, format="%.2f", step=100.0)
    if st.button("Guardar Presupuesto"):
        cursor.execute('INSERT INTO finanzas (monto, tipo) VALUES (?,?)', (presupuesto, "Presupuesto"))
        conn.commit()
        st.success(f"Presupuesto registrado: RD$ {presupuesto:,.2f}")
    
    monto = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f", step=1.0)
    tipo = st.selectbox("Tipo de movimiento:", ["Ingreso", "Gasto"])
    if st.button("Registrar Movimiento"):
        cursor.execute('INSERT INTO finanzas (monto, tipo) VALUES (?,?)', (monto, tipo))
        conn.commit()
        st.success(f"{tipo} registrado: RD$ {monto:,.2f}")
    
    data = pd.read_sql_query('SELECT * FROM finanzas', conn)
    st.write(data)
    
    borrar_id = st.number_input("ID a borrar en Finanzas:", min_value=0, step=1, key="fin_del")
    if st.button("Borrar Finanzas"):
        cursor.execute('DELETE FROM finanzas WHERE id=?', (borrar_id,))
        conn.commit()
        st.success("Registro eliminado")

    ingresos = data[data['tipo']=="Ingreso"]['monto'].sum()
    gastos = data[data['tipo']=="Gasto"]['monto'].sum()
    presupuesto_total = data[data['tipo']=="Presupuesto"]['monto'].sum()
    balance = ingresos - gastos
    
    st.metric("Ingresos", f"RD$ {ingresos:,.2f}")
    st.metric("Gastos", f"RD$ {gastos:,.2f}")
    st.metric("Balance", f"RD$ {balance:,.2f}")
    st.metric("Presupuesto", f"RD$ {presupuesto_total:,.2f}")
    
    if balance < presupuesto_total:
        st.warning("⚠️ El balance está por debajo del presupuesto. IA recomienda reducir gastos.")
    else:
        st.info("✅ Balance dentro del presupuesto.")

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
        
        borrar_id = st.number_input("ID a borrar en Glucosa:", min_value=0, step=1, key="glu_del")
        if st.button("Borrar Glucosa"):
            cursor.execute('DELETE FROM glucosa WHERE id=?', (borrar_id,))
            conn.commit()
            st.success("Registro eliminado")

    with t_meds:
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        if st.button("Registrar Medicamento"):
            cursor.execute('INSERT INTO meds (nombre, dosis) VALUES (?,?)', (nmed, dmed))
            conn.commit()
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.write(m_data)
        
        borrar_id = st.number_input("ID a borrar en Medicamentos:", min_value=0, step=1, key="med_del")
        if st.button("Borrar Medicamento"):
            cursor.execute('DELETE FROM meds WHERE id=?', (borrar_id,))
            conn.commit()
            st.success("Registro eliminado")

    with t_citas:
        fc = st.date_input("Fecha")
        dc = st.text_input("Doctor")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(fc), dc))
            conn.commit()
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)
        
        borrar_id = st.number_input("ID a borrar en Citas:", min_value=0, step=1, key="cit_del")
        if st.button("Borrar Cita"):
            cursor.execute('DELETE FROM citas WHERE id=?', (borrar_id,))
            conn.commit()
            st.success("Registro eliminado")

    with t_scan:
        if st.checkbox("Abrir Escáner"):
            img = st.camera_input("Escanee documento")
            if img:
                pdf_file = generarpdf(img, "documento_nexus.pdf")
                cursor.execute(
                    'INSERT INTO escaneo (fecha, archivo) VALUES (?,?)',
                    (datetime.datetime.now().strftime("%d/%m %H:%M"), pdf_file)
                )
                conn.commit()
                st.success("Documento escaneado y guardado como PDF")
                with open(pdf_file, "rb") as f:
                    st.download_button("📥 Descargar PDF", f, file_name=pdf_file)
                
                # Botones de compartir
                text_share = urllib.parse.quote("Documento escaneado disponible en PDF")
                st.markdown(f'[📲 Compartir por WhatsApp](https://wa.me/?text={text_share})')
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Documento+Escaneado&body={text_share}"
                st.markdown(f'[📧 Compartir por Gmail]({gmail_url})')

def generar_reportes():
    gdata = pd.read_sql_query('SELECT * FROM glucosa', conn)
    cdata = pd.read_sql_query('SELECT * FROM citas', conn)
    fdata = pd.read_sql_query('SELECT * FROM finanzas', conn)
    
    reporte = "📑 Reporte Nexus\n\n"
    reporte += "🩸 Glucosa:\n"
    for _, r in gdata.iterrows():
        reporte += f"- {r['fecha']}: {r['valor']} ({r['estado']})\n"
    
    reporte += "\n📅 Citas:\n"
    for _, c in cdata.iterrows():
        reporte += f"- {c['fecha']}: {c['doctor']}\n"
    
    reporte += "\n💰 Finanzas:\n"
    ingresos = fdata[fdata['tipo']=="Ingreso"]['monto'].sum()
    gastos = fdata[fdata['tipo']=="Gasto"]['monto'].sum()
    presupuesto_total = fdata[fdata['tipo']=="Presupuesto"]['monto'].sum()
    balance = ingresos - gastos
    reporte += f"Ingresos: RD$ {ingresos:,.2f}\nGastos: RD$ {gastos:,.2f}\nBalance: RD$ {balance:,.2f}\n"
    
    st.text_area("Vista previa del reporte:", reporte, height=200)
    rep_enc = urllib.parse.quote(reporte)
    st.markdown(f'[📲 WhatsApp](https://wa.me/?text={rep_enc})')

def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    st.title("📊 Dashboard Principal - Finanzas & Salud Inteligente")
    t_fin, t_salud, t_rep = st.tabs(["💰 Finanzas", "🩺 Salud", "📤 Reportes"])
    with t_fin: mostrar_finanzas()
    with t_salud: mostrar_salud()
    with t_rep: generar_reportes()

if __name__ == "__main__":
    main()
