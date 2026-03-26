import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
from fpdf import FPDF

# --- CLASE PDF CONFIGURADA ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo - Sistema Nexus', 0, 0, 'C')

# --- 1. CONFIGURACIÓN VISUAL PRO ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117 !important; }
    
    /* Tarjetas y Contenedores */
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22 !important; border-radius: 20px !important; 
        border: 1px solid #30363d !important; padding: 25px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important; margin-bottom: 20px !important;
    }
    
    /* Colores de Resalte */
    .neon-verde { color: #40E0D0 !important; font-weight: 800; font-size: 2.2rem; }
    .neon-rojo { color: #FF7F50 !important; font-weight: 800; font-size: 2.2rem; }
    
    /* Botones Premium */
    .stButton > button { 
        border-radius: 12px !important; font-weight: 700 !important; 
        transition: 0.3s all ease !important;
    }
    .stButton > button:hover { transform: translateY(-2px); border-color: #58a6ff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE TIEMPO Y BASE DE DATOS ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_final_v5.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- 3. SEGURIDAD DE ACCESO ---
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align:center; color:white;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    with st.form("login_nexus"):
        pwd = st.text_input("Contraseña de Acceso:", type="password")
        if st.form_submit_button("ENTRAR"):
            if pwd == "admin123": st.session_state["auth"] = True; st.rerun()
            else: st.error("Contraseña Incorrecta")
    st.stop()

# --- 4. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("🌐 NEXUS PRO")
    menu = st.radio("MENÚ PRINCIPAL", ["💰 PRESUPUESTO & FINANZAS", "🩺 CONTROL DE SALUD", "📝 BITÁCORA"])
    st.markdown("---")
    if st.button("CERRAR SESIÓN"): 
        del st.session_state["auth"]; st.rerun()

# --- 5. MÓDULO: PRESUPUESTO & FINANZAS ---
if menu == "💰 PRESUPUESTO & FINANZAS":
    st.title("💰 Gestión Financiera")
    
    # Presupuesto Meta
    res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
    presupuesto_fijo = res_conf[0] if res_conf else 0.0
    
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='balance-box'><h3>Balance Total</h3><div class='neon-verde'>RD$ {disponible:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='balance-box'><h3>Gastos del Mes</h3><div class='neon-rojo'>RD$ {gastos_mes:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='balance-box'><h3>Presupuesto Meta</h3><div style='color:#58a6ff; font-size:2rem; font-weight:800;'>RD$ {presupuesto_fijo:,.2f}</div></div>", unsafe_allow_html=True)

    with st.expander("⚙️ AJUSTAR PRESUPUESTO MENSUAL"):
        nuevo_p = st.number_input("Establecer Meta Mensual RD$:", min_value=0.0, value=presupuesto_fijo)
        if st.button("ACTUALIZAR"):
            db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
            db.commit(); st.rerun()

    with st.form("reg_fin", clear_on_submit=True):
        st.subheader("Nuevo Movimiento")
        col_t, col_f, col_m = st.columns(3)
        tipo_mov = col_t.selectbox("Tipo", ["GASTO", "INGRESO"])
        fec_mov = col_f.date_input("Fecha", f_obj)
        mon_mov = col_m.number_input("Monto RD$:", min_value=0.0)
        cat_mov = st.text_input("Categoría").upper()
        det_mov = st.text_input("Detalle").upper()
        if st.form_submit_button("REGISTRAR"):
            val_final = -mon_mov if tipo_mov == "GASTO" else mon_mov
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (fec_mov.strftime("%d/%m/%Y"), mes_str, tipo_mov, cat_mov, det_mov, val_final))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.subheader("Historial (Click en 🗑️ para borrar)")
        for _, r in df_f.iterrows():
            c_txt, c_del = st.columns([9,1])
            c_txt.info(f"**{r['fecha']}** | {r['tipo']} | {r['detalle']} | **RD$ {r['monto']:,.2f}**")
            if c_del.button("🗑️", key=f"f_{r['id']}"):
                db.execute("DELETE FROM finanzas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- 6. MÓDULO: CONTROL DE SALUD ---
elif menu == "🩺 CONTROL DE SALUD":
    st.title("🩺 Panel Médico")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark").update_traces(line_color='#40E0D0'), use_container_width=True)
            for _, r in df_g.head(5).iterrows():
                c_t, c_b = st.columns([9,1])
                c_t.success(f"{r['fecha']} - {r['momento']}: {r['valor']} mg/dL")
                if c_b.button("🗑️", key=f"g_{r['id']}"):
                    db.execute("DELETE FROM glucosa WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("f_g"):
            v = st.number_input("Valor:", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Desayuno", "Almuerzo", "Cena", "Noche"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()

    with t2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows():
            c_i, c_b = st.columns([9,1])
            c_i.warning(f"💊 **{r['nombre']}** | {r['dosis']} | {r['horario']}")
            if c_b.button("🗑️", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("f_m"):
            n, d, h = st.text_input("Nombre"), st.text_input("Dosis"), st.text_input("Horario")
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d, h)); db.commit(); st.rerun()

    with t3:
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        for _, r in df_c.iterrows():
            c_i, c_b = st.columns([9,1])
            c_i.error(f"📅 {r['fecha']} | Dr. {r['doctor']} | {r['motivo']}")
            if c_b.button("🗑️", key=f"c_{r['id']}"):
                db.execute("DELETE FROM citas WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("f_c"):
            dr, fe, mo = st.text_input("Dr."), st.date_input("Fecha"), st.text_input("Motivo")
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (dr.upper(), str(fe), mo.upper())); db.commit(); st.rerun()

# --- 7. MÓDULO: BITÁCORA (ACTUALIZADA) ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora Personal")
    
    nota = st.text_area("Nueva nota:", height=150, placeholder="Escriba aquí...")
    if st.button("GUARDAR NOTA"):
        if nota.strip():
            with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_str} {h_str}]: {nota.strip()}\n\n")
            st.success("Nota guardada.")
            st.rerun()

    st.markdown("---")
    
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f:
            contenido = f.read()
    except: contenido = ""

    if contenido:
        col_pdf, col_borrar, _ = st.columns([1, 1, 2])
        
        with col_pdf:
            pdf_b = PDF()
            pdf_b.add_page()
            pdf_b.set_font("Arial", 'B', 16); pdf_b.cell(190, 10, "NOTAS DE BITACORA", ln=True, align='C'); pdf_b.ln(10)
            pdf_b.set_font("Arial", '', 12); pdf_b.multi_cell(190, 8, contenido)
            st.download_button("📄 GENERAR PDF", pdf_b.output(dest='S').encode('latin-1', errors='replace'), f"Notas_{f_str}.pdf")

        with col_borrar:
            if st.button("🗑️ BORRAR TODO"):
                with open("nexus_notas.txt", "w", encoding="utf-8") as f: f.write("")
                st.rerun()

        st.text_area("Historial de Notas:", contenido, height=300)
    else:
        st.info("Sin notas registradas.")
