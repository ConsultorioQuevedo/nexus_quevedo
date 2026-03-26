import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
from fpdf import FPDF

# --- CLASE ESPECIAL PARA EL PDF CON SU NOMBRE AL PIE ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        # Nombre completo en el pie de página según su instrucción
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- 1. CONFIGURACIÓN VISUAL (ESTILO NEXUS DARK) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 45px; }
    .btn-pdf > div > button { background-color: #1e3a8a !important; color: white !important; border: 1px solid #3b82f6 !important; height: 50px; }
    .btn-whatsapp-rapido > a {
        display: inline-block; width: 100%; text-align: center; background-color: #25D366; color: white !important;
        padding: 12px; border-radius: 10px; text-decoration: none; font-weight: bold; margin-bottom: 20px; border: 1px solid #128C7E;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    _, col_b, _ = st.columns([1,2,1])
    with col_b:
        with st.form("login"):
            pwd = st.text_input("Contraseña Maestra:", type="password")
            if st.form_submit_button("ACCEDER"):
                if pwd == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Credenciales Incorrectas")
    st.stop()

# --- 3. FUNCIONES CORE Y BASE DE DATOS ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_pro_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "REPORTE HISTÓRICO DE GLUCOSA", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 8, "PACIENTE: LUIS RAFAEL QUEVEDO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 10, " FECHA", 1, 0, 'C', True)
    pdf.cell(40, 10, " HORA", 1, 0, 'C', True)
    pdf.cell(70, 10, " MOMENTO", 1, 0, 'C', True)
    pdf.cell(40, 10, " VALOR", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        pdf.cell(40, 9, f" {row['fecha']}", 1)
        pdf.cell(40, 9, f" {row['hora']}", 1)
        pdf.cell(70, 9, f" {row['momento']}", 1)
        if row['valor'] > 140:
            pdf.set_text_color(200, 0, 0); pdf.set_font("Arial", 'B', 10)
            pdf.cell(40, 9, f" {row['valor']} mg/dL *", 1, 1, 'C')
            pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
        else:
            pdf.cell(40, 9, f" {row['valor']} mg/dL", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    with st.form("f_fin", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("TIPO", ["GASTO", "INGRESO"])
        f_mov = c2.date_input("FECHA", value=f_obj)
        cat = st.text_input("CATEGORÍA").upper()
        det = st.text_input("DETALLE").upper()
        monto = st.number_input("MONTO RD$:", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_mov.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, m_real))
            db.commit(); st.rerun()
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    if not df_f.empty:
        st.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1 style='color:#2ecc71;'>RD$ {df_f['monto'].sum():,.2f}</h1></div>", unsafe_allow_html=True)
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)

# --- 6. SALUD (RESTAURADO CON TODAS LAS PESTAÑAS) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Salud - Luis Rafael Quevedo")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            c_a, c_b = st.columns(2)
            with c_a:
                pdf_data = generar_pdf_salud(df_g)
                st.markdown("<div class='btn-pdf'>", unsafe_allow_html=True)
                st.download_button(label="📥 DESCARGAR REPORTE (PDF)", data=pdf_data, file_name=f"Reporte_Quevedo_{f_str}.pdf", mime="application/pdf")
                st.markdown("</div>", unsafe_allow_html=True)
            with c_b:
                u = df_g.iloc[0]
                texto_w = f"🩸 *REPORTE LUIS RAFAEL QUEVEDO*\n📅 {f_str}\n📍 Última: {u['valor']} mg/dL"
                st.markdown(f"<div class='btn-whatsapp-rapido'><a href='https://wa.me/?text={urllib.parse.quote(texto_w)}' target='_blank'>AVISO RÁPIDO WHATSAPP</a></div>", unsafe_allow_html=True)
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True), use_container_width=True)
            st.markdown("### 📊 Historial Completo")
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']], use_container_width=True)

        with st.form("f_gluc", clear_on_submit=True):
            c1, c2 = st.columns(2)
            v, m = c1.number_input("Valor:", min_value=0), c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()

    with t2:
        st.markdown("### 💊 Registro de Medicamentos")
        with st.form("f_med", clear_on_submit=True):
            n, d, h = st.text_input("MEDICINA").upper(), st.text_input("DOSIS").upper(), st.text_input("HORARIO/FRECUENCIA").upper()
            if st.form_submit_button("AÑADIR MEDICINA"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        st.dataframe(df_m[['nombre', 'dosis', 'horario']], use_container_width=True)

    with t3:
        st.markdown("### 📅 Citas Médicas")
        with st.form("f_citas", clear_on_submit=True):
            doc, fec, mot = st.text_input("DOCTOR").upper(), st.date_input("FECHA"), st.text_input("MOTIVO").upper()
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot)); db.commit(); st.rerun()
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        st.dataframe(df_c[['doctor', 'fecha', 'motivo']], use_container_width=True)

# --- 7. BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    nota = st.text_area("Nota:", height=150)
    if st.button("GUARDAR NOTA"):
        with open("nexus_notas.txt", "a", encoding="utf-8") as f: f.write(f"[{f_str} {h_str}]: {nota}\n\n")
        st.success("Guardado.")
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f: st.text_area("Historial:", f.read(), height=400)
    except: st.info("Sin notas.")

# --- 8. CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes")
    st.write("Sistema Nexus V3 - Luis Rafael Quevedo")
