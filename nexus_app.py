import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import io

# ==========================================
# 1. BASE DE DATOS (PERSISTENCIA REAL - Punto 4)
# ==========================================
def init_db():
    conn = sqlite3.connect('nexus_data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, concepto TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS escaneos (id INTEGER PRIMARY KEY, fecha TEXT, imagen BLOB, nota TEXT)')
    conn.commit()
    return conn

db = init_db()

# ==========================================
# 2. MOTOR DE LÓGICA E IA (Punto 3 y 5)
# ==========================================
def obtener_semaforo(v):
    if v < 90: return "⚪ Bajo"
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA"

def analizar_ia():
    alertas = []
    df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 5", db)
    if not df_g.empty:
        promedio = df_g['valor'].mean()
        if promedio > 160: alertas.append("🚨 IA: Su promedio reciente es crítico. Contacte a su médico.")
        elif promedio > 125: alertas.append("⚠️ IA: Tendencia al alza detectada. Revise su dieta.")
    return alertas

# ==========================================
# 3. INTERFAZ PROFESIONAL (Punto 1, 2, 3)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    st.title("🧬 NEXUS SMART: Control Institucional")
    st.write(f"Usuario: **Luis Rafael Quevedo** | 📱 Datos Protegidos en Disco")

    tab_dash, tab_salud, tab_fin, tab_citas, tab_scan, tab_rep = st.tabs([
        "🏠 DASHBOARD", "🩸 GLUCOSA", "💰 FINANZAS", "📅 CITAS", "📸 ESCÁNER", "📤 REPORTES"
    ])

    # --- DASHBOARD & IA ---
    with tab_dash:
        st.subheader("🤖 Análisis Proactivo")
        for a in analizar_ia(): st.warning(a)
        st.write("---")
        st.info("Utilice las pestañas superiores para gestionar sus registros médicos y financieros.")

    # --- GLUCOSA (Punto 3: Multiplicación corregida y Semáforo) ---
    with tab_salud:
        col1, col2 = st.columns([1, 2])
        with col1:
            val_g = st.number_input("Glucosa (mg/dL):", min_value=0.0, step=1.0, format="%.0f")
            if st.button("Guardar Glucosa"):
                est = obtener_semaforo(val_g)
                fec = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                db.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val_g, est))
                db.commit()
                st.rerun()
        with col2:
            data = pd.read_sql_query('SELECT fecha, valor, estado FROM glucosa ORDER BY id DESC', db)
            st.table(data)
            if st.button("🗑️ Borrar Glucosa"): db.execute('DELETE FROM glucosa'); db.commit(); st.rerun()

    # --- FINANZAS (Punto 2: Ingreso/Gasto y Formato) ---
    with tab_fin:
        f1, f2 = st.columns([1, 2])
        with f1:
            tipo = st.selectbox("Tipo:", ["Gasto", "Ingreso"])
            conc = st.text_input("Concepto:")
            # Se usa float para evitar la multiplicación de strings
            monto = st.number_input("Monto RD$:", min_value=0.0, step=1.0, format="%.2f")
            if st.button("Registrar Transacción"):
                fec = datetime.datetime.now().strftime("%d/%m/%Y")
                db.execute('INSERT INTO finanzas (fecha, tipo, concepto, monto) VALUES (?,?,?,?)', (fec, tipo, conc, monto))
                db.commit()
                st.rerun()
        with f2:
            df_f = pd.read_sql_query('SELECT * FROM finanzas', db)
            st.dataframe(df_f, use_container_width=True)
            if st.button("🗑️ Vaciar Finanzas"): db.execute('DELETE FROM finanzas'); db.commit(); st.rerun()

    # --- ESCÁNER Y PDF (Punto 1) ---
    with tab_scan:
        st.subheader("📸 Módulo de Escaneo y Archivo")
        captura = st.camera_input("Escanear Documento")
        nota_scan = st.text_input("Nota del documento:")
        if captura and st.button("💾 Archivar Escaneo"):
            fec = datetime.datetime.now().strftime("%d/%m/%Y")
            db.execute('INSERT INTO escaneos (fecha, imagen, nota) VALUES (?,?,?)', (fec, captura.read(), nota_scan))
            db.commit()
            st.success("Documento guardado en el archivo.")
        
        st.write("---")
        st.subheader("📂 Documentos Guardados")
        df_docs = pd.read_sql_query('SELECT id, fecha, nota FROM escaneos', db)
        st.table(df_docs)

    # --- REPORTES (Punto 5: Elegante tipo Récord Médico) ---
    with tab_rep:
        st.subheader("📤 Exportar Información Profesional")
        
        # Construcción del reporte elegante
        rep_med = "🏥 *NEXUS PRO - RÉCORD MÉDICO*\n"
        rep_med += "---------------------------\n"
        rep_med += "🩸 *ESTADO DE GLUCOSA:*\n"
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC LIMIT 10", db)
        for _, r in df_g.iterrows(): rep_med += f"• {r['fecha']}: {r['valor']} mg/dL ({r['estado']})\n"
        
        st.text_area("Previsualización:", rep_med, height=200)
        
        enc = urllib.parse.quote(rep_med)
        c_wa, c_gm = st.columns(2)
        c_wa.markdown(f'[📲 WhatsApp Profesional](https://wa.me/?text={enc})')
        c_gm.markdown(f'[📧 Gmail Institucional](https://mail.google.com/mail/?view=cm&fs=1&su=Reporte+Nexus+Salud&body={enc})')

if __name__ == "__main__":
    main()
