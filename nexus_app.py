import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import requests
from io import StringIO

# --- 1. CONFIGURACIÓN VISUAL NEXUS ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .info-box { background-color: #0c2d48; color: #5dade2; padding: 15px; border-radius: 10px; border-left: 5px solid #2e86c1; margin-bottom: 10px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 48px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
def check_password():
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
        return False
    return True

if check_password():
    # --- 3. FUNCIONES CORE ---
    def obtener_tiempo_rd():
        zona = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(zona)
        return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

    def iniciar_db():
        conn = sqlite3.connect("nexus_pro_v4.db", check_same_thread=False)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, notas TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
        conn.commit()
        return conn

    db = iniciar_db()
    f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

    # --- 4. BARRA LATERAL ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🌐 NEXUS CONTROL</h2>", unsafe_allow_html=True)
        st.info(f"📅 {f_str} | ⏰ {h_str}")
        
        st.markdown("### 🔔 PRÓXIMAS CITAS")
        df_citas_aviso = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY fecha ASC LIMIT 3", db)
        if not df_citas_aviso.empty:
            for _, r in df_citas_aviso.iterrows():
                st.markdown(f"<div class='info-box'>📍 {r['doctor']}<br>📅 {r['fecha']}</div>", unsafe_allow_html=True)
        else: st.write("Sin citas.")

        st.divider()
        menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
        if st.button("CERRAR SESIÓN"):
            del st.session_state["password_correct"]; st.rerun()

    # --- 5. MÓDULO: FINANZAS (CONEXIÓN POR CSV DIRECTO) ---
    if menu == "💰 FINANZAS":
        st.title("💰 Gestión Financiera")
        
        # URL de exportación directa (reemplaza el /edit por /export)
        URL_BASE = "https://docs.google.com/spreadsheets/d/12jg8nHRUCJwwty0VcsbWFvTIpRcGLCITNKLevZ7Nwb8"
        URL_CSV = f"{URL_BASE}/export?format=csv"
        
        try:
            # Lectura directa desde la web
            response = requests.get(URL_CSV)
            df_f = pd.read_csv(StringIO(response.text))
            
            # Limpieza básica
            df_f = df_f.dropna(how="all")

            with st.form("f_fin", clear_on_submit=True):
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("MOVIMIENTO", ["GASTO", "INGRESO"])
                f_gasto = c2.date_input("FECHA", value=f_obj)
                cat = st.text_input("CATEGORIA:").upper()
                det = st.text_input("DETALLE:").upper()
                monto = st.number_input("VALOR RD$:", min_value=0.0)
                
                if st.form_submit_button("REGISTRAR"):
                    st.warning("⚠️ Nota: La escritura directa requiere configuración extra. Por ahora, use este módulo para visualizar sus datos de Excel en tiempo real.")

            st.subheader("Registros en Google Sheets")
            st.dataframe(df_f, use_container_width=True)
            
            if not df_f.empty and "Monto" in df_f.columns:
                total = pd.to_numeric(df_f["Monto"]).sum()
                st.markdown(f"<div class='balance-box'><h3>DISPONIBLE EN EXCEL</h3><h1 style='color:#2ecc71;'>RD$ {total:,.2f}</h1></div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: Verifique que su Excel tenga los títulos: Fecha, Mes, Tipo, Categoria, Detalle, Monto")

    # --- 6. MÓDULO: SALUD ---
    elif menu == "🩺 SALUD":
        st.title("🩺 Control de Salud")
        t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

        with t1:
            with st.form("f_gluc"):
                c1, c2 = st.columns(2)
                valor = c1.number_input("Nivel mg/dL:", min_value=0)
                momento = c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
                not_g = st.text_input("NOTAS:").upper()
                if st.form_submit_button("GUARDAR GLUCOSA"):
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor, notas) VALUES (?,?,?,?,?)", (f_str, h_str, momento, valor, not_g))
                    db.commit(); st.rerun()
            
            df_g = pd.read_sql_query("SELECT fecha, momento, valor, notas FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                st.dataframe(df_g, use_container_width=True)
                st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, template="plotly_dark"))

        with t2:
            st.subheader("💊 Medicinas")
            with st.form("f_med", clear_on_submit=True):
                n = st.text_input("Nombre:").upper()
                d = st.text_input("Dosis:").upper()
                h = st.selectbox("Frecuencia:", ["UNA VEZ AL DÍA", "CADA 12 HORAS", "CADA 8 HORAS"])
                if st.form_submit_button("AÑADIR"):
                    db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                    db.commit(); st.rerun()
            st.dataframe(pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", db), use_container_width=True)

        with t3:
            st.subheader("📅 Citas Médicas")
            with st.form("f_cit"):
                doc = st.text_input("Doctor:").upper(); f_c = st.date_input("Fecha"); m_c = st.text_input("Motivo:").upper()
                if st.form_submit_button("AGENDAR"):
                    db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_c), m_c))
                    db.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db))

    # --- 7. MÓDULO: BITÁCORA ---
    elif menu == "📝 BITÁCORA":
        st.title("📝 Notas Personales")
        entrada = st.text_area("Escriba aquí:")
        if st.button("GUARDAR NOTA"):
            with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_str}]: {entrada}\n---\n")
            st.success("Nota guardada."); st.rerun()
        try:
            with open("nexus_notas.txt", "r", encoding="utf-8") as f:
                st.text_area("Historial:", f.read(), height=300)
        except: st.info("Sin notas.")
