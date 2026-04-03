import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN DE BASE DE DATOS (PERSISTENCIA) ---
def init_db():
    conn = sqlite3.connect('nexus_data.db', check_same_thread=False)
    c = conn.cursor()
    # Tabla Finanzas: Presupuesto, Ingresos, Gastos
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT, monto REAL, fecha TEXT)''')
    # Tabla Salud: Glucosa, Medicamentos, Citas
    c.execute('''CREATE TABLE IF NOT EXISTS salud 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, valor TEXT, fecha TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- 2. FUNCIONES DE AYUDA ---
def generar_pdf(df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Reporte de {titulo}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for i in range(len(df)):
        linea = " | ".join([str(val) for val in df.iloc[i].values])
        pdf.cell(200, 10, txt=linea, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INTERFAZ DE USUARIO (STREAMLIT) ---
st.set_page_config(page_title="Nexus - Gestión Total", layout="wide")

# CSS para mejorar la estética
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .finanzas-header { color: #2E7D32; }
    .salud-header { color: #D32F2F; }
    </style>
    """, unsafe_allow_html=True)

menu = ["🏠 Inicio", "💰 Finanzas", "🏥 Salud", "📑 Documentos y Escaneo"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- SECCIÓN: INICIO ---
if choice == "🏠 Inicio":
    st.title("Bienvenido a su Panel de Control")
    st.info("Seleccione una opción en el menú lateral para comenzar a registrar sus datos.")

# --- SECCIÓN: FINANZAS ---
elif choice == "💰 Finanzas":
    st.header("📊 Gestión Financiera", divider='green')
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Registrar Movimiento")
        cat = st.selectbox("Categoría", ["Ingreso", "Gasto", "Presupuesto"])
        monto = st.number_input("Monto ($)", min_value=0.0, step=10.0)
        fecha_fin = st.date_input("Fecha", datetime.now())
        
        if st.button("Guardar en Finanzas"):
            c.execute("INSERT INTO finanzas (categoria, monto, fecha) VALUES (?,?,?)", 
                      (cat, monto, fecha_fin.strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Guardado correctamente")

    with col2:
        st.subheader("Historial y Balance")
        df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
        
        if not df_f.empty:
            ingresos = df_f[df_f['categoria'] == 'Ingreso']['monto'].sum()
            gastos = df_f[df_f['categoria'] == 'Gasto']['monto'].sum()
            balance = ingresos - gastos
            
            c_b1, c_b2 = st.columns(2)
            c_b1.metric("Balance Neto", f"${balance:,.2f}")
            c_b2.metric("Total Gastos", f"${gastos:,.2f}", delta_color="inverse")
            
            st.dataframe(df_f, use_container_width=True)
            
            id_borrar = st.number_input("ID a eliminar", min_value=0, step=1)
            if st.button("🗑️ Eliminar Registro"):
                c.execute("DELETE FROM finanzas WHERE id=?", (id_borrar,))
                conn.commit()
                st.rerun()

# --- SECCIÓN: SALUD ---
elif choice == "🏥 Salud":
    st.header("🩺 Control de Salud", divider='red')
    tab1, tab2, tab3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas Médicas"])

    with tab1:
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            valor_g = st.number_input("Nivel Glucosa (mg/dL)", min_value=0)
            if st.button("Registrar Glucosa"):
                c.execute("INSERT INTO salud (tipo, valor, fecha) VALUES (?,?,?)", 
                          ("Glucosa", str(valor_g), datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()

            # Lógica de Semáforo
            if valor_g > 0:
                if 90 <= valor_g <= 140:
                    st.success(f"🟢 VERDE: {valor_g} (Normal)")
                elif 140 < valor_g <= 160:
                    st.warning(f"🟡 AMARILLO: {valor_g} (Precaución)")
                elif valor_g > 160:
                    st.error(f"🔴 ROJO: {valor_g} (Alerta)")

        with col_s2:
            df_g = pd.read_sql_query("SELECT valor, fecha FROM salud WHERE tipo='Glucosa'", conn)
            if not df_g.empty:
                df_g['valor'] = df_g['valor'].astype(float)
                st.line_chart(df_g.set_index('fecha'))

    with tab2:
        med = st.text_input("Nombre del Medicamento")
        dosis = st.text_input("Dosis (ej: 500mg)")
        if st.button("Guardar Medicamento"):
            c.execute("INSERT INTO salud (tipo, valor, fecha) VALUES (?,?,?)", 
                      ("Medicamento", f"{med} - {dosis}", datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
        
        df_m = pd.read_sql_query("SELECT * FROM salud WHERE tipo='Medicamento'", conn)
        st.table(df_m)

    with tab3:
        cita = st.text_area("Detalles de la Cita Médica")
        if st.button("Agendar Cita"):
            c.execute("INSERT INTO salud (tipo, valor, fecha) VALUES (?,?,?)", 
                      ("Cita", cita, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

# --- SECCIÓN: ESCANEO Y DOCUMENTOS ---
elif choice == "📑 Documentos y Escaneo":
    st.header("📂 Gestión de Documentos")
    
    # Simulación de Escaneo
    archivo = st.file_uploader("Escanear/Subir Documento", type=['png', 'jpg', 'pdf'])
    if archivo:
        st.image(archivo, caption="Documento Escaneado", width=400)
        st.success("Documento almacenado en caché. Los datos no se borrarán de la vista.")

    # Generación de PDF
    st.subheader("Generar Reportes")
    if st.button("Exportar Finanzas a PDF"):
        df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
        pdf_data = generar_pdf(df_f, "Finanzas")
        st.download_button("Descargar PDF Finanzas", pdf_data, "reporte_finanzas.pdf", "application/pdf")

    # Enlaces externos
    st.subheader("Comunicación")
    c_l1, c_l2 = st.columns(2)
    with c_l1:
        st.link_button("📧 Enviar por Gmail", "https://mail.google.com/mail/?view=cm&fs=1")
    with c_l2:
        st.link_button("💬 Enviar por WhatsApp", "https://web.whatsapp.com/")

# Cierre automático de conexión (opcional según el flujo)
# conn.close()
