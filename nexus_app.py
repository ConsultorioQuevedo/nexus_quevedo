import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px

# --- 1. CONFIGURACIÓN VISUAL NEXUS (COLORES Y ESTILO ORIGINAL) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; text-transform: uppercase; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .info-box { background-color: #0c2d48; color: #5dade2; padding: 15px; border-radius: 10px; border-left: 5px solid #2e86c1; margin-bottom: 10px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 48px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD (CONTRASEÑA MAESTRA) ---
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

# --- 3. FUNCIONES DE TIEMPO Y BASE DE DATOS (RESTAURADO) ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    # Usamos su archivo de base de datos principal
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- 4. BARRA LATERAL CON NOTIFICACIONES ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 NEXUS CONTROL</h2>", unsafe_allow_html=True)
    st.info(f"📅 {f_str} | ⏰ {h_str}")
    
    st.markdown("### 🔔 PRÓXIMAS CITAS")
    df_citas_aviso = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY fecha ASC LIMIT 2", db)
    if not df_citas_aviso.empty:
        for _, r in df_citas_aviso.iterrows():
            st.markdown(f"<div class='info-box'>📍 {r['doctor']}<br>📅 {r['fecha']}</div>", unsafe_allow_html=True)
    
    st.divider()
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. MÓDULO: FINANZAS (EL ORIGINAL CON QUINCENAS) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    
    # URL Directa para evitar el bloqueo de "Connecting..."
    URL_CSV = "https://docs.google.com/spreadsheets/d/12jg8nHRUCJwwty0VcsbWFvTIpRcGLCITNKLevZ7Nwb8/export?format=csv"
    
    try:
        df_f = pd.read_csv(URL_CSV).dropna(how="all")
        
        with st.form("f_fin", clear_on_submit=True):
            c1, c2 = st.columns(2)
            tipo = c1.selectbox("MOVIMIENTO", ["GASTO", "INGRESO"])
            f_mov = c2.date_input("FECHA", value=f_obj)
            cat = st.text_input("CATEGORIA:").upper()
            det = st.text_input("DETALLE:").upper()
            monto = st.number_input("VALOR RD$:", min_value=0.0)
            if st.form_submit_button("REGISTRAR"):
                st.warning("Nota: Para que el cambio sea permanente, añada la fila en su archivo de Google Sheets.")

        if not df_f.empty:
            df_f["Monto"] = pd.to_numeric(df_f["Monto"], errors='coerce').fillna(0)
            
            # Balance Grande
            st.markdown(f"<div class='balance-box'><h3>DISPONIBLE EN NUBE</h3><h1 style='color:#2ecc71;'>RD$ {df_f['Monto'].sum():,.2f}</h1></div>", unsafe_allow_html=True)
            
            # Resumen Quincenal Restaurado
            st.subheader("📊 RESUMEN POR QUINCENAS")
            df_f['Fecha_dt'] = pd.to_datetime(df_f['Fecha'], format='%d/%m/%Y', errors='coerce')
            df_f = df_f.dropna(subset=['Fecha_dt'])
            df_f['Quincena'] = df_f['Fecha_dt'].apply(lambda x: f"1ra Q ({x.strftime('%b')})" if x.day <= 15 else f"2da Q ({x.strftime('%b')})")
            resumen_q = df_f.groupby(['Quincena', 'Tipo'])['Monto'].sum().unstack().fillna(0)
            st.table(resumen_q.style.format("RD$ {:,.2f}"))
            
            st.subheader("HISTORIAL DE MOVIMIENTOS")
            st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
    except:
        st.error("⚠️ No se pudo conectar con el Excel. Verifique que el enlace sea público.")

# --- 6. MÓDULO: SALUD (RESTAURADO COMPLETO: GLUCOSA, MEDICINAS CON HORA, CITAS) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        with st.form("f_gluc"):
            c1, c2 = st.columns(2)
            valor = c1.number_input("Nivel mg/dL:", min_value=0)
            momento = c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
            if st.form_submit_button("GUARDAR GLUCOSA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, momento, valor))
                db.commit(); st.rerun()
        
        df_g = pd.read_sql_query("SELECT fecha, hora, momento, valor FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, title="TENDENCIA DE GLUCOSA", template="plotly_dark"))
            st.dataframe(df_g, use_container_width=True)

    with t2:
        st.subheader("💊 REGISTRO DE MEDICAMENTOS Y HORARIOS")
        with st.form("f_med", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            n_med = col1.text_input("MEDICAMENTO:").upper()
            d_med = col2.text_input("DOSIS:").upper()
            h_med = col3.text_input("HORARIO (EJ: 08:00 AM):").upper() # Campo restaurado
            if st.form_submit_button("AÑADIR MEDICINA"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n_med, d_med, h_med))
                db.commit(); st.rerun()
        st.table(pd.read_sql_query("SELECT nombre AS MEDICAMENTO, dosis AS DOSIS, horario AS HORARIO FROM medicamentos", db))

    with t3:
        st.subheader("📅 AGENDAR CITA MÉDICA")
        with st.form("f_cit"):
            doc = st.text_input("DOCTOR / ESPECIALIDAD:").upper()
            f_c = st.date_input("FECHA DE CITA")
            mot = st.text_input("MOTIVO:").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_c), mot))
                db.commit(); st.rerun()
        st.table(pd.read_sql_query("SELECT doctor AS DOCTOR, fecha AS FECHA, motivo AS MOTIVO FROM citas ORDER BY fecha ASC", db))

# --- 7. MÓDULO: BITÁCORA (RESTAURADO) ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora de Notas")
    entrada = st.text_area("ESCRIBA AQUÍ SU NOTA O RECORDATORIO:", height=200)
    if st.button("GUARDAR EN MEMORIA"):
        with open("nexus_notas.txt", "a", encoding="utf-8") as f:
            f.write(f"[{f_str} {h_str}]: {entrada}\n---\n")
        st.success("Nota guardada correctamente.")
    
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f:
            st.text_area("HISTORIAL DE NOTAS:", f.read(), height=400)
    except: st.info("Aún no hay notas registradas.")
