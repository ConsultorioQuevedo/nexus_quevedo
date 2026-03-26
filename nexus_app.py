import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
from fpdf import FPDF

# --- CLASE ESPECIAL PARA EL PDF ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    
    /* ESTILO PARA BOTONES MANUALES */
    .btn-container {
        display: flex;
        gap: 10px;
        width: 100%;
        margin-bottom: 20px;
    }
    .btn-manual {
        flex: 1;
        height: 55px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        text-decoration: none !important;
        color: white !important;
        font-size: 14px;
        border: none;
        cursor: pointer;
    }
    .btn-pdf-manual { background-color: #1e3a8a; border: 1px solid #3b82f6; }
    .btn-wa-manual { background-color: #25D366; border: 1px solid #128C7E; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    _, col_b, _ = st.columns([1,2,1])
    with col_b:
        with st.form("login"):
            pwd = st.text_input("Contraseña:", type="password")
            if st.form_submit_button("ACCEDER"):
                if pwd == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Incorrecto")
    st.stop()

# --- 3. FUNCIONES CORE ---
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
    pdf.cell(190, 10, "REPORTE DE GLUCOSA", ln=True, align='C')
    pdf.ln(10)
    for _, row in df.iterrows():
        pdf.cell(0, 10, f"{row['fecha']} - {row['hora']} - {row['momento']}: {row['valor']} mg/dL", ln=True, border=1)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. FINANZAS (Simplificado para brevedad) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    st.metric("DISPONIBLE", f"RD$ {disponible:,.2f}")
    
    with st.form("f_fin", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
        monto = col2.number_input("MONTO RD$:", min_value=0.0)
        cat = st.text_input("CATEGORÍA").upper()
        det = st.text_input("DETALLE").upper()
        if st.form_submit_button("REGISTRAR"):
            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_str, mes_str, tipo, cat, det, m_real))
            db.commit(); st.rerun()

# --- 6. SALUD (SOLUCIÓN DEFINITIVA BOTONES) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Salud - Luis Rafael Quevedo")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        
        if not df_g.empty:
            u = df_g.iloc[0]
            texto_w = f"🩸 *REPORTE LUIS RAFAEL QUEVEDO*%0A📅 {f_str} ({u['hora']})%0A📍 Glucosa: {u['valor']} mg/dL"
            url_wa = f"https://wa.me/?text={texto_w}"
            
            # --- HTML PURO PARA FORZAR LADO A LADO ---
            st.markdown(f"""
                <div class="btn-container">
                    <a href="{url_wa}" target="_blank" class="btn-manual btn-wa-manual">
                        📲 WHATSAPP
                    </a>
                </div>
            """, unsafe_allow_html=True)
            
            # El botón de PDF lo dejamos solo debajo porque Streamlit no permite disparar la descarga desde un link HTML común por seguridad de archivos
            pdf_data = generar_pdf_salud(df_g)
            st.download_button(
                label="📥 DESCARGAR REPORTE PDF", 
                data=pdf_data, 
                file_name=f"Reporte_{f_str}.pdf", 
                mime="application/pdf",
                use_container_width=True
            )
            
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark"), use_container_width=True)

        with st.form("f_gluc", clear_on_submit=True):
            v = st.number_input("Valor mg/dL:", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR LECTURA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()

# --- 7. BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    nota = st.text_area("Nueva nota:")
    if st.button("GUARDAR"):
        with open("nexus_notas.txt", "a") as f: f.write(f"[{f_str}]: {nota}\n\n")
        st.success("Nota guardada")

# --- 8. CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes")
    st.write("Configuración general de la cuenta de Luis Rafael Quevedo.")
