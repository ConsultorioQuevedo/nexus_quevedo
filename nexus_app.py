import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import matplotlib.pyplot as plt
import os

# --- CONFIGURACIÓN E INICIALIZACIÓN ---
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
    # Para máxima compatibilidad en el servidor, usamos CSV que no requiere librerías extra
    tablas = ["glucosa", "meds", "citas", "finanzas"]
    for tabla in tablas:
        df = pd.read_sql_query(f'SELECT * FROM {tabla}', conn)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 Descargar {tabla.capitalize()} (CSV)",
            data=csv,
            file_name=f"nexus_{tabla}_{datetime.date.today()}.csv",
            mime='text/csv',
        )

# --- CAPA 2: FINANZAS INTELIGENTES ---
def mostrar_finanzas():
    st.subheader("💰 Gestión Financiera Pro")
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
    if st.button("Borrar Registro Finanzas"):
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

    if presupuesto_total > 0 and balance < presupuesto_total:
        st.warning("⚠️ IA: Balance bajo el presupuesto. Reduzca gastos no esenciales.")
    elif presupuesto_total > 0:
        st.info("✅ IA: Balance saludable dentro del presupuesto.")

    if not data[data['tipo']=="Gasto"].empty:
        gastosporcat = data[data['tipo']=="Gasto"].groupby("categoria")['monto'].sum()
        fig, ax = plt.subplots()
        ax.pie(gastosporcat, labels=gastosporcat.index, autopct='%1.1f%%')
        ax.set_title("Distribución de Gastos")
        st.pyplot(fig)
        plt.close(fig)

# --- CAPA 1 & 3: SALUD PREDICTIVA Y ORGANIZACIÓN ---
def mostrar_salud():
    t_gluc, t_meds, t_citas, t_scan = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas", "📸 Escáner"])
    
    with t_gluc:
        val = st.number_input("Valor Glucosa:", min_value=0, step=1)
        if st.button("Guardar Glucosa"):
            estado = obtener_semaforo(val)
            fec = datetime.datetime.now().strftime("%d/%m %H:%M")
            cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val, estado))
            conn.commit()
            st.success("Registro de glucosa guardado")
        
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        st.write(g_data)
        
        borrar_id_g = st.number_input("ID a borrar en Glucosa:", min_value=0, step=1, key="glu_del")
        if st.button("Borrar Registro Glucosa"):
            cursor.execute('DELETE FROM glucosa WHERE id=?', (borrar_id_g,))
            conn.commit()
            st.rerun()

        if not g_data.empty:
            prom = g_data['valor'].mean()
            if prom > 140:
                st.warning(f"🤖 IA Salud: Promedio {prom:.1f} elevado. Ajuste su dieta.")
            else:
                st.info(f"🤖 IA Salud: Promedio {prom:.1f} en rango saludable.")
            
            fig, ax = plt.subplots()
            ax.plot(g_data['fecha'], g_data['valor'], marker='o', color='red')
            ax.set_title("Tendencia de Glucosa")
            plt.xticks(rotation=45)
            st.pyplot(fig)
            plt.close(fig)

    with t_meds:
        nmed = st.text_input("Medicamento:")
        dmed = st.text_input("Dosis:")
        if st.button("Registrar Medicamento"):
            cursor.execute('INSERT INTO meds (nombre, dosis) VALUES (?,?)', (nmed, dmed))
            conn.commit()
        
        m_data = pd.read_sql_query('SELECT * FROM meds', conn)
        st.write(m_data)
        
        borrar_id_m = st.number_input("ID a borrar en Medicamentos:", min_value=0, step=1, key="med_del")
        if st.button("Borrar Medicamento"):
            cursor.execute('DELETE FROM meds WHERE id=?', (borrar_id_m,))
            conn.commit()
            st.rerun()

        if not m_data.empty:
            st.info(f"💊 Recordatorio: Tomar {m_data.iloc[-1]['nombre']} ({m_data.iloc[-1]['dosis']}) hoy.")

    with t_citas:
        fc = st.date_input("Fecha de Cita")
        dc = st.text_input("Doctor/Especialidad")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(fc), dc))
            conn.commit()
        
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        st.write(c_data)
        
        borrar_id_c = st.number_input("ID a borrar en Citas:", min_value=0, step=1, key="cit_del")
        if st.button("Borrar Cita"):
            cursor.execute('DELETE FROM citas WHERE id=?', (borrar_id_c,))
            conn.commit()
            st.rerun()

        hoy = datetime.date.today()
        for _, row in c_data.iterrows():
            try:
                fecha_cita = datetime.datetime.strptime(row['fecha'], "%Y-%m-%d").date()
                dias_restantes = (fecha_cita - hoy).days
                if 0 <= dias_restantes <= 2:
                    st.warning(f"📅 Sr. Quevedo: Cita con {row['doctor']} en {dias_restantes} días.")
            except: pass

    with t_scan:
        img = st.camera_input("Escáner de Documentos")
        if img:
            pdf_file = generarpdf(img)
            st.success("PDF generado exitosamente")
            with open(pdf_file, "rb") as f:
                st.download_button("📥 Descargar PDF", f, file_name=pdf_file)
            
            msg = urllib.parse.quote(f"Sr. Quevedo: Documento enviado desde NEXUS PRO el {datetime.datetime.now().strftime('%d/%m/%Y')}")
            st.markdown(f'[📲 Compartir por WhatsApp](https://wa.me/?text={msg})')
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Reporte+Nexus&body={msg}"
            st.markdown(f'[📧 Compartir por Gmail]({gmail_url})')

# --- FUNCIÓN PRINCIPAL ---
def main():
    st.set_page_config(page_title="NEXUS PRO - Sr. Quevedo", layout="wide")
    st.title("🛡️ NEXUS PRO: Control Total de Vida")
    
    menu = st.sidebar.radio("Navegación", ["Panel Principal", "Respaldos"])
    
    if menu == "Panel Principal":
        tab_f, tab_s = st.tabs(["💰 Finanzas Inteligentes", "🩺 Salud Predictiva"])
        with tab_f: mostrar_finanzas()
        with tab_s: mostrar_salud()
    else:
        exportar_backup()

if __name__ == "__main__":
    main()
