import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import matplotlib.pyplot as plt
import os

def init_db():
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
    if os.path.exists(img_path): os.remove(img_path)
    return nombre_archivo

def exportar_backup():
    st.subheader("📦 Soberanía de Datos - Backup")
    for tabla in ["glucosa", "meds", "citas", "finanzas"]:
        df = pd.read_sql_query(f'SELECT * FROM {tabla}', conn)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(f"📥 Descargar {tabla.capitalize()} (CSV)", csv, f"backup_{tabla}.csv", "text/csv")

def mostrar_finanzas():
    st.subheader("💰 Gestión Financiera Pro")
    presupuesto = st.number_input("Presupuesto mensual (RD$):", min_value=0.0, format="%.2f")
    if st.button("Guardar Presupuesto"):
        cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (presupuesto, "Presupuesto","General"))
        conn.commit()
        st.success("Presupuesto guardado")

    monto = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f")
    tipo = st.selectbox("Tipo:", ["Ingreso", "Gasto"])
    cat = st.selectbox("Categoría:", ["Comida","Salud","Servicios","Otros"])
    if st.button("Registrar Movimiento"):
        cursor.execute('INSERT INTO finanzas (monto, tipo, categoria) VALUES (?,?,?)', (monto, tipo, cat))
        conn.commit()
        st.success("Registrado")

    data = pd.read_sql_query('SELECT * FROM finanzas', conn)
    st.write(data)

    borrar_id = st.number_input("ID a borrar en Finanzas:", min_value=0, step=1, key="fin_del")
    if st.button("Borrar Registro Finanzas"):
        cursor.execute('DELETE FROM finanzas WHERE id=?', (borrar_id,))
        conn.commit()
        st.rerun()

    ingresos = data[data['tipo']=="Ingreso"]['monto'].sum()
    gastos = data[data['tipo']=="Gasto"]['monto'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos", f"RD$ {ingresos:,.2f}")
    col2.metric("Gastos", f"RD$ {gastos:,.2f}")
    col3.metric("Balance", f"RD$ {ingresos-gastos:,.2f}")

    if not data[data['tipo']=="Gasto"].empty:
        fig, ax = plt.subplots()
        data[data['tipo']=="Gasto"].groupby("categoria")['monto'].sum().plot(kind='pie', autopct='%1.1f%%', ax=ax)
        ax.set_ylabel('')
        st.pyplot(fig)
        plt.close(fig)

def mostrar_salud():
    t1, t2, t3, t4 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas", "📸 Escáner"])
    
    with t1:
        val = st.number_input("Valor Glucosa:", min_value=0)
        if st.button("Guardar Glucosa"):
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, obtener_semaforo(val)))
            conn.commit()
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        st.write(g_data)
        
        borrar_id_glu = st.number_input("ID a borrar en Glucosa:", min_value=0, step=1, key="glu_del")
        if st.button("Borrar Registro Glucosa"):
            cursor.execute('DELETE FROM glucosa WHERE id=?', (borrar_id_glu,))
            conn.commit()
            st.rerun()

        if not g_data.empty:
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o', color='red')
            plt.xticks(rotation=45)
            st.pyplot(fig)
            plt.close(fig)

    with t2:
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        if st.button("Registrar Med"):
            cursor.execute('INSERT INTO meds (nombre, dosis) VALUES (?,?)', (nmed, dmed))
            conn.commit()
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.write(m_data)

        borrar_id_med = st.number_input("ID a borrar en Medicamentos:", min_value=0, step=1, key="med_del")
        if st.button("Borrar Registro Med"):
            cursor.execute('DELETE FROM meds WHERE id=?', (borrar_id_med,))
            conn.commit()
            st.rerun()

        if not m_data.empty:
            st.info(f"💊 Recordatorio: {m_data.iloc[-1]['nombre']} ({m_data.iloc[-1]['dosis']})")

    with t3:
        fc = st.date_input("Fecha Cita")
        dc = st.text_input("Doctor")
        if st.button("Agendar"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(fc), dc))
            conn.commit()
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)

        borrar_id_cit = st.number_input("ID a borrar en Citas:", min_value=0, step=1, key="cit_del")
        if st.button("Borrar Registro Cita"):
            cursor.execute('DELETE FROM citas WHERE id=?', (borrar_id_cit,))
            conn.commit()
            st.rerun()

        hoy = datetime.date.today()
        for _, r in c_data.iterrows():
            try:
                f_cita = datetime.datetime.strptime(r['fecha'], "%Y-%m-%d").date()
                if 0 <= (f_cita - hoy).days <= 2:
                    st.warning(f"📅 Cita con {r['doctor']} en {(f_cita-hoy).days} días")
            except: pass

    with t4:
        img = st.camera_input("Escanear")
        if img:
            pdf_file = generarpdf(img)
            st.success("PDF Creado")
            with open(pdf_file, "rb") as f:
                st.download_button("📥 Descargar PDF", f, file_name=pdf_file)
            
            # WhatsApp y Gmail restaurados
            msg = urllib.parse.quote(f"Sr. Quevedo: Documento escaneado el {datetime.datetime.now().strftime('%d/%m/%Y')}")
            st.markdown(f'[📲 Compartir por WhatsApp](https://wa.me/?text={msg})')
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Documento+Nexus&body={msg}"
            st.markdown(f'[📧 Compartir por Gmail]({gmail_url})')

def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    st.title("🛡️ NEXUS PRO - Panel de Control Sr. Quevedo")
    menu = st.sidebar.radio("Navegación", ["Principal", "Backup"])
    if menu == "Principal":
        tab_f, tab_s = st.tabs(["💰 Finanzas", "🩺 Salud"])
        with tab_f: mostrar_finanzas()
        with tab_s: mostrar_salud()
    else:
        exportar_backup()

if __name__ == "__main__":
    main()
