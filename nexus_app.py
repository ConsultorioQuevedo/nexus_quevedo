import streamlit as st
import pandas as pd
import sqlite3
import shutil
import os
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF
from PIL import Image
import pytesseract
import io

# --- 1. CONFIGURACIÓN INICIAL Y PERSISTENCIA ---
DB_NAME = 'nexus_ultra.db'

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    c = conn.cursor()
    # Tabla Finanzas: Incluye presupuesto para comparar
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, categoria TEXT, 
                  monto REAL, fecha TEXT, nota TEXT)''')
    # Tabla Salud: Glucosa, Medicamentos y Citas
    c.execute('''CREATE TABLE IF NOT EXISTS salud 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, valor_num REAL, 
                  texto_detalle TEXT, fecha TEXT, estado TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- 2. FUNCIONES DE LÓGICA DE NEGOCIO ---

def save_finance(tipo, cat, monto, nota):
    c.execute("INSERT INTO finanzas (tipo, categoria, monto, fecha, nota) VALUES (?,?,?,?,?)",
              (tipo, cat, monto, datetime.now().strftime("%Y-%m-%d %H:%M"), nota))
    conn.commit()

def save_health(tipo, valor, detalle, estado=""):
    c.execute("INSERT INTO salud (tipo, valor_num, texto_detalle, fecha, estado) VALUES (?,?,?,?,?)",
              (tipo, valor, detalle, datetime.now().strftime("%Y-%m-%d %H:%M"), estado))
    conn.commit()

def generar_reporte_pdf(tabla_nombre):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"REPORTE OFICIAL NEXUS - {tabla_nombre.upper()}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    
    df = pd.read_sql_query(f"SELECT * FROM {tabla_nombre}", conn)
    for i in range(len(df)):
        dato = " | ".join([f"{col}: {val}" for col, val in df.iloc[i].items()])
        pdf.multi_cell(0, 10, txt=dato, border=1)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="Nexus Ultra", layout="wide", initial_sidebar_state="expanded")

# Sidebar con Navegación y Backup
st.sidebar.title("🛡️ NEXUS ULTRA")
st.sidebar.markdown("Sistema Soberano de Datos")
menu = ["📊 Dashboard", "💰 Finanzas Pro", "🩺 Salud & Glucosa", "🔍 Escáner OCR", "⚙️ Configuración"]
choice = st.sidebar.selectbox("Navegación", menu)

# --- MÓDULO: DASHBOARD (Resumen General) ---
if choice == "📊 Dashboard":
    st.title("Vista General del Sistema")
    df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
    df_s = pd.read_sql_query("SELECT * FROM salud WHERE tipo='Glucosa'", conn)
    
    col1, col2, col3 = st.columns(3)
    if not df_f.empty:
        ing = df_f[df_f['tipo'] == 'Ingreso']['monto'].sum()
        gas = df_f[df_f['tipo'] == 'Gasto']['monto'].sum()
        col1.metric("Balance Total", f"${ing - gas:,.2f}")
        col2.metric("Total Gastos", f"${gas:,.2f}", delta_color="inverse")
    
    if not df_s.empty:
        ultima_g = df_s['valor_num'].iloc[-1]
        col3.metric("Última Glucosa", f"{ultima_g} mg/dL")

# --- MÓDULO: FINANZAS PRO ---
elif choice == "💰 Finanzas Pro":
    st.header("Gestión Financiera Avanzada")
    t1, t2 = st.tabs(["Nuevo Registro", "Historial y Gráficos"])
    
    with t1:
        with st.form("finanzas_form"):
            col_a, col_b = st.columns(2)
            f_tipo = col_a.radio("Tipo de Movimiento", ["Ingreso", "Gasto", "Presupuesto"])
            f_cat = col_b.selectbox("Categoría", ["Alimentación", "Salud", "Vivienda", "Transporte", "Ocio", "Otros"])
            f_monto = st.number_input("Monto Exacto", min_value=0.0)
            f_nota = st.text_area("Notas adicionales")
            if st.form_submit_button("Registrar en Base de Datos"):
                save_finance(f_tipo, f_cat, f_monto, f_nota)
                st.success("Registro guardado permanentemente.")
    
    with t2:
        df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
        st.dataframe(df_f, use_container_width=True)
        if not df_f.empty:
            fig, ax = plt.subplots()
            df_f[df_f['tipo'] == 'Gasto'].groupby('categoria')['monto'].sum().plot(kind='bar', ax=ax, color='salmon')
            st.pyplot(fig)
        
        st.divider()
        id_borrar = st.number_input("ID a eliminar", min_value=0, step=1)
        if st.button("🗑️ Eliminar permanentemente"):
            c.execute("DELETE FROM finanzas WHERE id=?", (id_borrar,))
            conn.commit()
            st.rerun()

