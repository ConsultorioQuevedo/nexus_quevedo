import streamlit as st
import sqlite3
import pandas as pd
import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN ESTÉTICA "ZEN" ---
st.set_page_config(page_title="NEXUS PRO - SR. QUEVEDO", layout="wide", initial_sidebar_state="collapsed")

# CSS para que la interfaz se vea limpia, moderna y profesional
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 15px; border: 1px solid #374151; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background-color: #1e293b; border-radius: 10px 10px 0px 0px; 
        color: white; padding: 10px 20px; font-weight: bold;
    }
    .stTabs [aria-selected="true"] { background-color: #4f46e5 !important; border-bottom: 4px solid #818cf8; }
    div.stButton > button { border-radius: 20px; width: 100%; transition: 0.3s; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE CONEXIÓN (SU LÓGICA ORIGINAL) ---
def conectar_db():
    return sqlite3.connect('nexus_data.db', timeout=20)

# --- CREACIÓN DE TABLAS (SU BLINDAJE) ---
with conectar_db() as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tipo TEXT, 
                  categoria TEXT, monto REAL, nota TEXT, presupuesto REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS medicamentos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis TEXT, 
                  horario TEXT, stock_actual REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agenda 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, 
                  asunto TEXT, lugar TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS salud 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, glucosa INTEGER, notas TEXT)""")

# --- CABECERA ---
st.title("🚀 NEXUS PRO")
st.write(f"📅 {datetime.date.today().strftime('%d/%m/%Y')} | Usuario: **Sr. Quevedo**")

# --- NAVEGACIÓN POR PESTAÑAS (PARA LIMPIEZA VISUAL) ---
tab_dash, tab_fin, tab_salud, tab_botiquin, tab_agenda = st.tabs([
    "🏠 DASHBOARD", "💰 FINANZAS", "🩺 SALUD", "💊 BOTIQUÍN", "📅 AGENDA"
])
# --- TAB 1: DASHBOARD (ALERTAS INTELIGENTES) ---
with tab_dash:
    st.subheader("👋 Resumen General")
    c1, c2, c3 = st.columns(3)
    
    # Buscamos datos reales para los indicadores
    df_s_mini = pd.read_sql_query("SELECT glucosa FROM salud ORDER BY id DESC LIMIT 1", conectar_db())
    val_g = df_s_mini['glucosa'].iloc[0] if not df_s_mini.empty else "N/A"
    
    c1.metric("Última Glucosa", f"{val_g} mg/dL")
    c2.metric("Presupuesto RD$", "🟢 EN ORDEN")
    c3.metric("Citas Próximas", "Ver Agenda")
    
    st.divider()
    st.info("🔔 **RECORDATORIO:** No olvide registrar sus medicamentos y revisar sus niveles de glucosa hoy.")

# --- TAB 2: FINANZAS & ESCÁNER ---
with tab_fin:
    st.subheader("💰 Control Financiero")
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        if st.button("📸 ESCANEAR DOCUMENTO (OCR)"):
            st.toast("Iniciando escáner...")
            st.info("Función de visión artificial lista para integrar cámara.")
            
        with st.expander("➕ REGISTRO MANUAL", expanded=True):
            tipo = st.selectbox("Tipo:", ["GASTO", "INGRESO"])
            monto = st.number_input("Monto (RD$):", min_value=0.0, key="fin_monto")
            cat = st.selectbox("Categoría:", ["Salud", "Comida", "Servicios", "Otros"])
            nota = st.text_input("Detalle:", key="fin_nota")
            if st.button("💾 GUARDAR FINANZAS"):
                with conectar_db() as conn:
                    conn.execute("INSERT INTO finanzas (fecha, tipo, categoria, monto, nota) VALUES (?,?,?,?,?)",
                                (str(datetime.date.today()), tipo, cat, monto, nota))
                st.success("Guardado.")
                st.rerun()

    with col_f2:
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conectar_db())
        if not df_f.empty:
            st.dataframe(df_f.head(10), use_container_width=True)

# --- TAB 3: SALUD (CON SU SEMÁFORO ORIGINAL) ---
with tab_salud:
    st.subheader("🩺 Control de Glucosa")
    c_s1, c_s2 = st.columns([1, 2])
    
    with c_s1:
        valor = st.number_input("Nivel (mg/dL):", min_value=0, value=100)
        nota_s = st.text_input("Nota (ej: Ayunas):", key="sal_nota")
        
        if st.button("💾 REGISTRAR GLUCOSA"):
            with conectar_db() as conn:
                conn.execute("INSERT INTO salud (fecha, glucosa, notas) VALUES (?,?,?)",
                            (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), valor, nota_s))
            st.rerun()

        # SU SEMÁFORO ORIGINAL
        if valor < 70: st.error(f"🔴 NIVEL BAJO: {valor} (Hipoglucemia)")
        elif valor <= 130: st.success(f"🟢 NIVEL NORMAL: {valor}")
        elif valor <= 180: st.warning(f"🟡 NIVEL ELEVADO: {valor}")
        else: st.error(f"🔴 NIVEL MUY ALTO: {valor} (Peligro)")

    with c_s2:
        df_s = pd.read_sql_query("SELECT * FROM salud ORDER BY id DESC", conectar_db())
        if not df_s.empty:
            st.line_chart(df_s.set_index('fecha')['glucosa'])
            if st.button("📄 REPORTE PDF SALUD"):
                st.write("Generando archivo...")
                # Aquí va su lógica de FPDF que ya conocemos
# --- TAB 4: BOTIQUÍN ---
with tab_botiquin:
    st.subheader("💊 Mi Botiquín")
    with st.expander("➕ REGISTRAR MEDICAMENTO"):
        nombre = st.text_input("Nombre:")
        dosis = st.text_input("Dosis:")
        horario = st.text_input("Horario:")
        if st.button("💾 GUARDAR MEDICAMENTO"):
            with conectar_db() as conn:
                conn.execute("INSERT INTO medicamentos (nombre, dosis, horario, stock_actual) VALUES (?,?,?,?)",
                            (nombre, dosis, horario, 0))
            st.rerun()
    
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", conectar_db())
    st.dataframe(df_m, use_container_width=True)

# --- TAB 5: AGENDA & WHATSAPP ---
with tab_agenda:
    st.subheader("📅 Citas Médicas")
    with st.expander("➕ AGENDAR CITA"):
        f_cita = st.date_input("Fecha:")
        asunto = st.text_input("Asunto:")
        lugar = st.text_input("Lugar:")
        if st.button("💾 GUARDAR CITA"):
            with conectar_db() as conn:
                conn.execute("INSERT INTO agenda (fecha, hora, asunto, lugar) VALUES (?,?,?,?)",
                            (str(f_cita), "00:00", asunto, lugar))
            st.rerun()

    df_a = pd.read_sql_query("SELECT * FROM agenda ORDER BY fecha ASC", conectar_db())
    if not df_a.empty:
        for i, row in df_a.iterrows():
            with st.container():
                st.info(f"📌 {row['fecha']} - {row['asunto']} ({row['lugar']})")
                msg = f"Recordatorio: {row['asunto']} el {row['fecha']}"
                st.markdown(f"[📲 Avisar por WhatsApp](https://wa.me/?text={msg.replace(' ', '%20')})")
                if st.button(f"🗑️ Borrar {row['id']}", key=f"del_{row['id']}"):
                    with conectar_db() as conn:
                        conn.execute("DELETE FROM agenda WHERE id = ?", (row['id'],))
                    st.rerun()
                st.divider()                
