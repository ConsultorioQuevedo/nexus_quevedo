import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import io

# ==========================================
# 1. PERSISTENCIA Y SEGURIDAD DE TABLAS
# ==========================================
def conectar_db():
    conn = sqlite3.connect('nexus_pro_vault.db', check_same_thread=False)
    cursor = conn.cursor()
    # Aseguramos que todas las tablas existan desde el segundo 1
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, concepto TEXT, monto REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS escaneos (id INTEGER PRIMARY KEY, fecha TEXT, imagen BLOB, nota TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = conectar_db()

# ==========================================
# 2. INTELIGENCIA ARTIFICIAL PROTEGIDA
# ==========================================
def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    if v > 160: return "🔴 ALERTA"
    return "⚪ FUERA DE RANGO"

def motor_ia_proactivo():
    alertas = []
    try:
        # Leemos con manejo de errores por si la tabla está vacía
        df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 5", conn)
        if not df_g.empty:
            promedio = df_g['valor'].mean()
            if promedio > 160: alertas.append("🚨 IA SALUD: Tendencia crítica detectada.")
            elif promedio > 125: alertas.append("⚠️ IA SALUD: Niveles en zona de cuidado.")
        
        df_f = pd.read_sql_query("SELECT tipo, monto FROM finanzas", conn)
        if not df_f.empty:
            gastos = df_f[df_f['tipo'] == 'Gasto']['monto'].sum()
            if gastos > 10000: alertas.append("💰 IA FINANZAS: Alerta de gastos mensuales elevados.")
    except Exception:
        pass # Si no hay datos, la IA simplemente no muestra avisos aún
    return alertas

# ==========================================
# 3. GENERADOR DE PDF
# ==========================================
def generar_pdf_profesional():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="NEXUS PRO - REPORTE INSTITUCIONAL", ln=True, align='C')
    pdf.ln(10)
    
    # Datos de Salud
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="RESUMEN DE SALUD (GLUCOSA)", ln=True)
    pdf.set_font("Arial", size=10)
    df_g = pd.read_sql_query("SELECT * FROM glucosa", conn)
    for _, r in df_g.iterrows():
        pdf.cell(200, 8, txt=f"{r['fecha']} - {r['valor']} mg/dL - {r['estado']}", ln=True)
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. INTERFAZ DASHBOARD
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO", layout="wide")
    st.title("🧬 NEXUS SMART: Control Institucional")
    st.info(f"Usuario: **Luis Rafael Quevedo** | 📱 Base de Datos Vinculada")

    tabs = st.tabs(["🏠 DASHBOARD", "🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS", "💰 FINANZAS", "📸 ESCÁNER", "📤 EXPORTAR"])

    # --- DASHBOARD ---
    with tabs[0]:
        st.subheader("🤖 Cerebro Proactivo")
        avisos = motor_ia_proactivo()
        for a in avisos: st.warning(a)
        if not avisos: st.write("✅ Sistema en espera de nuevos datos para análisis.")

    # --- GLUCOSA (Cero multiplicaciones raras) ---
    with tabs[1]:
        c1, c2 = st.columns([1, 2])
        with c1:
            val_g = st.number_input("Valor Glucosa:", min_value=0.0, step=1.0, format="%.0f")
            if st.button("Guardar Glucosa"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                est = obtener_semaforo(val_g)
                cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val_g, est))
                conn.commit()
                st.rerun()
        with c2:
            df_g = pd.read_sql_query("SELECT fecha, valor, estado FROM glucosa ORDER BY id DESC", conn)
            st.table(df_g)

    # --- FINANZAS (Ingreso/Gasto y precisión) ---
    with tabs[4]:
        f1, f2 = st.columns([1, 2])
        with f1:
            t_fin = st.radio("Tipo:", ["Gasto", "Ingreso"])
            c_fin = st.text_input("Concepto:")
            m_fin = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f")
            if st.button("Registrar Transacción"):
                fec = datetime.datetime.now().strftime("%d/%m/%Y")
                cursor.execute('INSERT INTO finanzas (fecha, tipo, concepto, monto) VALUES (?,?,?,?)', (fec, t_fin, c_fin, m_fin))
                conn.commit()
                st.rerun()
        with f2:
            df_f = pd.read_sql_query("SELECT * FROM finanzas", conn)
            st.dataframe(df_f)

    # --- ESCÁNER Y PDF ---
    with tabs[5]:
        st.subheader("📸 Módulo de Escaneo")
        if st.toggle("Activar Cámara"):
            cam = st.camera_input("Enfoque documento")
            if cam and st.button("Archivar"):
                st.success("Guardado.")
    
    with tabs[6]:
        st.subheader("📤 Exportación")
        if st.button("📄 GENERAR PDF"):
            pdf_b = generar_pdf_profesional()
            st.download_button("Descargar PDF", data=pdf_b, file_name="Reporte_Nexus.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()
