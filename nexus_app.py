import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse

# --- 1. CONFIGURACIÓN VISUAL (ESTILO NEXUS DARK) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .semaforo-box { padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; margin-bottom: 20px; font-size: 22px; border: 2px solid #ffffff22; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 45px; }
    .btn-borrar-rojo > div > button { 
        background-color: #441111 !important; 
        color: #ff9999 !important; 
        border: 1px solid #662222 !important; 
    }
    .stDownloadButton > button { background-color: #064e3b !important; color: #a7f3d0 !important; border: 1px solid #065f46 !important; width: 100%; }
    .btn-whatsapp > a {
        display: inline-block; width: 100%; text-align: center; background-color: #25D366; color: white !important;
        padding: 12px; border-radius: 10px; text-decoration: none; font-weight: bold; margin: 10px 0; border: 1px solid #128C7E;
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

# --- 3. FUNCIONES DE APOYO ---
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

def calcular_semaforo(valor, momento):
    if momento == "Ayunas":
        if 80 <= valor <= 120: return "🟢 NORMAL", "#166534"
        elif 121 <= valor <= 140: return "🟡 PRECAUCIÓN", "#854d0e"
        elif valor > 140: return "🔴 ALTA", "#991b1b"
        else: return "🔵 BAJA", "#1e3a8a"
    elif "Post" in momento: 
        if valor < 170: return "🟢 NORMAL", "#166534"
        elif 170 <= valor <= 180: return "🟡 LÍMITE", "#854d0e"
        else: return "🔴 ALTA", "#991b1b"
    return "⚪ REGISTRADO", "#1f2937"

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 20000.0

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL</h2>", unsafe_allow_html=True)
    st.info(f"📅 {f_str} | ⏰ {h_str}")
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.divider()
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    with st.form("f_fin", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tipo, f_mov = c1.selectbox("TIPO", ["GASTO", "INGRESO"]), c2.date_input("FECHA", value=f_obj)
        cat, det, monto = st.text_input("CATEGORÍA").upper(), st.text_input("DETALLE").upper(), st.number_input("MONTO RD$:", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_mov.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, m_real))
            db.commit(); st.rerun()
    
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    if not df_f.empty:
        total_disp = df_f["monto"].sum()
        st.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1 style='color:#2ecc71;'>RD$ {total_disp:,.2f}</h1></div>", unsafe_allow_html=True)
        
        msg_fin = urllib.parse.quote(f"💰 *NEXUS FINANZAS*\n📅 Fecha: {f_str}\n💵 Disponible: RD$ {total_disp:,.2f}\n📊 Estado: Actualizado")
        st.markdown(f"<div class='btn-whatsapp'><a href='https://wa.me/?text={msg_fin}' target='_blank'>📲 COMPARTIR BALANCE POR WHATSAPP</a></div>", unsafe_allow_html=True)

        st.markdown("<div class='btn-borrar-rojo'>", unsafe_allow_html=True)
        if st.button("🗑️ BORRAR ÚLTIMO MOVIMIENTO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- 6. SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            u = df_g.iloc[0]
            promedio = df_g['valor'].mean()
            txt, col = calcular_semaforo(u['valor'], u['momento'])
            st.markdown(f"<div class='semaforo-box' style='background-color:{col};'>ESTADO ACTUAL: {txt} ({u['valor']} mg/dL)</div>", unsafe_allow_html=True)
            
            # Reporte de Salud Ampliado para WhatsApp
            texto_w = f"🩸 *REPORTE NEXUS SALUD*\n📅 {f_str}\n\n📍 *Última:* {u['valor']} mg/dL ({u['momento']})\n📊 *Promedio General:* {promedio:.1f} mg/dL\n✅ *Estado:* {txt}"
            msg_salud = urllib.parse.quote(texto_w)
            st.markdown(f"<div class='btn-whatsapp'><a href='https://wa.me/?text={msg_salud}' target='_blank'>📲 ENVIAR REPORTE COMPLETO POR WHATSAPP</a></div>", unsafe_allow_html=True)

            fig = px.line(df_g.iloc[::-1], x='hora', y='valor', color='momento', markers=True)
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_g[['fecha', 'hora', 'momento', 'valor']].to_excel(writer, index=False)
            st.download_button("📥 DESCARGAR REPORTE EXCEL", buffer.getvalue(), f"Salud_{f_str}.xlsx")

        with st.form("f_gluc", clear_on_submit=True):
            v, m = st.number_input("Valor mg/dL:", min_value=0), st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR LECTURA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v))
                db.commit(); st.rerun()
        
        if not df_g.empty:
            st.markdown("<div class='btn-borrar-rojo'>", unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA LECTURA"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with t2:
        with st.form("f_med", clear_on_submit=True):
            n, d, h = st.text_input("MEDICINA").upper(), st.text_input("DOSIS").upper(), st.selectbox("HORARIO", ["DIARIO", "CADA 8H", "CADA 12H", "SI HAY DOLOR"])
            if st.form_submit_button("AÑADIR"):
                if n: db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows(): st.info(f"💊 {r['nombre']} - {r['dosis']} ({r['horario']})")
        if not df_m.empty:
            st.markdown("<div class='btn-borrar-rojo'>", unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA MEDICINA"):
                db.execute("DELETE FROM medicamentos WHERE id = (SELECT MAX(id) FROM medicamentos)"); db.commit(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with t3:
        with st.form("f_citas", clear_on_submit=True):
            doc, fec, mot = st.text_input("DOCTOR").upper(), st.date_input("FECHA"), st.text_input("MOTIVO").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot)); db.commit(); st.rerun()
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        for _, r in df_c.iterrows(): st.write(f"📅 **{r['fecha']}** | {r['doctor']} - {r['motivo']}"); st.divider()
        if not df_c.empty:
            st.markdown("<div class='btn-borrar-rojo'>", unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA CITA"):
                db.execute("DELETE FROM citas WHERE id = (SELECT MAX(id) FROM citas)"); db.commit(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# --- 7. BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora Personal")
    entrada = st.text_area("Nota del día:", height=150)
    if st.button("GUARDAR NOTA"):
        if entrada.strip():
            with open("nexus_notas.txt", "a", encoding="utf-8") as f: f.write(f"[{f_str} {h_str}]: {entrada}\n\n")
            st.success("Nota guardada."); st.rerun()
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f: st.text_area("Historial:", f.read(), height=400)
    except FileNotFoundError: st.info("Sin notas.")

# --- 8. CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes")
    np = st.number_input("Presupuesto Mensual (RD$):", min_value=0.0, value=float(presupuesto_mensual))
    if st.button("ACTUALIZAR"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (np,))
        db.commit(); st.success("Presupuesto actualizado.")
