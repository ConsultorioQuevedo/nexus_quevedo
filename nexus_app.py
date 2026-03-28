import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
from fpdf import FPDF
import urllib.parse

# ==========================================
# 1. CONFIGURACIÓN DE NÚCLEO Y ESTILO
# ==========================================
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", initial_sidebar_state="expanded")

# CSS Personalizado para una apariencia Moderna y Profesional
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #00d4ff; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #00d4ff; color: black; border: none; }
    .card { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; margin-bottom: 15px; }
    .status-normal { border-left: 8px solid #2ea043; }
    .status-warning { border-left: 8px solid #d29922; }
    .status-danger { border-left: 8px solid #f85149; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE APOYO (RELOJ Y DATOS)
# ==========================================
def get_rd_time():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora

def init_db():
    # Unificamos a una sola base de datos maestra para evitar errores de visualización
    conn = sqlite3.connect("control_quevedo_maestro.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, nota TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS registro_medico (id INTEGER PRIMARY KEY, fecha TEXT, medicamento TEXT, hora_confirmada TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

conn = init_db()
f_txt, h_txt, ahora_obj = get_rd_time()

# ==========================================
# 3. SEGURIDAD DE ACCESO
# ==========================================
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #58a6ff;'>🌐 NEXUS QUEVEDO SYSTEM</h1>", unsafe_allow_html=True)
    with st.container():
        _, col_login, _ = st.columns([1, 1, 1])
        with col_login:
            pwd = st.text_input("Clave de Seguridad:", type="password")
            if st.button("DESBLOQUEAR ACCESO"):
                if pwd == "1628":
                    st.session_state["auth"] = True
                    st.rerun()
                else: st.error("Acceso Denegado")
    st.stop()

# ==========================================
# 4. MENÚ LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown(f"<h2 style='color:#58a6ff;'>🤵 Sr. Quevedo</h2>", unsafe_allow_html=True)
    st.write(f"📅 {f_txt} | ⏰ {h_txt}")
    st.markdown("---")
    menu = st.radio("NAVEGACIÓN:", ["🏠 DASHBOARD", "🩺 GLUCOSA", "💰 FINANZAS", "💊 BOTIQUÍN", "🗓️ AGENDA", "📝 BITÁCORA"])
    st.markdown("---")
    if st.button("🔴 CERRAR SESIÓN"):
        del st.session_state["auth"]
        st.rerun()

# ==========================================
# 5. MÓDULO 🏠 DASHBOARD (EL CEREBRO)
# ==========================================
if menu == "🏠 DASHBOARD":
    st.title(f"🛡️ Centro de Mando - Luis Rafael Quevedo")
    
    # --- FILA 1: MÉTRICAS RESUMEN ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Data para métricas
    try:
        last_glucosa = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1", conn).valor[0]
        color_g = "normal" if last_glucosa < 140 else "inverse"
    except: last_glucosa, color_g = 0, "normal"
    
    try:
        df_fin = pd.read_sql_query("SELECT tipo, monto FROM finanzas", conn)
        balance = df_fin[df_fin['tipo']=='INGRESO'].monto.sum() - df_fin[df_fin['tipo']=='GASTO'].monto.sum()
    except: balance = 0

    col1.metric("Última Glucosa", f"{last_glucosa} mg/dL", delta_color=color_g)
    col2.metric("Balance Disponible", f"${balance:,.2f}")
    col3.metric("Medicinas Hoy", "Pendientes")
    col4.metric("Próxima Cita", "Ver Agenda")

    st.markdown("---")

    # --- FILA 2: ALERTAS DE MEDICAMENTOS ---
    st.subheader("💊 Recordatorios Activos")
    df_meds = pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", conn)
    tomas_hoy = pd.read_sql_query(f"SELECT medicamento FROM registro_medico WHERE fecha = '{f_txt}'", conn).medicamento.tolist()
    
    if not df_meds.empty:
        for _, m in df_meds.iterrows():
            if m['nombre'] not in tomas_hoy:
                with st.container():
                    c_msg, c_bt = st.columns([4, 1])
                    c_msg.warning(f"🔔 **TOMA PENDIENTE:** {m['nombre']} ({m['dosis']}) - Horario: {m['horario']}")
                    if c_bt.button("✅ TOMADA", key=m['nombre']):
                        conn.execute("INSERT INTO registro_medico (fecha, medicamento, hora_confirmada) VALUES (?,?,?)", (f_txt, m['nombre'], h_txt))
                        conn.commit()
                        st.rerun()
    else:
        st.info("No hay medicamentos configurados en el botiquín.")

# ==========================================
# 6. MÓDULO 🩺 GLUCOSA (CON PREDICCIÓN)
# ==========================================
elif menu == "🩺 GLUCOSA":
    st.title("🩺 Monitoreo de Salud")
    
    with st.container():
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: val = st.number_input("Valor mg/dL:", min_value=0)
        with c2: mom = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Almuerzo", "Post-Almuerzo", "Antes de Cena", "Post-Cena", "Antes de Dormir"])
        with c3: note = st.text_input("Nota / Observación:").upper()
        
        if st.button("💾 GUARDAR MEDICIÓN"):
            conn.execute("INSERT INTO glucosa (fecha, hora, momento, valor, nota) VALUES (?,?,?,?,?)", (f_txt, h_txt, mom, val, note))
            conn.commit()
            st.success("Medición registrada con éxito.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Gráfico y Predicción
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    if not df_g.empty:
        # Predicción rápida
        prom = df_g.head(7).valor.mean()
        diff = df_g.iloc[0].valor - prom
        if diff > 10: st.warning(f"🧐 **Análisis:** Su nivel actual está subiendo respecto al promedio semanal ({prom:.1f}).")
        
        fig = px.line(df_g, x='id', y='valor', title="Tendencia Reciente", markers=True, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        # Botón PDF Arreglado (Dando prioridad a su nombre)
        if st.button("📄 DESCARGAR REPORTE PDF OFICIAL"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="REPORTE MÉDICO - LUIS RAFAEL QUEVEDO", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            for _, r in df_g.iterrows():
                pdf.cell(200, 8, txt=f"{r['fecha']} | {r['momento']}: {r['valor']} mg/dL", ln=True)
            
            pdf_out = pdf.output(dest='S').encode('latin-1')
            st.download_button("📥 Click para descargar archivo", pdf_out, "Reporte_Quevedo.pdf", "application/pdf")

# ==========================================
# 7. MÓDULO 💰 FINANZAS (MODERNO)
# ==========================================
elif menu == "💰 FINANZAS":
    st.title("💰 Gestión de Capital")
    
    with st.expander("➕ Registrar Nuevo Movimiento", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        t_f = col_f1.selectbox("Tipo:", ["GASTO", "INGRESO"])
        m_f = col_f2.number_input("Monto $:", min_value=0.0)
        d_f = col_f3.text_input("Concepto:").upper()
        if st.button("💾 REGISTRAR"):
            conn.execute("INSERT INTO finanzas (fecha, tipo, monto, detalle) VALUES (?,?,?,?)", (f_txt, t_f, m_f, d_f))
            conn.commit()
            st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
    if not df_f.empty:
        st.table(df_f[['fecha', 'detalle', 'tipo', 'monto']].head(10))

# ==========================================
# 8. MÓDULO 💊 BOTIQUÍN (ACTUALIZADO)
# ==========================================
elif menu == "💊 BOTIQUÍN":
    st.title("💊 Inventario Farmacéutico")
    with st.form("meds"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Nombre:")
        d = c2.text_input("Dosis:")
        h = c3.text_input("Horario:")
        if st.form_submit_button("Añadir al Sistema"):
            conn.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
            conn.commit()
            st.rerun()

    df_m = pd.read_sql_query("SELECT * FROM medicamentos", conn)
    st.dataframe(df_m, use_container_width=True)
    if st.button("🔥 VACIAR BOTIQUÍN"):
        conn.execute("DELETE FROM medicamentos")
        conn.commit()
        st.rerun()

# --- Módulos restantes (Agenda y Bitácora) se mantienen con lógica similar pero con el nuevo estilo ---
elif menu == "🗓️ AGENDA":
    st.title("🗓️ Agenda de Citas")
    d_cita = st.text_input("Especialista:")
    f_cita = st.date_input("Fecha:")
    if st.button("Agendar"):
        conn.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (d_cita, str(f_cita)))
        conn.commit()
        st.success("Cita guardada")

elif menu == "📝 BITÁCORA":
    st.title("📝 Notas del Día")
    nota = st.text_area("Escriba aquí...")
    if st.button("Guardar Nota"):
        with open("bitacora_pro.txt", "a") as f:
            f.write(f"{f_txt}: {nota}\n")
        st.success("Nota archivada")

st.markdown("---")
st.caption(f"NEXUS PRO SYSTEM v5.0 | Luis Rafael Quevedo | 2026")