# --- MÓDULO: SALUD & GLUCOSA ---
elif choice == "🩺 Salud & Glucosa":
    st.header("Control Médico y Glucémico")
    col_s1, col_s2 = st.columns([1, 2])
    
    with col_s1:
        st.subheader("Entrada de Datos")
        s_tipo = st.selectbox("Tipo de Dato", ["Glucosa", "Medicamento", "Cita Médica"])
        
        if s_tipo == "Glucosa":
            s_val = st.number_input("Nivel (mg/dL)", min_value=0.0)
            # Semáforo dinámico
            if s_val > 0:
                if 90 <= s_val <= 140: st.success(f"🟢 {s_val}: RANGO NORMAL")
                elif 140 < s_val <= 160: st.warning(f"🟡 {s_val}: PRECAUCIÓN")
                else: st.error(f"🔴 {s_val}: ALERTA ALTA")
            if st.button("Guardar Glucosa"):
                save_health("Glucosa", s_val, "Manual")
        
        elif s_tipo == "Medicamento":
            m_nom = st.text_input("Nombre Medicamento")
            m_dos = st.text_input("Dosis")
            if st.button("Guardar Medicamento"):
                save_health("Medicamento", 0, f"{m_nom} - {m_dos}")

    with col_s2:
        st.subheader("Gráfico de Tendencia")
        df_glu = pd.read_sql_query("SELECT valor_num, fecha FROM salud WHERE tipo='Glucosa'", conn)
        if not df_glu.empty:
            st.line_chart(df_glu.set_index('fecha'))
        
        st.subheader("Próximas Citas")
        st.write(pd.read_sql_query("SELECT texto_detalle, fecha FROM salud WHERE tipo='Cita Médica'", conn))

# --- MÓDULO: ESCÁNER OCR (LA JOYA DE LA CORONA) ---
elif choice == "🔍 Escáner OCR":
    st.header("Escaneo y Reconocimiento de Texto")
    st.info("Sube una foto de un recibo o receta. El sistema extraerá el texto y lo guardará.")
    
    fuente = st.radio("Origen de imagen:", ["Archivo/Galería", "Cámara Directa"])
    if fuente == "Cámara Directa":
        img_file = st.camera_input("Toma la foto")
    else:
        img_file = st.file_uploader("Subir Imagen", type=['jpg', 'png', 'jpeg'])

    if img_file:
        img = Image.open(img_file)
        st.image(img, caption="Imagen cargada", width=400)
        
        if st.button("🚀 Procesar Escaneo"):
            with st.spinner("Analizando texto con motor OCR..."):
                try:
                    # OCR Real
                    texto_final = pytesseract.image_to_string(img, lang='spa')
                    st.subheader("Texto Extraído:")
                    st.text_area("Contenido del documento", texto_final, height=300)
                    
                    # Guardar automáticamente el escaneo
                    save_health("Escaneo", 0, texto_final, "Procesado")
                    st.success("Datos almacenados en el historial de Salud.")
                except Exception as e:
                    st.error("Error: Tesseract no configurado. Si estás en móvil, usa la versión web.")

# --- MÓDULO: CONFIGURACIÓN Y EXPORTACIÓN ---
elif choice == "⚙️ Configuración":
    st.header("Herramientas del Sistema")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.subheader("Exportar Datos")
        if st.button("📦 Generar PDF Finanzas"):
            data = generar_reporte_pdf("finanzas")
            st.download_button("Descargar PDF", data, "Finanzas_Nexus.pdf")
            
        if st.button("📦 Generar PDF Salud"):
            data = generar_reporte_pdf("salud")
            st.download_button("Descargar PDF", data, "Salud_Nexus.pdf")

    with col_e2:
        st.subheader("Seguridad")
        if st.button("💾 Crear Backup de Base de Datos"):
            shutil.copy(DB_NAME, 'backup_nexus.db')
            st.success("Copia creada como 'backup_nexus.db'")
            
    st.divider()
    st.subheader("Comunicación Directa")
    st.link_button("📧 Gmail", "https://mail.google.com")
    st.link_button("💬 WhatsApp Web", "https://web.whatsapp.com")

st.sidebar.markdown("---")
st.sidebar.write(f"Última sincronización: {datetime.now().strftime('%H:%M:%S')}")
