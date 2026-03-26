import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import os
from fpdf import FPDF

# --- 1. CLASE PARA REPORTES PDF PERSONALIZADOS ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(120)
        # Su nombre como autor en el pie de página
        self.cell(0, 10, 'Luis Rafael Quevedo - Nexus System', 0, 0, 'C')

# --- 2. CONFIGURACIÓN VISUAL Y ESTILO PROFESIONAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117; }
    
    /* DISEÑO DE TARJETAS DE MÉTRICAS */
    .metric-card { 
        background-color: #161b22; border-radius: 12px; border: 1px solid #30363d; 
        padding: 20px; text-align: center; margin-bottom: 10px;
    }
    .neon-verde { color: #40E0D0; font-weight: 800; font-size: 2.2rem; margin: 0; }
    .neon-rojo { color: #FF7F50; font-weight: 800; font-size: 2.2rem; margin: 0; }
    .neon-azul { color: #58a6ff; font-weight: 800; font-size: 2.2rem; margin: 0; }
    h4 { color: #8b949e; margin-bottom: 10px; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; }

    /* FORMULARIOS Y BOTONES */
    div[data-testid="stForm"] { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 25px; }
    .stButton > button { border-radius: 10px; font-weight: 700; height: 48px; width: 100%; transition: 0.3s; }
    .stButton > button:hover { border: 1px solid #40E0D0; transform: scale(1.01); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE TIEMPO Y BASE DE DATOS ---
def obtener_datos_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y")

def iniciar_db():
    conn = sqlite3.connect("nexus_final_quevedo.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

db = iniciar_db()
f_s, h_s, mes_s = obtener_datos_rd()

# --- 4. SEGURIDAD DE ACCESO (FIX: MISSING SUBMIT BUTTON) ---
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align:center; color:white; margin-top:100px;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        clave = st.text_input("Clave de Acceso:", type="password")
        if st.form_submit_button("INGRESAR AL SISTEMA"):
            if clave == "admin123":
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Acceso Denegado")
    st.stop()

# --- 5. PANEL DE NAVEGACIÓN ---
with st.sidebar:
    st.title("🌐 CONTROL PRO")
    menu = st.radio("MÓDULOS", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    st.markdown("---")
    if st.button("CERRAR SESIÓN"):
        del st.session_state["auth"]
        st.rerun()

# --- 6. MÓDULO: FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Presupuesto y Finanzas")
    
    # Meta de presupuesto
    r_meta = db.execute("SELECT valor FROM config WHERE param='meta'").fetchone()
    meta_val = r_meta[0] if r_meta else 0.0
    
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    total_cap = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_s)]['monto'].sum()) if not df_f.empty else 0.0

    # Fila de métricas organizada en columnas
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><h4>Capital Total</h4><p class="neon-verde">RD$ {total_cap:,.2f}</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><h4>Gastos {mes_s}</h4><p class="neon-rojo">RD$ {gastos_mes:,.2f}</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><h4>Presupuesto Meta</h4><p class="neon-azul">RD$ {meta_val:,.2f}</p></div>', unsafe_allow_html=True)

    col_conf, col_reg = st.columns([1, 1.5])
    with col_conf:
        with st.expander("⚙️ AJUSTAR META"):
            n_meta = st.number_input("Nueva Meta:", value=meta_val)
            if st.button("ACTUALIZAR"):
                db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('meta', ?)", (n_meta,))
                db.commit(); st.rerun()
                
    with col_reg:
        with st.form("form_finanzas"):
            st.subheader("Registrar Movimiento")
            tipo = st.selectbox("Tipo", ["GASTO", "INGRESO"])
            det = st.text_input("Detalle").upper()
            mon = st.number_input("Monto RD$", min_value=0.0)
            if st.form_submit_button("GUARDAR TRANSACCIÓN"):
                db.execute("INSERT INTO finanzas (fecha, mes, tipo, detalle, monto) VALUES (?,?,?,?,?)", 
                           (f_s, mes_s, tipo, det, -mon if tipo=="GASTO" else mon))
                db.commit(); st.rerun()

    if not df_f.empty:
        st.subheader("Historial Reciente")
        st.dataframe(df_f[["fecha", "tipo", "detalle", "monto"]].head(15), use_container_width=True)

# --- 7. MÓDULO: SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS MÉDICAS"])
    
    with t1:
        dfg = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not dfg.empty:
            st.plotly_chart(px.line(dfg.iloc[::-1], x='hora', y='valor', title="Tendencia de Glucosa", template="plotly_dark"), use_container_width=True)
        with st.form("f_glucosa"):
            v = st.number_input("Valor mg/dL:", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Almuerzo", "Cena", "Noche"])
            if st.form_submit_button("REGISTRAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_s, h_s, m, v))
                db.commit(); st.rerun()

    with t2:
        with st.form("f_med"):
            nom, dos, hor = st.text_input("Medicamento"), st.text_input("Dosis"), st.text_input("Horario")
            if st.form_submit_button("AÑADIR MEDICAMENTO"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (nom.upper(), dos, hor))
                db.commit(); st.rerun()
        dfm = pd.read_sql_query("SELECT * FROM medicamentos", db)
        st.table(dfm[["nombre", "dosis", "horario"]])

    with t3:
        with st.form("f_citas"):
            doc, fec, mot = st.text_input("Doctor"), st.date_input("Fecha"), st.text_input("Motivo")
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc.upper(), str(fec), mot.upper()))
                db.commit(); st.rerun()
        dfc = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        st.dataframe(dfc, use_container_width=True)

# --- 8. MÓDULO: BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora Personal")
    nueva_nota = st.text_area("Escribir nota:", height=150)
    if st.button("💾 GUARDAR EN BITÁCORA"):
        if nueva_nota.strip():
            with open("bitacora_nexus.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_s} {h_s}]: {nueva_nota.strip()}\n\n")
            st.success("Nota guardada correctamente."); st.rerun()

    st.markdown("---")
    if os.path.exists("bitacora_nexus.txt"):
        with open("bitacora_nexus.txt", "r", encoding="utf-8") as f:
            contenido = f.read()
    else: contenido = ""

    if contenido:
        c_pdf, c_borrar, _ = st.columns([1, 1, 3])
        with c_pdf:
            reporte = PDF()
            reporte.add_page()
            reporte.set_font("Arial", 'B', 16); reporte.cell(190, 10, "NOTAS PERSONALES - NEXUS", ln=True, align='C'); reporte.ln(10)
            reporte.set_font("Arial", '', 12); reporte.multi_cell(190, 8, contenido)
            st.download_button("📄 EXPORTAR PDF", reporte.output(dest='S').encode('latin-1', errors='replace'), "Bitacora_Quevedo.pdf")
        with c_borrar:
            if st.button("🗑️ BORRAR TODO"):
                if os.path.exists("bitacora_nexus.txt"): os.remove("bitacora_nexus.txt")
                st.rerun()
        st.text_area("Historial de Notas:", contenido, height=350)
