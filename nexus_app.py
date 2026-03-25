import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px

# --- 1. CONFIGURACIÓN ESTÉTICA (EL LOOK "GENIAL") ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; text-transform: uppercase; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .info-card { background-color: #0c2d48; color: #5dade2; padding: 15px; border-radius: 10px; border-left: 5px solid #2e86c1; margin-bottom: 10px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 48px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD MAESTRA ---
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

# --- 3. FUNCIONES DE TIEMPO Y BASES DE DATOS ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

db = iniciar_db()
f_str, h_str, f_obj = obtener_tiempo_rd()

# --- 4. BARRA LATERAL (CONTROL TOTAL) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL CENTRAL</h2>", unsafe_allow_html=True)
    st.info(f"📅 {f_str} | ⏰ {h_str}")
    
    st.markdown("### 🔔 RECORDATORIO DE CITAS")
    df_citas_bar = pd.read_sql_query("SELECT doctor, fecha FROM citas ORDER BY fecha ASC LIMIT 2", db)
    for _, r in df_citas_bar.iterrows():
        st.markdown(f"<div class='info-card'>📍 {r['doctor']}<br>📅 {r['fecha']}</div>", unsafe_allow_html=True)
    
    st.divider()
    menu = st.radio("NAVEGACIÓN", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    if st.button("SALIR DEL SISTEMA"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 5. MÓDULO: FINANZAS (CONEXIÓN ROBUSTA) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    
    # URL Directa para saltar el error de "Connecting..."
    URL_CSV = "https://docs.google.com/spreadsheets/d/12jg8nHRUCJwwty0VcsbWFvTIpRcGLCITNKLevZ7Nwb8/export?format=csv"
    
    try:
        df_f = pd.read_csv(URL_CSV)
        # Limpieza de columnas para evitar fallos de tildes
        df_f.columns = [c.strip().replace('Categoría', 'Categoria').capitalize() for c in df_f.columns]
        
        st.success("✅ Datos sincronizados con la nube")

        # Métricas principales
        df_f["Monto"] = pd.to_numeric(df_f["Monto"], errors='coerce').fillna(0)
        total_disp = df_f["Monto"].sum()
        st.markdown(f"<div class='balance-box'><h3>DISPONIBLE EN CUENTA</h3><h1 style='color:#2ecc71;'>RD$ {total_disp:,.2f}</h1></div>", unsafe_allow_html=True)

        # Resumen Quincenal (Lo que más satisfacción dio)
        st.subheader("📊 Resumen por Quincenas")
        df_f['Fecha_dt'] = pd.to_datetime(df_f['Fecha'], dayfirst=True, errors='coerce')
        df_f = df_f.dropna(subset=['Fecha_dt'])
        df_f['Quincena'] = df_f['Fecha_dt'].apply(lambda x: f"1ra Q ({x.strftime('%b')})" if x.day <= 15 else f"2da Q ({x.strftime('%b')})")
        
        res_q = df_f.groupby(['Quincena', 'Tipo'])['Monto'].sum().unstack().fillna(0)
        st.table(res_q.style.format("RD$ {:,.2f}"))

        st.subheader("📝 Historial de Movimientos")
        st.dataframe(df_f.sort_values(by="Fecha_dt", ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Error de conexión. El servidor de Google no responde. Reintente en un momento.")

# --- 6. MÓDULO: SALUD (TODO: GLUCOSA, MEDICINAS CON BORRADO Y CITAS) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS MÉDICAS"])

    with t1:
        with st.form("f_glucosa"):
            col_a, col_b = st.columns(2)
            val = col_a.number_input("Nivel (mg/dL):", min_value=0, step=1)
            mom = col_b.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
            if st.form_submit_button("REGISTRAR LECTURA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, mom, val))
                db.commit()
                st.success("Registrado."); st.rerun()

        df_g = pd.read_sql_query("SELECT id, fecha, momento, valor FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, title="TENDENCIA GLUCÉMICA", template="plotly_dark"))
            # Botones de Borrado de Glucosa
            for i, r in df_g.iterrows():
                c1, c2 = st.columns([5,1])
                c1.write(f"🩸 {r['fecha']} - {r['momento']}: **{r['valor']} mg/dL**")
                if c2.button("Borrar", key=f"del_g_{r['id']}"):
                    db.execute("DELETE FROM glucosa WHERE id=?", (r['id'],))
                    db.commit(); st.rerun()

    with t2:
        st.subheader("💊 Esquema de Medicación")
        with st.form("f_meds"):
            c1, c2, c3 = st.columns([2,1,1])
            nom_m = c1.text_input("Nombre del Medicamento:")
            dos_m = c2.text_input("Dosis:")
            hor_m = c3.text_input("Horario (Ej: 8:00 AM):")
            if st.form_submit_button("AÑADIR A LA LISTA"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (nom_m.upper(), dos_m.upper(), hor_m.upper()))
                db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT id, nombre, dosis, horario FROM medicamentos", db)
        for i, r in df_m.iterrows():
            col1, col2 = st.columns([5,1])
            col1.markdown(f"<div class='info-card'>💊 **{r['nombre']}** | {r['dosis']} | ⏰ {r['horario']}</div>", unsafe_allow_html=True)
            if col2.button("Eliminar", key=f"del_m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],))
                db.commit(); st.rerun()

    with t3:
        st.subheader("📅 Agenda de Citas")
        with st.form("f_citas"):
            doc = st.text_input("Doctor/Especialidad:")
            fec_c = st.date_input("Fecha de la Cita:")
            mot = st.text_input("Motivo:")
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc.upper(), str(fec_c), mot.upper()))
                db.commit(); st.rerun()
        
        df_c = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        for i, r in df_c.iterrows():
            c1, c2 = st.columns([5,1])
            c1.write(f"📅 {r['fecha']} | **{r['doctor']}** - {r['motivo']}")
            if c2.button("Borrar", key=f"del_c_{r['id']}"):
                db.execute("DELETE FROM citas WHERE id=?", (r['id'],))
                db.commit(); st.rerun()

# --- 7. MÓDULO: BITÁCORA (NOTAS PERSONALES) ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora Nexus")
    nota = st.text_area("Escriba su pensamiento o recordatorio aquí:", height=150)
    if st.button("GUARDAR NOTA PERMANENTE"):
        with open("nexus_notas_quevedo.txt", "a", encoding="utf-8") as f:
            f.write(f"--- {f_str} {h_str} ---\n{nota}\n\n")
        st.success("Nota almacenada con éxito.")
    
    st.divider()
    st.subheader("📖 Historial de Notas")
    try:
        with open("nexus_notas_quevedo.txt", "r", encoding="utf-8") as f:
            st.text(f.read())
    except: st.info("La bitácora está vacía.")
