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
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NEXUS - REPORTE DE SALUD', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo - Control Personal', 0, 0, 'C')

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

# --- 1. CONFIGURACIÓN VISUAL Y ESTILOS ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    
    /* Botones Estándar */
    div.stButton > button, div.stDownloadButton > button { 
        background-color: #1f2937; color: white; border: 1px solid #30363d; 
        border-radius: 8px; width: 100%; font-weight: bold; height: 50px; transition: 0.3s;
    }
    
    /* Botón Descarga PDF */
    div.stDownloadButton > button { background-color: #1e3a8a !important; border: 1px solid #3b82f6 !important; }
    div.stDownloadButton > button:hover { background-color: #2563eb !important; }

    /* Botón Borrar (Rojo) */
    .btn-borrar-rojo > div > button { 
        background-color: #441111 !important; color: #ff9999 !important; 
        border: 1px solid #662222 !important; height: 40px !important; 
    }
    
    /* Botón WhatsApp */
    a[data-testid="stLinkButton"] {
        background-color: #25D366 !important; color: white !important; 
        height: 50px !important; border-radius: 8px !important; 
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

# --- 3. FUNCIONES DE TIEMPO Y BASE DE DATOS ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    # CONEXIÓN DIRECTA A TU BASE DE DATOS REAL
    conn = sqlite3.connect("control_quevedo.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

# --- 4. LÓGICA DE INTERPRETACIÓN (SEMAFORO) ---
def interpretar_salud(valor, momento):
    if momento == "Ayunas":
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"
    elif momento == "Post-Desayuno (2h)":
        if valor < 140: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 140 <= valor <= 199: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"
    elif momento == "Antes de dormir":
        if 100 <= valor <= 140: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 141 <= valor <= 160: return "AMARILLO", "MEDIO", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "REVISAR", "background-color: #b71c1c; color: white;"
    return "GRIS", "N/A", ""

# --- 5. GENERADORES DE PDF ---
def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"PACIENTE: LUIS RAFAEL QUEVEDO", ln=True, align='L')
    pdf.ln(5)
    pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 10, " FECHA", 1, 0, 'C', True)
    pdf.cell(30, 10, " HORA", 1, 0, 'C', True)
    pdf.cell(55, 10, " MOMENTO", 1, 0, 'C', True)
    pdf.cell(30, 10, " VALOR", 1, 0, 'C', True)
    pdf.cell(40, 10, " SEMAFORO", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        color_slug, texto, _ = interpretar_salud(row['valor'], row['momento'])
        pdf.cell(35, 9, f" {row['fecha']}", 1)
        pdf.cell(30, 9, f" {row['hora']}", 1)
        pdf.cell(55, 9, f" {row['momento']}", 1)
        pdf.cell(30, 9, f" {row['valor']} mg/dL", 1)
        curr_x, curr_y = pdf.get_x(), pdf.get_y()
        pdf.cell(40, 9, f"      {texto}", 1, 1)
        pdf.dibujar_semaforo(curr_x + 3, curr_y + 2.5, color_slug)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

def generar_pdf_bitacora(contenido):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(190, 10, "BITÁCORA DE NOTAS PERSONALES", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(190, 10, contenido.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 6. INICIALIZACIÓN ---
db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 0.0

# --- 7. BARRA LATERAL (MENÚ) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 NEXUS CONTROL</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.markdown("---")
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 8. LÓGICA DE FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0.0
    if presupuesto_mensual > 0:
        porcentaje = min(gastos_mes / presupuesto_mensual, 1.0)
        st.write(f"📊 **Presupuesto del Mes ({mes_str}):** RD$ {gastos_mes:,.2f} / RD$ {presupuesto_mensual:,.2f}")
        st.progress(porcentaje)
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1 style='color:#2ecc71;'>RD$ {disponible:,.2f}</h1></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='balance-box'><h3>GASTOS DEL MES</h3><h1 style='color:#e74c3c;'>RD$ {gastos_mes:,.2f}</h1></div>", unsafe_allow_html=True)
    with st.form("form_finanzas", clear_on_submit=True):
        col1, col2, col3 = st.columns([1,1,2])
        t_mov = col1.selectbox("Tipo", ["GASTO", "INGRESO"])
        f_mov = col2.date_input("Fecha", value=f_obj)
        cat = col3.text_input("Categoría").upper()
        det = st.text_input("Detalle del movimiento").upper()
        monto = st.number_input("Monto RD$", min_value=0.0, step=100.0)
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            m_final = -abs(monto) if t_mov == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (f_mov.strftime("%d/%m/%Y"), f_mov.strftime("%m-%Y"), t_mov, cat, det, m_final))
            db.commit(); st.rerun()
    if not df_f.empty:
        st.subheader("Historial de Movimientos")
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
        st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
        if st.button("🗑️ BORRAR ÚLTIMO REGISTRO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 9. LÓGICA DE SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control Médico")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS"])
    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            c_pdf, c_wa = st.columns(2)
            with c_pdf:
                st.download_button("📥 DESCARGAR REPORTE SEMÁFORO (PDF)", generar_pdf_salud(df_g), f"Glucosa_{f_str}.pdf", "application/pdf", use_container_width=True)
            with c_wa:
                ult = df_g.iloc[0]
                msg = f"🩸 *REPORTE GLUCOSA*\n👤 Paciente: Luis Rafael Quevedo\n📅 Fecha: {ult['fecha']}\n🕒 Hora: {ult['hora']}\n📍 Valor: {ult['valor']} mg/dL\n📝 Momento: {ult['momento']}"
                st.link_button("📲 ENVIAR POR WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, title="Evolución de Glucosa", template="plotly_dark"), use_container_width=True)
            def color_tabla(row):
                _, _, estilo = interpretar_salud(row['valor'], row['momento'])
                return [estilo] * len(row)
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']].style.apply(color_tabla, axis=1), use_container_width=True)
            st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA LECTURA"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with st.form("form_glucosa", clear_on_submit=True):
            col_v, col_m = st.columns(2)
            val = col_v.number_input("Valor (mg/dL)", min_value=0)
            mom = col_m.selectbox("Momento", ["Ayunas", "Post-Desayuno (2h)", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR MEDICIÓN"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, mom, val)); db.commit(); st.rerun()
    with t2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, row in df_m.iterrows():
            col_info, col_del = st.columns([5,1])
            col_info.info(f"💊 **{row['nombre']}** | {row['dosis']} | 🕒 {row['horario']}")
            if col_del.button("🗑️", key=f"del_med_{row['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (row['id'],)); db.commit(); st.rerun()
        with st.form("form_meds", clear_on_submit=True):
            n_med = st.text_input("Nombre de Medicina").upper()
            d_med = st.text_input("Dosis").upper()
            h_med = st.text_input("Horario").upper()
            if st.form_submit_button("AÑADIR MEDICINA"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n_med, d_med, h_med)); db.commit(); st.rerun()
    with t3:
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        if not df_c.empty:
            st.table(df_c[['doctor', 'fecha', 'motivo']])
            st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA CITA"):
                db.execute("DELETE FROM citas WHERE id = (SELECT MAX(id) FROM citas)"); db.commit(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with st.form("form_citas", clear_on_submit=True):
            doc = st.text_input("Doctor").upper()
            fec_c = st.date_input("Fecha de Cita")
            mot = st.text_input("Motivo").upper()
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec_c), mot)); db.commit(); st.rerun()

# --- 10. LÓGICA DE BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora de Notas")
    path_notas = "nexus_notas.txt"
    contenido = open(path_notas, "r", encoding="utf-8").read() if os.path.exists(path_notas) else ""
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    nueva_nota = st.text_area("Escriba su nota aquí:", height=150)
    if col_btn1.button("💾 GUARDAR EN HISTORIAL"):
        if nueva_nota.strip():
            with open(path_notas, "a", encoding="utf-8") as f: f.write(f"[{f_str} {h_str}]: {nueva_nota}\n\n")
            st.rerun()
    if contenido:
        col_btn2.download_button("📥 DESCARGAR BITÁCORA (PDF)", generar_pdf_bitacora(contenido), f"Bitacora_{f_str}.pdf")
        st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
        if col_btn3.button("🗑️ LIMPIAR TODO EL HISTORIAL"):
            if os.path.exists(path_notas): os.remove(path_notas)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.text_area("Historial de notas:", contenido, height=350)

# --- 11. CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Configuración")
    nuevo_pres = st.number_input("Establecer Presupuesto Mensual (RD$)", min_value=0.0, value=float(presupuesto_mensual))
    if st.button("GUARDAR CONFIGURACIÓN"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_pres,))
        db.commit(); st.success("¡Configuración actualizada!")
        st.rerun()
