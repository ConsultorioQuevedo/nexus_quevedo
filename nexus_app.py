import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
import os
from fpdf import FPDF

# --- CLASE PARA EL PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NEXUS - REPORTE DE SALUD', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'Luis Rafael Quevedo - Control Personal', 0, 0, 'C')
    def dibujar_semaforo(self, x, y, color_tipo):
        if color_tipo == "VERDE": self.set_fill_color(27, 94, 32)
        elif color_tipo == "AMARILLO": self.set_fill_color(251, 192, 45)
        elif color_tipo == "ROJO": self.set_fill_color(183, 28, 28)
        else: self.set_fill_color(200, 200, 200)
        self.ellipse(x, y, 4, 4, 'F')

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    .balance-box { background-color: #1f2937; padding: 20px; border-radius: 15px; text-align: center; border: 1px solid #30363d; }
    .alerta-card { padding: 15px; border-radius: 10px; background-color: #1c2128; border-left: 5px solid #30363d; margin-bottom: 10px; }
    div.stButton > button, div.stDownloadButton > button { background-color: #1f2937; color: white; border-radius: 8px; height: 50px; width: 100%; font-weight: bold; }
    div.stDownloadButton > button { background-color: #1e3a8a !important; border: 1px solid #3b82f6 !important; }
    .btn-borrar-rojo > div > button { background-color: #441111 !important; color: #ff9999 !important; border: 1px solid #662222 !important; }
    a[data-testid="stLinkButton"] { background-color: #25D366 !important; color: white !important; border-radius: 8px !important; height: 50px !important; display: flex !important; align-items: center; justify-content: center; text-decoration: none !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
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

# --- FUNCIONES CORE ---
def obtener_tiempo():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    # USANDO TU NOMBRE DE ARCHIVO ORIGINAL
    conn = sqlite3.connect("control_quevedo.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def interpretar_salud(valor, momento):
    if "Ayunas" in momento:
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "background-color: #1b5e20;"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c;"
    else:
        if valor < 140: return "VERDE", "NORMAL", "background-color: #1b5e20;"
        elif 140 <= valor <= 199: return "AMARILLO", "ELEVADO", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c;"

# --- INICIO ---
db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo()

with st.sidebar:
    st.title("🌐 NEXUS")
    menu = st.radio("IR A:", ["🏠 INICIO", "💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("SALIR"):
        del st.session_state["password_correct"]; st.rerun()

if menu == "🏠 INICIO":
    st.header(f"Panel de Control - Quevedo")
    st.info(f"📅 {f_str} | 🕒 {h_str}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📅 Próximas Citas")
        citas = db.execute("SELECT doctor, fecha FROM citas").fetchall()
        if citas:
            for c in citas[-2:]: st.markdown(f"<div class='alerta-card'>Dr. {c[0]}<br>{c[1]}</div>", unsafe_allow_html=True)
        else: st.write("No hay citas.")
    
    with col2:
        st.markdown("### 🩸 Última Glucosa")
        ult_g = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
        if ult_g:
            s, t, _ = interpretar_salud(ult_g[0], ult_g[1])
            st.markdown(f"<div class='alerta-card' style='border-left-color: {'#27ae60' if s=='VERDE' else '#e74c3c'};'>{ult_g[0]} mg/dL<br>{t}</div>", unsafe_allow_html=True)
        else: st.write("Sin datos.")

    with col3:
        st.markdown("### 💰 Balance")
        total = db.execute("SELECT SUM(monto) FROM finanzas").fetchone()[0] or 0.0
        st.markdown(f"<div class='alerta-card'>RD$ {total:,.2f}</div>", unsafe_allow_html=True)

elif menu == "💰 FINANZAS":
    st.header("💰 Gestión de Finanzas")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    
    col_a, col_b = st.columns(2)
    total_f = df_f['monto'].sum() if not df_f.empty else 0.0
    col_a.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1>RD$ {total_f:,.2f}</h1></div>", unsafe_allow_html=True)
    
    with st.form("add_fin", clear_on_submit=True):
        c1, c2, c3 = st.columns([1,1,2])
        tipo = c1.selectbox("Tipo", ["GASTO", "INGRESO"])
        fec = c2.date_input("Fecha", f_obj)
        cat = c3.text_input("Categoría").upper()
        det = st.text_input("Detalle").upper()
        mon = st.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            valor = -mon if tipo == "GASTO" else mon
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (fec.strftime("%d/%m/%Y"), fec.strftime("%m-%Y"), tipo, cat, det, valor))
            db.commit(); st.rerun()

    st.subheader("Historial Reciente")
    st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
    
    st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
    if st.button("🗑️ BORRAR ÚLTIMO MOVIMIENTO"):
        db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🩺 SALUD":
    st.header("🩺 Control de Salud")
    tab1, tab2, tab3 = st.tabs(["GLUCOSA", "MEDICINAS", "CITAS"])
    
    with tab1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            c_wa, c_del = st.columns([3,1])
            msg = f"Glucosa: {df_g.iloc[0]['valor']} mg/dL ({df_g.iloc[0]['momento']})"
            c_wa.link_button("📲 ENVIAR ÚLTIMA A WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(msg)}")
            
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark"))
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']], use_container_width=True)
            
            st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA LECTURA"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with st.form("add_glu", clear_on_submit=True):
            v = st.number_input("Valor mg/dL", 0)
            m = st.selectbox("Momento", ["Ayunas", "Post-Almuerzo", "Antes de dormir"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v))
                db.commit(); st.rerun()

    with tab2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows():
            st.info(f"💊 {r['nombre']} - {r['dosis']} ({r['horario']})")
        with st.form("add_med"):
            n = st.text_input("Medicina").upper()
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre) VALUES (?)", (n,)); db.commit(); st.rerun()

    with tab3:
        df_c = pd.read_sql_query("SELECT * FROM citas", db)
        st.table(df_c)
        with st.form("add_cita"):
            dr = st.text_input("Doctor")
            fe = st.date_input("Fecha")
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha) VALUES (?,?)", (dr, str(fe))); db.commit(); st.rerun()

elif menu == "📝 BITÁCORA":
    st.header("📝 Notas Personales")
    if not os.path.exists("nexus_notas.txt"): open("nexus_notas.txt", "w").close()
    
    nota = st.text_area("Escribir nota:")
    if st.button("💾 GUARDAR NOTA"):
        with open("nexus_notas.txt", "a") as f: f.write(f"[{f_str}]: {nota}\n\n")
        st.rerun()
    
    st.text_area("Historial:", open("nexus_notas.txt").read(), height=300)
    if st.button("🗑️ LIMPIAR BITÁCORA"):
        open("nexus_notas.txt", "w").close(); st.rerun()

elif menu == "⚙️ CONFIG":
    st.header("⚙️ Configuración")
    st.write("Base de datos conectada: **control_quevedo.db**")
    if st.button("REINICIAR VISTA"): st.rerun()
