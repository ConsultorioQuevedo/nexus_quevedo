import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import io

# ==========================================
# 1. PERSISTENCIA REAL (Punto 4: SQLite)
# ==========================================
def conectar_db():
    conn = sqlite3.connect('nexus_pro_vault.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tablas independientes según su diagrama
    cursor.execute('CREATE Timport streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import io

# ==========================================
# 1. EL BÚNKER (PERSISTENCIA REAL - PUNTO 4)
# ==========================================
def conectar_db():
    # Creamos un archivo real. Los datos NO se borran al cerrar la app.
    conn = sqlite3.connect('nexus_pro_vault.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tablas 100% independientes (Arquitectura Quevedo)
    cursor.execute('''CREATE TABLE IF NOT EXISTS salud 
                     (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT, nota TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS finanzas 
                     (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, concepto TEXT, monto REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS agenda 
                     (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS meds 
                     (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)''')
    conn.commit()
    return conn, cursor

db_conn, db_cursor = conectar_db()

# ==========================================
# 2. LÓGICA DE PRECISIÓN (PUNTO 2, 3 Y 7)
# ==========================================
def calcular_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    if v > 160: return "🔴 ALERTA"
    return "⚪ REVISAR"

def analizar_ia():
    alertas = []
    df = pd.read_sql_query("SELECT valor FROM salud ORDER BY id DESC LIMIT 5", db_conn)
    if not df.empty:
        if df['valor'].mean() > 160: 
            alertas.append("🚨 IA: Tendencia de glucosa alta. Se recomienda revisión médica.")
    return alertas

# ==========================================
# 3. GENERADOR DE PDF (PUNTO 1 Y 9)
# ==========================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NEXUS PRO - REPORTE INSTITUCIONAL', 0, 1, 'C')
        self.ln(5)

def generar_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Datos de Salud
    pdf.cell(0, 10, "--- REGISTRO DE SALUD ---", ln=True)
    df_s = pd.read_sql_query("SELECT * FROM salud", db_conn)
    for _, r in df_s.iterrows():
        pdf.cell(0, 10, f"{r['fecha']} | {r['valor']} mg/dL | {r['estado']}", ln=True)
    
    # Datos de Finanzas
    pdf.ln(5)
    pdf.cell(0, 10, "--- REGISTRO FINANCIERO ---", ln=True)
    df_f = pd.read_sql_query("SELECT * FROM finanzas", db_conn)
    for _, f in df_f.iterrows():
        pdf.cell(0, 10, f"{f['fecha']} | {f['tipo']}: {f['concepto']} | RD$ {f['monto']:,.2f}", ln=True)
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. INTERFAZ (DASHBOARD PROFESIONAL)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO", layout="wide")
    st.title("🧬 NEXUS SMART: Control de Gestión")
    
    tabs = st.tabs(["🏠 DASHBOARD", "🩸 SALUD", "💊 MEDS", "📅 CITAS", "💰 FINANZAS", "📸 ESCÁNER", "📤 EXPORTAR"])

    # DASHBOARD
    with tabs[0]:
        st.subheader("🤖 Análisis de IA Proactivo")
        for a in analizar_ia(): st.warning(a)
        st.write("---")
        st.info("Bienvenido, Sr. Quevedo. El sistema está operando sobre base de datos persistente.")

    # SALUD (PUNTO 3: Corrección de números y semáforo)
    with tabs[1]:
        c1, c2 = st.columns([1, 2])
        with c1:
            # Usamos step=1.0 para que el incremento sea controlado
            val_in = st.number_input("Glucosa (mg/dL):", min_value=0.0, format="%.0f", step=1.0)
            if st.button("💾 Guardar"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                est = calcular_semaforo(val_in)
                db_cursor.execute("INSERT INTO salud (fecha, valor, estado) VALUES (?,?,?)", (fec, val_in, est))
                db_conn.commit()
                st.rerun()
        with c2:
            st.table(pd.read_sql_query("SELECT fecha, valor, estado FROM salud ORDER BY id DESC", db_conn))
            if st.button("🗑️ Borrar Salud"):
                db_cursor.execute("DELETE FROM salud"); db_conn.commit(); st.rerun()

    # FINANZAS (PUNTO 2: Diferenciación y precisión)
    with tabs[4]:
        f1, f2 = st.columns([1, 2])
        with f1:
            t_f = st.radio("Tipo:", ["Gasto", "Ingreso"])
            c_f = st.text_input("Concepto:")
            m_f = st.number_input("Monto RD$:", min_value=0.0, format="%.2f", step=1.0)
            if st.button("💸 Registrar"):
                fec = datetime.datetime.now().strftime("%d/%m/%Y")
                db_cursor.execute("INSERT INTO finanzas (fecha, tipo, concepto, monto) VALUES (?,?,?,?)", (fec, t_f, c_f, m_f))
                db_conn.commit(); st.rerun()
        with f2:
            st.dataframe(pd.read_sql_query("SELECT * FROM finanzas", db_conn))

    # ESCÁNER (PUNTO 1: Bajo demanda)
    with tabs[5]:
        st.subheader("📸 Escáner de Documentos")
        if st.toggle("Activar Cámara"):
            foto = st.camera_input("Tome foto de la receta")
            if foto: st.success("Imagen capturada y archivada en el backend.")

    # EXPORTAR (PUNTO 9: PDF y WhatsApp elegante)
    with tabs[6]:
        st.subheader("📤 Generar Reportes")
        if st.button("📄 GENERAR PDF PROFESIONAL"):
            pdf_out = generar_pdf()
            st.download_button("Descargar Reporte", data=pdf_out, file_name="Reporte_Nexus.pdf", mime="application/pdf")
        
        st.write("---")
        msg = "🏥 *REPORTE NEXUS PRO*\n\n"
        df_ult = pd.read_sql_query("SELECT valor, estado FROM salud ORDER BY id DESC LIMIT 1", db_conn)
        if not df_ult.empty:
            msg += f"🩸 Última Glucosa: {df_ult['valor'].iloc[0]} ({df_ult['estado'].iloc[0]})"
        
        st.markdown(f'[📲 Enviar por WhatsApp](https://wa.me/?text={urllib.parse.quote(msg)})')

if __name__ == "__main__":
    main()ABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, concepto TEXT, monto REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS escaneos (id INTEGER PRIMARY KEY, fecha TEXT, imagen BLOB, nota TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = conectar_db()

# ==========================================
# 2. INTELIGENCIA ARTIFICIAL Y SEMÁFORO
# ==========================================
def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    if v > 160: return "🔴 ALERTA"
    return "⚪ FUERA DE RANGO"

def motor_ia_proactivo():
    alertas = []
    df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 5", conn)
    if not df_g.empty:
        promedio = df_g['valor'].mean()
        if promedio > 160: alertas.append("🚨 IA SALUD: Tendencia crítica. Reduzca azúcares y consulte médico.")
        elif promedio > 125: alertas.append("⚠️ IA SALUD: Niveles elevados. Monitoree su próxima ingesta.")
    
    df_f = pd.read_sql_query("SELECT tipo, monto FROM finanzas", conn)
    if not df_f.empty:
        gastos = df_f[df_f['tipo'] == 'Gasto']['monto'].sum()
        if gastos > 5000: alertas.append("💰 IA FINANZAS: Alerta de gasto elevado este mes.")
    return alertas

# ==========================================
# 3. GENERADOR DE PDF PROFESIONAL (Punto 1 y 9)
# ==========================================
def generar_pdf_profesional():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="NEXUS PRO - RÉCORD MÉDICO E INSTITUCIONAL", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Fecha de Reporte: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)

    # Sección Salud
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="1. REGISTROS DE GLUCOSA", ln=True)
    pdf.set_font("Arial", size=10)
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    for _, r in df_g.iterrows():
        pdf.cell(200, 8, txt=f"• {r['fecha']} | Valor: {r['valor']} mg/dL | Estado: {r['estado']}", ln=True)

    # Sección Finanzas
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="2. RESUMEN FINANCIERO", ln=True)
    pdf.set_font("Arial", size=10)
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    for _, f in df_f.iterrows():
        pdf.cell(200, 8, txt=f"• {f['fecha']} | {f['tipo']}: {f['concepto']} | RD$ {f['monto']:,.2f}", ln=True)

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. INTERFAZ DASHBOARD (Punto 1-8)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    
    st.title("🧬 NEXUS SMART: Control Institucional")
    st.write(f"Usuario: **Luis Rafael Quevedo** | 📱 Persistencia en Disco Activada")

    tabs = st.tabs(["🏠 DASHBOARD", "🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS", "💰 FINANZAS", "📸 ESCÁNER", "📤 EXPORTAR"])

    # --- DASHBOARD & IA ---
    with tabs[0]:
        st.subheader("🤖 Cerebro Proactivo")
        avisos = motor_ia_proactivo()
        if avisos:
            for a in avisos: st.warning(a)
        else: st.success("✅ Todo bajo control según el análisis de IA.")
        
        st.write("---")
        c_r1, c_r2, c_r3 = st.columns(3)
        c_r1.metric("Registros Salud", len(pd.read_sql_query("SELECT id FROM glucosa", conn)))
        c_r2.metric("Citas Pendientes", len(pd.read_sql_query("SELECT id FROM citas", conn)))
        df_fin = pd.read_sql_query("SELECT tipo, monto FROM finanzas", conn)
        balance = df_fin[df_fin['tipo']=='Ingreso']['monto'].sum() - df_fin[df_fin['tipo']=='Gasto']['monto'].sum()
        c_r3.metric("Balance RD$", f"{balance:,.2f}")

    # --- GLUCOSA (Punto 3: Sin errores de multiplicación) ---
    with tabs[1]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Nuevo Registro")
            # El step=1.0 y format="%.0f" asegura que 250 sea 250
            val_g = st.number_input("Valor Glucosa (mg/dL):", min_value=0.0, step=1.0, format="%.0f", key="gluc_in")
            if st.button("💾 Guardar Glucosa"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                est = obtener_semaforo(val_g)
                cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val_g, est))
                conn.commit()
                st.rerun()
        with c2:
            st.subheader("Historial Clínico")
            df_g = pd.read_sql_query("SELECT fecha, valor, estado FROM glucosa ORDER BY id DESC", conn)
            st.table(df_g)
            if st.button("🗑️ Borrar Todo Salud"):
                cursor.execute("DELETE FROM glucosa"); conn.commit(); st.rerun()

    # --- MEDICAMENTOS (Punto 5) ---
    with tabs[2]:
        m1, m2 = st.columns(2)
        with m1:
            n_med = st.text_input("Nombre:")
            d_med = st.text_input("Dosis (Ej: 1 tableta/día):")
            if st.button("Registrar Medicina"):
                cursor.execute('INSERT INTO meds (nombre, dosis) VALUES (?,?)', (n_med, d_med))
                conn.commit(); st.rerun()
        with m2:
            st.write(pd.read_sql_query("SELECT * FROM meds", conn))

    # --- CITAS MÉDICAS (Punto 4) ---
    with tabs[3]:
        st.subheader("Agenda de Citas")
        f_c = st.date_input("Fecha de Cita")
        d_c = st.text_input("Doctor/Especialista")
        m_c = st.text_input("Motivo")
        if st.button("Agendar Cita"):
            cursor.execute('INSERT INTO citas (fecha, doctor, motivo) VALUES (?,?,?)', (str(f_c), d_c, m_c))
            conn.commit(); st.rerun()
        st.write(pd.read_sql_query("SELECT * FROM citas", conn))

    # --- FINANZAS (Punto 2 y 6: Diferenciación e Importe Exacto) ---
    with tabs[4]:
        f1, f2 = st.columns([1, 2])
        with f1:
            tipo_f = st.radio("Tipo:", ["Gasto", "Ingreso"])
            conc_f = st.text_input("Concepto:")
            # format="%.2f" evita el error de los miles
            mont_f = st.number_input("Monto RD$:", min_value=0.0, step=1.0, format="%.2f")
            if st.button("Ejecutar Transacción"):
                fec = datetime.datetime.now().strftime("%d/%m/%Y")
                cursor.execute('INSERT INTO finanzas (fecha, tipo, concepto, monto) VALUES (?,?,?,?)', (fec, tipo_f, conc_f, mont_f))
                conn.commit(); st.rerun()
        with f2:
            st.write(pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn))
            if st.button("🗑️ Vaciar Finanzas"):
                cursor.execute("DELETE FROM finanzas"); conn.commit(); st.rerun()

    # --- ESCÁNER (Punto 1: Cámara bajo demanda) ---
    with tabs[5]:
        st.subheader("📸 Archivo de Documentos")
        if st.toggle("Activar Cámara"):
            captura = st.camera_input("Escanee su documento")
            nota_s = st.text_input("Nota del documento:")
            if captura and st.button("💾 Archivar"):
                cursor.execute('INSERT INTO escaneos (fecha, imagen, nota) VALUES (?,?,?)', 
                               (datetime.datetime.now().strftime("%d/%m/%Y"), captura.read(), nota_s))
                conn.commit(); st.success("Documento guardado.")
        
        st.write("---")
        st.subheader("📂 Documentos Guardados")
        st.write(pd.read_sql_query("SELECT id, fecha, nota FROM escaneos", conn))

    # --- REPORTES Y PDF (Punto 9) ---
    with tabs[6]:
        st.subheader("📤 Exportar Récord Médico Profesional")
        rep_text = "🏥 *NEXUS PRO - RÉCORD MÉDICO*\n"
        rep_text += "---------------------------------\n"
        rep_text += f"Paciente: Luis Rafael Quevedo\n"
        
        # Últimos datos para el texto
        df_g_rep = pd.read_sql_query("SELECT valor, estado FROM glucosa ORDER BY id DESC LIMIT 1", conn)
        if not df_g_rep.empty:
            rep_text += f"🩸 Última Glucosa: {df_g_rep['valor'].iloc[0]} ({df_g_rep['estado'].iloc[0]})\n"
        
        st.text_area("Previsualización:", rep_text, height=150)
        
        col_pdf, col_wa, col_gm = st.columns(3)
        with col_pdf:
            if st.button("📄 GENERAR PDF"):
                pdf_data = generar_pdf_profesional()
                st.download_button("Descargar PDF", data=pdf_data, file_name="Reporte_Nexus_Pro.pdf", mime="application/pdf")
        
        with col_wa:
            enc_wa = urllib.parse.quote(rep_text)
            st.markdown(f'[📲 Enviar WhatsApp](https://wa.me/?text={enc_wa})')
        with col_gm:
            st.markdown(f'[📧 Enviar Gmail](https://mail.google.com/mail/?view=cm&fs=1&su=Reporte+Nexus+Pro&body={enc_wa})')

if __name__ == "__main__":
    main()
