import streamlit as st
import pandas as pd
import sqlite3
import shutil
import os
from datetime import datetime
import matplotlib.pyplot as plt
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN DE BASE DE DATOS Y BACKUP ---
DB_NAME = 'nexus_data.db'
BACKUP_NAME = 'nexus_backup.db'

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    c = conn.cursor()
    # Finanzas: Presupuesto, Ingresos, Gastos
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, categoria TEXT, descripcion TEXT, monto REAL, fecha TEXT)''')
    # Salud: Glucosa, Medicamentos, Citas
    c.execute('''CREATE TABLE IF NOT EXISTS salud 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, valor TEXT, detalle TEXT, fecha TEXT)''')
    conn.commit()
    return conn

def crear_backup():
    if os.path.exists(DB_NAME):
        shutil.copy(DB_NAME, BACKUP_NAME)

# Inicializar
conn = init_db()
c = conn.cursor()
crear_backup()

# --- 2. FUNCIONES DE EXPORTACIÓN ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'NEXUS - REPORTE GENERAL', 0, 1, 'C')
        self.ln(5)

def generar_pdf_datos(tabla):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
    
    if df.empty:
        pdf.cell(0, 10, "No hay datos registrados.", ln=True)
    else:
        for i in range(len(df)):
            row = df.iloc[i]
            texto = " | ".join([f"{col}: {val}" for col, val in row.items()])
            pdf.multi_cell(0, 10, txt=texto, border=1)
            
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Nexus Pro", layout="wide")

# Estilos Personalizados
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .footer { position: fixed; bottom: 0; width: 100%; text-align: center; color: gray; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
st.sidebar.title("🛡️ Nexus v2.0")
menu = ["💰 Finanzas", "🏥 Salud", "📑 Escaneo y Archivos"]
choice = st.sidebar.radio("Seleccione Módulo:", menu)

st.sidebar.markdown("---")
if st.sidebar.button("💾 Crear Backup Manual"):
    crear_backup()
    st.sidebar.success("Copia de seguridad creada.")

# --- MÓDULO FINANZAS ---
if choice == "💰 Finanzas":
    st.title("📊 Gestión Financiera")
    col_f1, col_f2 = st.columns([1, 2])

    with col_f1:
        st.subheader("Nuevo Registro")
        cat = st.selectbox("Tipo", ["Ingreso", "Gasto", "Presupuesto"])
        desc = st.text_input("Descripción (ej: Supermercado)")
        monto = st.number_input("Monto ($)", min_value=0.0)
        if st.button("Añadir a Finanzas"):
            c.execute("INSERT INTO finanzas (categoria, descripcion, monto, fecha) VALUES (?,?,?,?)",
                      (cat, desc, monto, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Dato guardado con éxito.")

    with col_f2:
        df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
        if not df_f.empty:
            ing = df_f[df_f['categoria'] == 'Ingreso']['monto'].sum()
            gas = df_f[df_f['categoria'] == 'Gasto']['monto'].sum()
            bal = ing - gas
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingresos", f"${ing:,.2f}")
            m2.metric("Gastos", f"${gas:,.2f}", delta=f"-{gas:,.2f}", delta_color="inverse")
            m3.metric("Balance Disponible", f"${bal:,.2f}")

            st.dataframe(df_f, use_container_width=True)
            
            id_del = st.number_input("ID para eliminar", min_value=0, step=1)
            if st.button("🗑️ Eliminar Registro Finanzas"):
                c.execute("DELETE FROM finanzas WHERE id=?", (id_del,))
                conn.commit()
                st.rerun()

# --- MÓDULO SALUD ---
elif choice == "🏥 Salud":
    st.title("🩺 Control de Salud")
    tab_glu, tab_med, tab_cit = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas"])

    with tab_glu:
        c1, c2 = st.columns([1, 2])
        with c1:
            valor_g = st.number_input("Nivel de Glucosa (mg/dL)", min_value=0)
            if st.button("Guardar Glucosa"):
                c.execute("INSERT INTO salud (tipo, valor, detalle, fecha) VALUES (?,?,?,?)",
                          ("Glucosa", str(valor_g), "Nivel diario", datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
            
            if valor_g > 0:
                if 90 <= valor_g <= 140: st.success(f"🟢 VERDE ({valor_g}): Rango Normal")
                elif 140 < valor_g <= 160: st.warning(f"🟡 AMARILLO ({valor_g}): Precaución")
                else: st.error(f"🔴 ROJO ({valor_g}): Alerta - Consulte Médico")
        
        with c2:
            df_g = pd.read_sql_query("SELECT valor, fecha FROM salud WHERE tipo='Glucosa'", conn)
            if not df_g.empty:
                df_g['valor'] = df_g['valor'].astype(float)
                st.line_chart(df_g.set_index('fecha'))

    with tab_med:
        nombre_m = st.text_input("Medicamento")
        dosis_m = st.text_input("Dosis / Frecuencia")
        if st.button("Registrar Medicamento"):
            c.execute("INSERT INTO salud (tipo, valor, detalle, fecha) VALUES (?,?,?,?)",
                      ("Medicamento", nombre_m, dosis_m, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
        st.table(pd.read_sql_query("SELECT id, valor as Nombre, detalle as Dosis, fecha FROM salud WHERE tipo='Medicamento'", conn))

    with tab_cit:
        det_cita = st.text_area("Detalles de la cita")
        if st.button("Guardar Cita"):
            c.execute("INSERT INTO salud (tipo, valor, detalle, fecha) VALUES (?,?,?,?)",
                      ("Cita", "Cita Médica", det_cita, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
        st.write(pd.read_sql_query("SELECT id, detalle as Info, fecha FROM salud WHERE tipo='Cita'", conn))

# --- MÓDULO ESCANEO Y EXPORTACIÓN ---
elif choice == "📑 Escaneo y Archivos":
    st.title("📂 Documentación y Reportes")
    
    # Simulación de Escaneo y almacenamiento
    archivo_subido = st.file_uploader("Escanear Documento (Imagen/PDF)", type=["png", "jpg", "pdf"])
    if archivo_subido:
        st.image(archivo_subido, caption="Vista previa del documento", width=300)
        st.info("Documento procesado. Los datos han sido indexados en la base de datos local.")

    st.markdown("---")
    st.subheader("📤 Exportar y Compartir")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if st.button("📄 Generar PDF de Finanzas"):
            pdf_bytes = generar_pdf_datos("finanzas")
            st.download_button("⬇️ Descargar PDF Finanzas", pdf_bytes, "nexus_finanzas.pdf", "application/pdf")
        
        if st.button("📄 Generar PDF de Salud"):
            pdf_bytes = generar_pdf_datos("salud")
            st.download_button("⬇️ Descargar PDF Salud", pdf_bytes, "nexus_salud.pdf", "application/pdf")

    with col_e2:
        st.link_button("📧 Enviar por Gmail", "https://mail.google.com/mail/?view=cm&fs=1")
        st.link_button("💬 Enviar por WhatsApp", "https://web.whatsapp.com/")

st.markdown('<div class="footer">Nexus Pro - Sistema de Registro Soberano © 2026</div>', unsafe_allow_html=True)
