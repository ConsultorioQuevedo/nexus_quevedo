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

# --- CLASE PARA EL PDF PROFESIONAL CON SEMÁFORO ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NEXUS - REPORTE DE SALUD INTEGRAL', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'Control de Glucosa - Luis Rafael Quevedo', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def dibujar_semaforo(self, x, y, color_tipo):
        if color_tipo == "VERDE": self.set_fill_color(27, 94, 32) 
        elif color_tipo == "AMARILLO": self.set_fill_color(251, 192, 45) 
        elif color_tipo == "ROJO": self.set_fill_color(183, 28, 28) 
        else: self.set_fill_color(200, 200, 200) 
        self.ellipse(x, y, 4, 4, 'F')

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #1c2128; border-radius: 15px; border: 1px solid #30363d; padding: 25px; }
    h1, h2, h3 { font-weight: 800; color: #f0f6fc; }
    
    .balance-box { 
        background-color: #1f2937; padding: 30px; border-radius: 15px; 
        text-align: center; border: 1px solid #30363d; margin-bottom: 20px;
    }

    .alerta-card {
        padding: 20px; border-radius: 12px; background-color: #1c2128;
        border: 1px solid #30363d; border-left: 8px solid #30363d; margin-bottom: 15px;
    }

    div.stButton > button, div.stDownloadButton > button { 
        background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; 
        border-radius: 8px; width: 100%; font-weight: bold; height: 45px; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #30363d; border-color: #8b949e; }
    
    a[data-testid="stLinkButton"] {
        background-color: #238636 !important; color: white !important; 
        height: 45px !important; border-radius: 8px !important; 
        display: flex !important; align-items: center; justify-content: center;
        font-weight: bold !important; text-decoration: none !important;
    }

    .btn-borrar-rojo > div > button { 
        background-color: #441111 !important; color: #ff9999 !important; 
        border: 1px solid #662222 !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 100px;'>🌐 NEXUS SYSTEM</h1>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1,1.5,1])
    with col_login:
        with st.form("login_form"):
            user_pwd = st.text_input("Introduzca Contraseña Maestra:", type="password")
            if st.form_submit_button("INGRESAR AL SISTEMA"):
                if user_pwd == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("Acceso Denegado")
    st.stop()

# --- 3. FUNCIONES DE BASE DE DATOS Y TIEMPO ---
def obtener_fecha_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def conectar_db():
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
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"
    else:
        if valor < 140: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 140 <= valor <= 199: return "AMARILLO", "ELEVADO", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO (REVISAR)", "background-color: #b71c1c; color: white;"

# --- 4. GENERACIÓN DE REPORTES ---
def exportar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(40, 44, 52); pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 10, " FECHA", 1, 0, 'C', True)
    pdf.cell(30, 10, " HORA", 1, 0, 'C', True)
    pdf.cell(50, 10, " MOMENTO", 1, 0, 'C', True)
    pdf.cell(35, 10, " VALOR", 1, 0, 'C', True)
    pdf.cell(40, 10, " ESTADO", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, r in df.iterrows():
        slug, txt, _ = interpretar_salud(r['valor'], r['momento'])
        pdf.cell(35, 10, f" {r['fecha']}", 1)
        pdf.cell(30, 10, f" {r['hora']}", 1)
        pdf.cell(50, 10, f" {r['momento']}", 1)
        pdf.cell(35, 10, f" {r['valor']} mg/dL", 1)
        x_pos, y_pos = pdf.get_x(), pdf.get_y()
        pdf.cell(40, 10, f"      {txt}", 1, 1)
        pdf.dibujar_semaforo(x_pos + 3, y_pos + 3, slug)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 5. LÓGICA DE NAVEGACIÓN ---
db_conn = conectar_db()
db = db_conn.cursor()
f_txt, h_txt, m_txt, f_obj = obtener_fecha_rd()

q_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_val = q_conf[0] if q_conf else 0.0

with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>🌐 NEXUS</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>{f_txt} | {h_txt}</p>", unsafe_allow_html=True)
    st.markdown("---")
    opcion = st.radio("SECCIONES", ["🏠 INICIO", "💰 FINANZAS", "🩺 SALUD", "💊 MEDICINAS", "📅 CITAS", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.markdown("---")
    if st.button("SALIR"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 6. PANTALLA: INICIO (INTELIGENCIA SUMADA) ---
if opcion == "🏠 INICIO":
    st.title(f"Bienvenido, Sr. Quevedo")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a: 
        st.subheader("Estado de Salud")
        u_glucosa = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
        if u_glucosa:
            slug, txt, _ = interpretar_salud(u_glucosa[0], u_glucosa[1])
            color = "#27ae60" if slug == "VERDE" else ("#f1c40f" if slug == "AMARILLO" else "#e74c3c")
            st.markdown(f"<div class='alerta-card' style='border-left-color: {color};'><strong>ÚLTIMA MEDICIÓN</strong><br>{u_glucosa[0]} mg/dL ({u_glucosa[1]})<br>Estado: {txt}</div>", unsafe_allow_html=True)
        else: st.info("Sin datos de glucosa.")

    with col_b: 
        st.subheader("Control Medicinas")
        n_meds = db.execute("SELECT COUNT(*) FROM medicamentos").fetchone()[0]
        st.markdown(f"<div class='alerta-card' style='border-left-color: #3498db;'><strong>PLAN ACTUAL</strong><br>{n_meds} Medicamentos registrados.<br>Revise la sección MEDICINAS.</div>", unsafe_allow_html=True)

    with col_c: 
        st.subheader("Gasto Mensual")
        g_mes = abs(db.execute("SELECT SUM(monto) FROM finanzas WHERE tipo='GASTO' AND mes=?", (m_txt,)).fetchone()[0] or 0)
        if presupuesto_val > 0:
            porc = (g_mes / presupuesto_val)
            color = "#27ae60" if porc < 0.8 else "#e74c3c"
            st.markdown(f"<div class='alerta-card' style='border-left-color: {color};'><strong>PRESUPUESTO</strong><br>{porc*100:.1f}% utilizado<br>Gasto: RD$ {g_mes:,.2f}</div>", unsafe_allow_html=True)
        else: st.warning("Configure presupuesto en Ajustes.")

# --- 7. PANTALLA: FINANZAS (INTELIGENCIA SUMADA) ---
elif opcion == "💰 FINANZAS":
    st.title("Gestión Financiera RD$")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db_conn)
    
    total_in = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum() if not df_f.empty else 0
    total_out = abs(df_f[df_f['tipo'] == 'GASTO']['monto'].sum()) if not df_f.empty else 0
    balance = total_in - total_out

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='balance-box'><h4 style='color:#2ecc71;'>INGRESOS</h4><h2>RD$ {total_in:,.2f}</h2></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='balance-box'><h4 style='color:#e74c3c;'>GASTOS</h4><h2>RD$ {total_out:,.2f}</h2></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='balance-box'><h4 style='color:#3498db;'>DISPONIBLE</h4><h2>RD$ {balance:,.2f}</h2></div>", unsafe_allow_html=True)

    # Gráfico de presupuesto (SUMA DE INTELIGENCIA)
    if presupuesto_val > 0:
        st.write(f"**Progreso de Gasto Mensual vs Presupuesto (RD$ {presupuesto_val:,.2f})**")
        progreso = min(total_out / presupuesto_val, 1.0)
        st.progress(progreso)

    with st.form("form_finanzas", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns([1,1,2])
        tipo = col_f1.selectbox("Movimiento", ["GASTO", "INGRESO"])
        fecha_mov = col_f2.date_input("Fecha", value=f_obj)
        cate = col_f3.text_input("Categoría").upper()
        deta = st.text_input("Detalle").upper()
        monto = st.number_input("Monto RD$", min_value=0.0, step=50.0)
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            monto_final = -monto if tipo == "GASTO" else monto
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (fecha_mov.strftime("%d/%m/%Y"), fecha_mov.strftime("%m-%Y"), tipo, cate, deta, monto_final))
            db_conn.commit(); st.rerun()

    if not df_f.empty:
        st.subheader("Historial de Movimientos")
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)

# --- 8. PANTALLA: SALUD (INTELIGENCIA MÉDICA SUMADA) ---
elif opcion == "🩺 SALUD":
    st.title("Control de Glucosa")
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db_conn)

    if not df_g.empty:
        u = df_g.iloc[0]
        slug, txt, _ = interpretar_salud(u['valor'], u['momento'])
        
        # SUMA DE INTELIGENCIA: Recomendación de medicamentos
        if slug == "ROJO":
            st.error(f"⚠️ ATENCIÓN: Nivel {txt}. Verifique sus medicamentos registrados.")
            meds_list = db.execute("SELECT nombre, dosis FROM medicamentos").fetchall()
            if meds_list:
                with st.expander("Recordatorio de Medicinas Registradas"):
                    for m in meds_list: st.write(f"• {m[0]} ({m[1]})")

        st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', title="Tendencia Glucosa", markers=True, template="plotly_dark"), use_container_width=True)
        
        st.download_button("📥 DESCARGAR PDF", exportar_pdf_salud(df_g), f"Salud_Quevedo_{f_txt}.pdf", "application/pdf")
        st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']], use_container_width=True)

    with st.form("form_glucosa", clear_on_submit=True):
        st.subheader("Nueva Medición")
        cg1, cg2 = st.columns(2)
        val_g = cg1.number_input("Valor (mg/dL)", min_value=0)
        mom_g = cg2.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
        if st.form_submit_button("GUARDAR RESULTADO"):
            db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_txt, h_txt, mom_g, val_g))
            db_conn.commit(); st.rerun()

# --- 9. PANTALLA: MEDICINAS ---
elif opcion == "💊 MEDICINAS":
    st.title("Control de Medicamentos")
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", db_conn)
    
    for _, r in df_m.iterrows():
        col_m1, col_m2 = st.columns([6,1])
        col_m1.info(f"💊 **{r['nombre']}** | {r['dosis']} | {r['horario']}")
        if col_m2.button("🗑️", key=f"med_{r['id']}"):
            db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db_conn.commit(); st.rerun()

    with st.form("form_med", clear_on_submit=True):
        st.subheader("Agregar Medicamento")
        m_nom = st.text_input("Nombre").upper()
        m_dos = st.text_input("Dosis").upper()
        m_hor = st.text_input("Horario").upper()
        if st.form_submit_button("REGISTRAR"):
            db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (m_nom, m_dos, m_hor))
            db_conn.commit(); st.rerun()

