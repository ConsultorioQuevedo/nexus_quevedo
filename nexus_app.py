import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import io

# ==========================================
# 1. MOTOR DE PERSISTENCIA (BACKEND SÓLIDO)
# ==========================================
def init_db():
    conn = sqlite3.connect('nexus_vault_pro.db', check_same_thread=False)
    c = conn.cursor()
    # Tablas independientes para evitar cruces (Punto 4)
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, concepto TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS agenda (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS escaneos (id INTEGER PRIMARY KEY, fecha TEXT, imagen BLOB, nota TEXT)')
    conn.commit()
    return conn

db = init_db()

# ==========================================
# 2. LÓGICA DE SEMÁFORO E IA (Punto 3 y 5)
# ==========================================
def get_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    if v > 160: return "🔴 ALERTA"
    return "⚪ FUERA DE RANGO"

def motor_ia_proactivo():
    alertas = []
    df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 5", db)
    if not df_g.empty:
        promedio = df_g['valor'].mean()
        if promedio > 160: alertas.append("🚨 IA: Tendencia crítica detectada. Reduzca azúcares y consulte a su médico.")
        elif promedio > 125: alertas.append("⚠️ IA: Niveles en zona de precaución. Monitoree su próxima comida.")
    return alertas

# ==========================================
# 3. GENERADOR DE PDF PROFESIONAL (Punto 1 y 5)
# ==========================================
def crear_pdf_reporte(datos_g, datos_f):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="NEXUS PRO - RÉCORD MÉDICO Y FINANCIERO", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="RESUMEN DE GLUCOSA", ln=True)
    pdf.set_font("Arial", size=10)
    for _, row in datos_g.iterrows():
        pdf.cell(200, 8, txt=f"{row['fecha']} | Valor: {row['valor']} mg/dL | Estado: {row['estado']}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="RESUMEN FINANCIERO", ln=True)
    pdf.set_font("Arial", size=10)
    for _, row in datos_f.iterrows():
        pdf.cell(200, 8, txt=f"{row['fecha']} | {row['tipo']}: {row['concepto']} | RD$ {row['monto']:,.2f}", ln=True)
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. INTERFAZ DASHBOARD PRINCIPAL
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO ARCHITECTURE", layout="wide")
    st.title("🧬 NEXUS SMART: Control Institucional")
    st.write(f"Gestión Profesional: **Luis Rafael Quevedo**")

    tabs = st.tabs(["🏠 DASHBOARD", "🩸 SALUD", "💰 FINANZAS", "📅 AGENDA", "📸 ESCÁNER", "📤 REPORTES"])

    # --- DASHBOARD & IA ---
    with tabs[0]:
        st.subheader("🤖 Cerebro Proactivo (IA)")
        for aviso in motor_ia_proactivo(): st.warning(aviso)
        
        st.write("---")
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.info(f"Registros de Salud: {len(pd.read_sql_query('SELECT id FROM glucosa', db))}")
        with col_res2:
            st.success(f"Citas en Agenda: {len(pd.read_sql_query('SELECT id FROM agenda', db))}")

    # --- SALUD (Punto 3: Sin multiplicaciones raras) ---
    with tabs[1]:
        c1, c2 = st.columns([1, 2])
        with c1:
            val_g = st.number_input("Glucosa (mg/dL):", min_value=0.0, step=1.0, format="%.0f")
            if st.button("Guardar Registro"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                est = get_semaforo(val_g)
                db.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val_g, est))
                db.commit()
                st.rerun()
        with c2:
            df_g = pd.read_sql_query("SELECT fecha, valor, estado FROM glucosa ORDER BY id DESC", db)
            st.table(df_g)
            if st.button("🗑️ Limpiar Salud"): db.execute('DELETE FROM glucosa'); db.commit(); st.rerun()

    # --- FINANZAS (Punto 2: Diferenciación y Precisión) ---
    with tabs[2]:
        f1, f2 = st.columns([1, 2])
        with f1:
            t_fin = st.radio("Operación:", ["Ingreso", "Gasto"])
            c_fin = st.text_input("Concepto:")
            m_fin = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f", step=1.0)
            if st.button("Ejecutar Transacción"):
                fec = datetime.datetime.now().strftime("%d/%m/%Y")
                db.execute('INSERT INTO finanzas (fecha, tipo, concepto, monto) VALUES (?,?,?,?)', (fec, t_fin, c_fin, m_fin))
                db.commit()
                st.rerun()
        with f2:
            df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
            st.dataframe(df_f, use_container_width=True)
            if st.button("🗑️ Limpiar Finanzas"): db.execute('DELETE FROM finanzas'); db.commit(); st.rerun()

    # --- ESCÁNER (Punto 1) ---
    with tabs[4]:
        st.subheader("📸 Archivo de Documentos")
        cam = st.camera_input("Escanear Receta o Documento")
        nota = st.text_input("Nota del Escaneo:")
        if cam and st.button("💾 Archivar Documento"):
            fec = datetime.datetime.now().strftime("%d/%m/%Y")
            db.execute('INSERT INTO escaneos (fecha, imagen, nota) VALUES (?,?,?)', (fec, cam.read(), nota))
            db.commit()
            st.success("Documento guardado en el búnker de datos.")
        
        st.write("---")
        st.subheader("📂 Galería de Escaneos")
        df_e = pd.read_sql_query("SELECT id, fecha, nota FROM escaneos", db)
        st.table(df_e)

    # --- REPORTES Y PDF (Punto 5) ---
    with tabs[5]:
        st.subheader("📤 Exportación Institucional")
        df_g_rep = pd.read_sql_query("SELECT * FROM glucosa", db)
        df_f_rep = pd.read_sql_query("SELECT * FROM finanzas", db)
        
        # Reporte Texto
        rep_txt = f"🏥 NEXUS PRO - RÉCORD DE {datetime.datetime.now().strftime('%d/%m/%Y')}\n"
        rep_txt += "----------------------------------\n"
        rep_txt += "🩸 SALUD: " + (f"{df_g_rep['valor'].iloc[-1]} mg/dL" if not df_g_rep.empty else "N/A") + "\n"
        rep_txt += "💰 BALANCE: " + (f"RD$ {df_f_rep['monto'].sum():,.2f}" if not df_f_rep.empty else "N/A")
        
        st.text_area("Vista previa:", rep_txt)
        
        col_pdf, col_wa, col_gm = st.columns(3)
        with col_pdf:
            if st.button("📄 GENERAR PDF"):
                pdf_bytes = crear_pdf_reporte(df_g_rep, df_f_rep)
                st.download_button("Descargar PDF", data=pdf_bytes, file_name="Reporte_Nexus_Pro.pdf", mime="application/pdf")
        
        with col_wa:
            enc = urllib.parse.quote(rep_txt)
            st.markdown(f'[📲 WhatsApp](https://wa.me/?text={enc})')
        with col_gm:
            st.markdown(f'[📧 Gmail](https://mail.google.com/mail/?view=cm&fs=1&su=Reporte+Salud+Nexus&body={enc})')

if __name__ == "__main__":
    main()
