import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
from fpdf import FPDF

# --- CLASE PARA GENERAR EL PDF ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo - Nexus Pro', 0, 0, 'C')

# --- CONFIGURACIÓN VISUAL (CSS AGRESIVO) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117 !important; }

    /* Tarjetas Modernas Redondeadas */
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22 !important; 
        border-radius: 25px !important; 
        border: 1px solid #30363d !important; 
        padding: 25px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important;
        margin-bottom: 20px !important;
    }
    
    .balance-box h3 { 
        color: #8b949e !important; 
        font-size: 13px !important; 
        text-transform: uppercase !important; 
        letter-spacing: 2px !important;
        margin-bottom: 5px !important;
    }

    /* Botones Estilo Premium */
    div.stButton > button, div.stDownloadButton > button { 
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%) !important;
        color: #f0f6fc !important; 
        border: 1px solid #30363d !important; 
        border-radius: 12px !important; 
        font-weight: 700 !important; 
        height: 45px !important; 
        width: 100% !important;
        transition: 0.2s all ease !important;
    }
    div.stButton > button:hover { border-color: #58a6ff !important; transform: translateY(-2px) !important; }
    
    /* Botones de Borrado (Rojos) */
    .stButton > button[key^="del_"] {
        background: rgba(255, 75, 75, 0.1) !important;
        color: #ff4b4b !important;
        border: 1px solid rgba(255, 75, 75, 0.2) !important;
    }

    /* Colores Neón */
    .neon-verde { color: #40E0D0 !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    .neon-rojo { color: #FF7F50 !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE DATOS ---
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
    conn.commit()
    return conn

def generar_pdf(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(190, 10, "HISTORICO DE SALUD", ln=True, align='C'); pdf.ln(10)
    pdf.set_fill_color(30, 30, 30); pdf.set_text_color(255, 255, 255)
    for col in ["FECHA", "HORA", "MOMENTO", "VALOR"]: pdf.cell(47, 10, col, 1, 0, 'C', True)
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, r in df.iterrows():
        pdf.cell(47, 9, str(r['fecha']), 1); pdf.cell(47, 9, str(r['hora']), 1)
        pdf.cell(47, 9, str(r['momento']), 1); pdf.cell(47, 9, f"{r['valor']} mg/dL", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1', errors='replace')

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- ACCESO ---
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color:white;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1,1.2,1])
    with col_login:
        with st.form("login"):
            clave = st.text_input("Contraseña Maestra:", type="password")
            if st.form_submit_button("ENTRAR AL SISTEMA"):
                if clave == "admin123": st.session_state["autenticado"] = True; st.rerun()
                else: st.error("❌")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🌐 CONTROL")
    opcion = st.radio("", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    if st.button("CERRAR SESIÓN"): del st.session_state["autenticado"]; st.rerun()

# --- MÓDULO: FINANZAS ---
if opcion == "💰 FINANZAS":
    st.title("💰 Gestión de Capital")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    capital = df_f['monto'].sum() if not df_f.empty else 0.0
    
    st.markdown(f"<div class='balance-box'><h3>Capital Disponible</h3><div class='neon-verde'>RD$ {capital:,.2f}</div></div>", unsafe_allow_html=True)
    
    with st.form("f_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo de Movimiento", ["GASTO", "INGRESO"])
        fec_f = col2.date_input("Fecha", f_obj)
        cat = st.text_input("Categoría (Casa, Comida, etc.)").upper()
        det = st.text_input("Detalle").upper()
        mon = st.number_input("Monto (RD$)", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            valor = -mon if tipo == "GASTO" else mon
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (fec_f.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, valor))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.write("### Historial (Borre para corregir)")
        for _, r in df_f.iterrows():
            c_info, c_borrar = st.columns([9,1])
            color = "#FF7F50" if r['monto'] < 0 else "#40E0D0"
            c_info.markdown(f"**{r['fecha']}** | {r['detalle']} | <span style='color:{color}; font-weight:bold;'>RD$ {r['monto']:,.2f}</span>", unsafe_allow_html=True)
            if c_borrar.button("🗑️", key=f"del_f_{r['id']}"):
                db.execute("DELETE FROM finanzas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- MÓDULO: SALUD ---
elif opcion == "🩺 SALUD":
    st.title("🩺 Panel de Salud")
    tab1, tab2, tab3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with tab1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark").update_traces(line_color='#40E0D0'), use_container_width=True)
            c_pdf, c_wa = st.columns(2)
            c_pdf.download_button("📥 DESCARGAR PDF", generar_pdf(df_g), "Salud_Quevedo.pdf")
            u = df_g.iloc[0]
            txt_wa = f"Reporte: {u['valor']} mg/dL ({u['momento']})"
            c_wa.link_button("📲 WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(txt_wa)}")
            
            for _, r in df_g.head(10).iterrows():
                c_i, c_b = st.columns([9,1])
                c_i.success(f"📅 {r['fecha']} | {r['momento']}: {r['valor']} mg/dL")
                if c_b.button("🗑️", key=f"del_g_{r['id']}"):
                    db.execute("DELETE FROM glucosa WHERE id=?", (r['id'],)); db.commit(); st.rerun()

        with st.form("f_glu"):
            val = st.number_input("Valor:", min_value=0)
            mom = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR GLUCOSA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, mom, val)); db.commit(); st.rerun()

    with tab2:
        st.write("### Listado de Medicamentos")
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows():
            c_i, c_b = st.columns([8, 2])
            c_i.warning(f"💊 **{r['nombre']}** - {r['dosis']} ({r['horario']})")
            if c_b.button("BORRAR 💊", key=f"del_m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        
        with st.form("f_med"):
            n, d, h = st.text_input("Medicamento"), st.text_input("Dosis"), st.text_input("Horario")
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d, h)); db.commit(); st.rerun()

    with tab3:
        st.write("### Mis Citas Médicas")
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        for _, r in df_c.iterrows():
            c_i, c_b = st.columns([8, 2])
            c_i.error(f"📅 {r['fecha']} | Dr. {r['doctor']} | {r['motivo']}")
            if c_b.button("QUITAR 📅", key=f"del_c_{r['id']}"):
                db.execute("DELETE FROM citas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

        with st.form("f_cita"):
            doc, fec, mot = st.text_input("Doctor"), st.date_input("Fecha"), st.text_input("Motivo")
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc.upper(), str(fec), mot.upper())); db.commit(); st.rerun()

# --- MÓDULO: BITÁCORA ---
elif opcion == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    nota = st.text_area("Escribir nota del día:", height=200)
    if st.button("GUARDAR EN MEMORIA"):
        if nota:
            with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                f.write(f"--- {f_str} {h_str} ---\n{nota}\n\n")
            st.success("Guardado.")
    
    st.markdown("---")
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f:
            st.text_area("Historial de Notas:", f.read(), height=300)
    except: st.info("No hay notas guardadas.")
