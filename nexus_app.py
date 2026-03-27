import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
import os
from fpdf import FPDF

# --- CONFIGURACIÓN DE TIEMPO RD ---
def obtener_fecha_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date(), ahora

# --- BASE DE DATOS COMPLETA ---
def conectar_db():
    conn = sqlite3.connect("control_quevedo.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS registro_medico (id INTEGER PRIMARY KEY, fecha TEXT, medicamento TEXT, hora_confirmada TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

# --- DISEÑO INTERFAZ NEXUS PRO ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🌐")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stMetric { background-color: #1c2128; padding: 20px; border-radius: 12px; border: 1px solid #30363d; }
    .stForm { background-color: #1c2128; border-radius: 15px; border: 1px solid #30363d; padding: 25px; }
    .alerta-card { padding: 15px; border-radius: 10px; background-color: #1c2128; border-left: 5px solid #f1e05a; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)
def interpretar_salud(valor, momento):
    if "Ayunas" in momento:
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "#1b5e20"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "#fbc02d"
        else: return "ROJO", "ALTO", "#b71c1c"
    else:
        if valor < 140: return "VERDE", "NORMAL", "#1b5e20"
        elif 140 <= valor <= 199: return "AMARILLO", "ELEVADO", "#fbc02d"
        else: return "ROJO", "ALTO (REVISAR)", "#b71c1c"

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NEXUS PRO - REPORTE MÉDICO QUEVEDO', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Historial de Glucosa", ln=True, align='C')
    pdf.ln(5)
    for i, r in df.iterrows():
        pdf.cell(0, 10, f"{r['fecha']} - {r['momento']}: {r['valor']} mg/dL", ln=True, border=1)
    return pdf.output(dest='S').encode('latin-1')
  if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🌐 NEXUS SYSTEM</h1>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,1.5,1])
    with col:
        with st.form("login"):
            pwd = st.text_input("Clave Maestra:", type="password")
            if st.form_submit_button("INGRESAR"):
                if pwd == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("Acceso Denegado")
    st.stop()

db = conectar_db()
f_txt, h_txt, m_txt, f_obj, ahora_obj = obtener_fecha_rd()
hora_24 = ahora_obj.hour

with st.sidebar:
    st.title("🌐 CONTROL QUEVEDO")
    st.write(f"📅 {f_txt} | ⏰ {h_txt}")
    opcion = st.radio("SECCIONES", ["🏠 INICIO", "💰 FINANZAS", "🩺 SALUD", "💊 MEDICINAS", "📅 CITAS", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("SALIR"):
        del st.session_state["password_correct"]; st.rerun()
# --- 6. PANTALLA: INICIO Y ALERTAS MÉDICAS ---
if opcion == "🏠 INICIO":
    st.title(f"Bienvenido, Sr. Quevedo")
    st.info(f"Estado del Sistema: Óptimo | {f_txt}")

    plan_medico = [
        {"med": "Jarinu Max", "hora": "07:00 AM", "rango": [6, 9]},
        {"med": "Aspirin / Pregabalina", "hora": "08:00 AM", "rango": [7, 10]},
        {"med": "Pregabalina (Tarde)", "hora": "06:00 PM", "rango": [17, 20]},
        {"med": "Insulina", "hora": "08:00 PM", "rango": [19, 22]},
        {"med": "Triglicer / Libal", "hora": "09:00 PM", "rango": [20, 23]}
    ]

    st.markdown("### 🔔 Alertas de Salud")
    alertas_hoy = 0
    for item in plan_medico:
        if item["rango"][0] <= hora_24 <= item["rango"][1]:
            alertas_hoy += 1
            st.warning(f"💊 **HORA DE MEDICINA:** {item['med']} ({item['hora']})")
            if st.button(f"CONFIRMAR TOMA: {item['med']}", key=f"btn_{item['med']}"):
                db.execute("INSERT INTO registro_medico (fecha, medicamento, hora_confirmada) VALUES (?,?,?)", (f_txt, item['med'], h_txt))
                db.commit(); st.success(f"Toma registrada: {h_txt}"); st.rerun()

    if alertas_hoy == 0: st.success("✅ No tiene medicamentos pendientes en este horario.")

    st.markdown("---")
    st.markdown("#### 📋 Historial Reciente de Tomas")
    reg_rec = db.execute("SELECT medicamento, hora_confirmada FROM registro_medico ORDER BY id DESC LIMIT 5").fetchall()
    if reg_rec: st.table(pd.DataFrame(reg_rec, columns=["Medicina", "Hora Confirmada"]))

# --- 7. PANTALLA: FINANZAS (CONTROL QUEVEDO) ---
elif opcion == "💰 FINANZAS":
    st.title("💰 Control Quevedo - Gestión Financiera")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    t_in = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum() if not df_f.empty else 0
    t_out = abs(df_f[df_f['tipo'] == 'GASTO']['monto'].sum()) if not df_f.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("DISPONIBLE", f"RD$ {t_in - t_out:,.2f}")
    c2.metric("GASTOS", f"RD$ {t_out:,.2f}", delta_color="inverse")
    c3.metric("INGRESOS", f"RD$ {t_in:,.2f}")

    with st.form("f_fin", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            t = st.selectbox("Tipo", ["GASTO", "INGRESO"])
            m = st.number_input("Monto RD$", min_value=0.0)
        with col2:
            c = st.text_input("Categoría").upper()
            d = st.text_input("Detalle").upper()
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            val = -m if t == "GASTO" else m
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_txt, m_txt, t, c, d, val))
            db.commit(); st.rerun()
    st.dataframe(df_f, use_container_width=True)
  # --- 8. PANTALLA: SALUD (GLUCOSA) ---
elif opcion == "🩺 SALUD":
    st.title("🩺 Monitoreo de Salud")
    with st.form("f_salud", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1: v = st.number_input("Nivel Glucosa (mg/dL)", min_value=0)
        with col2: m = st.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de Dormir"])
        if st.form_submit_button("GUARDAR REGISTRO"):
            db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_txt, h_txt, m, v))
            db.commit(); st.rerun()

    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
    if not df_g.empty:
        st.plotly_chart(px.line(df_g, x='fecha', y='valor', color='momento', title="Tendencia de Glucosa", template="plotly_dark"))
        if st.button("📄 GENERAR REPORTE PDF"):
            pdf_bytes = generar_pdf(df_g)
            st.download_button("Descargar Reporte Médico", pdf_bytes, f"reporte_quevedo_{f_txt}.pdf")
        st.table(df_g[['fecha', 'hora', 'momento', 'valor']].head(10))

# --- 9. PANTALLA: MEDICINAS (BOTIQUÍN) ---
elif opcion == "💊 MEDICINAS":
    st.title("💊 Catálogo de Medicinas")
    with st.form("f_med"):
        n = st.text_input("Medicina").upper()
        d = st.text_input("Dosis").upper()
        h = st.text_input("Frecuencia").upper()
        if st.form_submit_button("AÑADIR AL BOTIQUÍN"):
            db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
            db.commit(); st.rerun()
    
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
    for i, r in df_m.iterrows():
        st.info(f"**{r['nombre']}**: {r['dosis']} - {r['horario']}")
# --- 10. PANTALLA: CITAS ---
elif opcion == "📅 CITAS":
    st.title("📅 Agenda de Citas")
    with st.form("f_cita"):
        doc = st.text_input("Doctor/Especialidad").upper()
        fec = st.date_input("Fecha")
        mot = st.text_area("Motivo").upper()
        if st.form_submit_button("AGENDAR"):
            db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot))
            db.commit(); st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db))

# --- 11. PANTALLA: BITÁCORA ---
elif opcion == "📝 BITÁCORA":
    st.title("📝 Notas Personales")
    nota = st.text_area("Escriba su nota aquí:", height=200)
    if st.button("GUARDAR EN ARCHIVO"):
        with open("notas_quevedo.txt", "a", encoding="utf-8") as f:
            f.write(f"--- {f_txt} {h_txt} ---\n{nota}\n\n")
        st.success("Nota guardada físicamente.")

# --- 12. PANTALLA: CONFIGURACIÓN ---
elif opcion == "⚙️ CONFIG":
    st.title("⚙️ Sistema NEXUS PRO")
    st.write(f"Propiedad de: Luis Rafael Quevedo")
    st.markdown("---")
    if st.button("Limpiar Datos de Glucosa"):
        db.execute("DELETE FROM glucosa"); db.commit(); st.rerun()
    if st.button("Limpiar Datos de Finanzas"):
        db.execute("DELETE FROM finanzas"); db.commit(); st.rerun()
    st.caption("Versión 4.5 | Seguridad SSL | Base de Datos SQLite")