# --- 10. PANTALLA: CITAS ---
elif opcion == "📅 CITAS":
    st.title("Agenda de Citas")
    df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db_conn)
    if not df_c.empty: st.table(df_c[['doctor', 'fecha', 'motivo']])

    with st.form("form_citas", clear_on_submit=True):
        c_doc = st.text_input("Doctor").upper()
        c_fec = st.date_input("Fecha")
        c_mot = st.text_input("Motivo").upper()
        if st.form_submit_button("AGENDAR"):
            db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (c_doc, str(c_fec), c_mot))
            db_conn.commit(); st.rerun()

# --- 11. PANTALLA: BITÁCORA ---
elif opcion == "📝 BITÁCORA":
    st.title("Notas Personales")
    archivo_notas = "nexus_notas.txt"
    if st.button("🗑️ LIMPIAR TODO"):
        if os.path.exists(archivo_notas): os.remove(archivo_notas)
        st.rerun()
    
    nueva_n = st.text_area("Nueva nota:", height=100)
    if st.button("💾 GUARDAR"):
        with open(archivo_notas, "a", encoding="utf-8") as f:
            f.write(f"[{f_txt}]: {nueva_n}\n\n")
        st.rerun()
    
    if os.path.exists(archivo_notas):
        st.text_area("Historial:", open(archivo_notas, "r", encoding="utf-8").read(), height=300)

# --- 12. PANTALLA: CONFIGURACIÓN ---
elif opcion == "⚙️ CONFIG":
    st.title("Configuración")
    st.write(f"Presupuesto: **RD$ {presupuesto_val:,.2f}**")
    
    with st.form("form_config"):
        nuevo_p = st.number_input("Nuevo Límite Mensual:", min_value=0.0, value=float(presupuesto_val))
        if st.form_submit_button("ACTUALIZAR"):
            db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
            db_conn.commit(); st.success("Actualizado."); st.rerun()

    st.error("ZONA DE PELIGRO")
    if st.button("RESET TOTAL DEL SISTEMA"):
        for t in ["glucosa", "finanzas", "medicamentos", "citas"]: db.execute(f"DELETE FROM {t}")
        db_conn.commit(); st.rerun()

st.markdown("<p style='text-align: center; color: gray;'>Sistema Quevedo v4.1 - Inteligencia Activa</p>", unsafe_allow_html=True)
