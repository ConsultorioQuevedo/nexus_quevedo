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

# --- CLASE ESPECIAL PARA EL PDF CON SEMÁFORO ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

    def dibujar_semaforo(self, x, y, color_tipo):
        if color_tipo == "VERDE":
            self.set_fill_color(27, 94, 32) 
        elif color_tipo == "AMARILLO":
            self.set_fill_color(251, 192, 45) 
        elif color_tipo == "ROJO":
            self.set_fill_color(183, 28, 28) 
        else:
            self.set_fill_color(200, 200, 200) 
        self.ellipse(x, y, 4, 4, 'F')

# --- 1. CONFIGURACIÓN VISUAL (ESTILOS CSS) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    
    div.stButton > button, div.stDownloadButton > button { 
        background-color: #1f2937; color: white; border: 1px solid #30363d; 
        border-radius: 8px; width: 100%; font-weight: bold; height: 55px; transition: 0.3s;
    }
    
    div.stDownloadButton > button { background-color: #1e3a8a !important; border: 1px solid #3b82f6 !important; }
    div.stDownloadButton > button:hover { background-color: #2563eb !important; }

    .btn-borrar-rojo > div > button { background-color: #441111 !important; color: #ff9999 !important; border: 1px solid #662222 !important; height: 40px; }
    
    a[data-testid="stLinkButton"] {
        background-color: #25D366 !important; color: white !important; 
        height: 55px !important; border-radius: 8px !important; 
        display: flex !important; align-items: center; justify-content: center;
        font-weight: bold !important; text-decoration: none !important; border: 1px solid #128C7E !important;
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

# --- 3. FUNCIONES CORE Y BASE DE DATOS ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_pro_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tomas_diarias (fecha TEXT, medicina_id INTEGER, PRIMARY KEY (fecha, medicina_id))')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def interpretar_para_semaforo(valor, momento):
    if momento == "Ayunas":
        if 70 <= valor <= 100: return "VERDE", "NORMAL"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES"
        else: return "ROJO", "ALTO"
    elif momento == "Post-Desayuno (2h)":
        if valor < 140: return "VERDE", "NORMAL"
        elif 140 <= valor <= 199: return "AMARILLO", "PRE-DIABETES"
        else: return "ROJO", "ALTO"
    elif momento == "Antes de dormir":
        if 100 <= valor <= 140: return "VERDE", "NORMAL"
        elif 141 <= valor <= 160: return "AMARILLO", "MEDIO"
        else: return "ROJO", "REVISAR"
    return "GRIS", "N/A"

def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "REPORTE HISTORICO DE GLUCOSA", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 8, f"PACIENTE: LUIS RAFAEL QUEVEDO", ln=True, align='C')
    pdf.ln(10)
    pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 10, " FECHA", 1, 0, 'C', True)
    pdf.cell(30, 10, " HORA", 1, 0, 'C', True)
    pdf.cell(55, 10, " MOMENTO", 1, 0, 'C', True)
    pdf.cell(30, 10, " VALOR", 1, 0, 'C', True)
    pdf.cell(40, 10, " SEMAFORO", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        color_slug, texto_estado = interpretar_para_semaforo(row['valor'], row['momento'])
        pdf.cell(35, 9, f" {row['fecha']}", 1)
        pdf.cell(30, 9, f" {row['hora']}", 1)
        pdf.cell(55, 9, f" {row['momento']}", 1)
        pdf.cell(30, 9, f" {row['valor']} mg/dL", 1)
        curr_x, curr_y = pdf.get_x(), pdf.get_y()
        pdf.cell(40, 9, f"      {texto_estado}", 1, 1)
        pdf.dibujar_semaforo(curr_x + 3, curr_y + 2.5, color_slug)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

def generar_pdf_bitacora(contenido):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(190, 10, "BITACORA DE NOTAS", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12); pdf.multi_cell(190, 10, contenido.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 4. INICIO DE APP ---
db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 0.0

with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. SECCIÓN FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0.0
    
    if presupuesto_mensual > 0:
        porc = min(gastos_mes / presupuesto_mensual, 1.0)
        st.write(f"📊 Uso del Presupuesto: {porc:.1%}")
        st.progress(porc)

    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1 style='color:#2ecc71;'>RD$ {disponible:,.2f}</h1></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='balance-box'><h3>GASTOS MES</h3><h1 style='color:#e74c3c;'>RD$ {gastos_mes:,.2f}</h1></div>", unsafe_allow_html=True)
    
    with st.form("f_fin", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
        f_mov = col2.date_input("FECHA", value=f_obj)
        cat, det = st.text_input("CATEGORÍA").upper(), st.text_input("DETALLE").upper()
        monto = st.number_input("MONTO RD$:", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_mov.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, m_real))
            db.commit(); st.rerun()
    
    if not df_f.empty:
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
        st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
        if st.button("🗑️ BORRAR ÚLTIMO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. SECCIÓN SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Salud - Luis Rafael Quevedo")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            col_pdf, col_wa = st.columns(2)
            with col_pdf:
                pdf_bytes = generar_pdf_salud(df_g)
                st.download_button("📥 GENERAR PDF (SEMÁFORO)", pdf_bytes, f"Salud_{f_str}.pdf", "application/pdf", use_container_width=True)
            with col_wa:
                u = df_g.iloc[0]
                texto_w = f"🩸 *REPORTE LUIS RAFAEL QUEVEDO*\n📅 {f_str}\n📍 Glucosa: {u['valor']} mg/dL\n📝 {u['momento']}"
                st.link_button("📲 WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(texto_w)}", use_container_width=True)
            
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, title="TENDENCIA", template="plotly_dark"), use_container_width=True)
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']], use_container_width=True)
            st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA LECTURA"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with st.form("f_gluc", clear_on_submit=True):
            v = st.number_input("Valor mg/dL:", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno (2h)", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()

    with t2:
        df_meds = pd.read_sql_query("SELECT * FROM medicamentos", db)
        if not df_meds.empty:
            for _, m in df_meds.iterrows():
                c_txt, c_del = st.columns([5, 1])
                c_txt.write(f"💊 **{m['nombre']}** - {m['dosis']} ({m['horario']})")
                if c_del.button("🗑️", key=f"del_med_{m['id']}"):
                    db.execute("DELETE FROM medicamentos WHERE id = ?", (m['id'],)); db.commit(); st.rerun()
        with st.form("f_med", clear_on_submit=True):
            n, d, h = st.text_input("MEDICINA").upper(), st.text_input("DOSIS").upper(), st.text_input("HORARIO").upper()
            if st.form_submit_button("AGREGAR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()

    with t3:
        df_citas = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        if not df_citas.empty:
            st.dataframe(df_citas[['doctor', 'fecha', 'motivo']], use_container_width=True)
            st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA CITA"):
                db.execute("DELETE FROM citas WHERE id = (SELECT MAX(id) FROM citas)"); db.commit(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with st.form("f_citas", clear_on_submit=True):
            doc, fec, mot = st.text_input("DOCTOR").upper(), st.date_input("FECHA"), st.text_input("MOTIVO").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot)); db.commit(); st.rerun()

# --- 7. SECCIÓN BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    if os.path.exists("nexus_notas.txt"):
        with open("nexus_notas.txt", "r", encoding="utf-8") as f: contenido_bitacora = f.read()
    else: contenido_bitacora = ""

    col_save, col_pdf, col_del = st.columns([1, 1, 1])
    nota = st.text_area("Nueva nota:", height=150)
    if col_save.button("💾 GUARDAR NOTA"):
        if nota.strip():
            with open("nexus_notas.txt", "a", encoding="utf-8") as f: f.write(f"[{f_str} {h_str}]: {nota}\n\n")
            st.rerun()
    if contenido_bitacora:
        col_pdf.download_button("📥 PDF BITÁCORA", generar_pdf_bitacora(contenido_bitacora), f"Bitacora_{f_str}.pdf")
        st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
        if col_del.button("🗑️ BORRAR HISTORIAL"):
            if os.path.exists("nexus_notas.txt"): os.remove("nexus_notas.txt")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.text_area("Historial:", contenido_bitacora, height=400)

# --- 8. SECCIÓN CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes")
    new_p = st.number_input("Presupuesto Mensual (RD$):", min_value=0.0, value=float(presupuesto_mensual))
    if st.button("GUARDAR"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (new_p,))
        db.commit(); st.success("Guardado")
