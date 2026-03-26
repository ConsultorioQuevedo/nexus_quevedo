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
    
    /* --- TRUCO MAESTRO: FORZAR COLUMNAS HORIZONTALES EN MÓVIL --- */
    [data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 auto !important;
        min-width: 0px !important;
    }

    /* Botones Estilizados */
    div.stButton > button, div.stDownloadButton > button { 
        background-color: #1f2937; color: white; border: 1px solid #30363d; 
        border-radius: 8px; width: 100%; font-weight: bold; height: 55px; transition: 0.3s;
        font-size: 12px; /* Un poco más pequeño para que quepa bien en móvil */
    }
    
    /* Color específico para PDF */
    div.stDownloadButton > button { background-color: #1e3a8a !important; border: 1px solid #3b82f6 !important; }
    div.stDownloadButton > button:hover { background-color: #2563eb !important; transform: scale(1.02); }

    /* Botón WhatsApp Link */
    a[data-testid="stLinkButton"] {
        background-color: #25D366 !important; color: white !important; 
        height: 55px !important; border-radius: 8px !important; 
        display: flex !important; align-items: center; justify-content: center;
        font-weight: bold !important; text-decoration: none !important; border: 1px solid #128C7E !important;
        transition: 0.3s; font-size: 12px;
    }
    a[data-testid="stLinkButton"]:hover { background-color: #128C7E !important; transform: scale(1.02); }
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
    pdf.cell(190, 10, "REPORTE HISTORICO DE GLUCOSA", ln=True, align='C')
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
        pdf.cell(40, 9, f" {row['valor']} mg/dL", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1', errors='replace')

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# Presupuesto
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 0.0

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0.0
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1 style='color:#2ecc71;'>RD$ {disponible:,.2f}</h1></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='balance-box'><h3>GASTOS MES</h3><h1 style='color:#e74c3c;'>RD$ {gastos_mes:,.2f}</h1></div>", unsafe_allow_html=True)
    
    with st.form("f_fin", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
        f_mov = col2.date_input("FECHA", value=f_obj)
        cat, det = st.text_input("CATEGORÍA").upper(), st.text_input("DETALLE").upper()
        monto = st.number_input("MONTO RD$:", min_value=0.0)
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_mov.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, m_real))
            db.commit(); st.rerun()
    
    if not df_f.empty:
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)

# --- 6. SALUD (BOTONES REPARADOS AQUÍ) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Salud - Luis Rafael Quevedo")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        
        if not df_g.empty:
            # Esta fila ahora se mantendrá horizontal en el celular gracias al CSS de arriba
            col_pdf, col_wa = st.columns(2)
            
            with col_pdf:
                pdf_data = generar_pdf_salud(df_g)
                st.download_button(
                    label="📥 GENERAR PDF", 
                    data=pdf_data, 
                    file_name=f"Reporte_Quevedo_{f_str}.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_wa:
                u = df_g.iloc[0]
                texto_w = f"🩸 *REPORTE LUIS RAFAEL QUEVEDO*\n📅 {f_str} ({u['hora']})\n📍 Glucosa: {u['valor']} mg/dL"
                st.link_button(
                    "📲 WHATSAPP", 
                    f"https://wa.me/?text={urllib.parse.quote(texto_w)}",
                    use_container_width=True
                )
            
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, title="TENDENCIA", template="plotly_dark"), use_container_width=True)
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']], use_container_width=True)

        with st.form("f_gluc", clear_on_submit=True):
            col_g1, col_g2 = st.columns(2)
            v = col_g1.number_input("Valor mg/dL:", min_value=0)
            m = col_g2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR LECTURA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()

    with t2:
        st.markdown("### 💊 Control de Medicamentos")
        with st.form("f_med", clear_on_submit=True):
            n, d, h = st.text_input("MEDICINA").upper(), st.text_input("DOSIS").upper(), st.text_input("HORARIO").upper()
            if st.form_submit_button("AGREGAR MEDICAMENTO"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", db), use_container_width=True)

    with t3:
        st.markdown("### 📅 Próximas Citas")
        with st.form("f_citas", clear_on_submit=True):
            doc, fec, mot = st.text_input("DOCTOR").upper(), st.date_input("FECHA"), st.text_input("MOTIVO").upper()
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot)); db.commit(); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db), use_container_width=True)

# --- 7. BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora de Notas")
    nota = st.text_area("Nueva nota personalizada:", height=150)
    if st.button("GUARDAR NOTA"):
        if nota.strip():
            with open("nexus_notas.txt", "a", encoding="utf-8") as f: f.write(f"[{f_str} {h_str}]: {nota}\n\n")
            st.success("Nota guardada.")
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f: st.text_area("Historial:", f.read(), height=400)
    except: st.info("Sin notas.")

# --- 8. CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Configuración")
    new_p = st.number_input("Presupuesto Mensual (RD$):", min_value=0.0, value=float(presupuesto_mensual))
    if st.button("GUARDAR AJUSTES"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (new_p,))
        db.commit(); st.success("Guardado"); st.rerun()
