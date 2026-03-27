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
    
    .alerta-card {
        padding: 20px; border-radius: 12px; background-color: #1c2128;
        border: 1px solid #30363d; border-left: 6px solid #30363d; margin-bottom: 10px;
    }

    div.stButton > button, div.stDownloadButton > button { 
        background-color: #1f2937; color: white; border: 1px solid #30363d; 
        border-radius: 8px; width: 100%; font-weight: bold; height: 50px; transition: 0.3s;
    }
    
    div.stDownloadButton > button { background-color: #1e3a8a !important; border: 1px solid #3b82f6 !important; }

    .btn-borrar-rojo > div > button { 
        background-color: #441111 !important; color: #ff9999 !important; 
        border: 1px solid #662222 !important; height: 40px !important; 
    }
    
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

# --- 3. FUNCIONES ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
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
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"

def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"PACIENTE: LUIS RAFAEL QUEVEDO", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 10, " FECHA", 1, 0, 'C', True)
    pdf.cell(30, 10, " HORA", 1, 0, 'C', True)
    pdf.cell(55, 10, " MOMENTO", 1, 0, 'C', True)
    pdf.cell(30, 10, " VALOR", 1, 0, 'C', True)
    pdf.cell(40, 10, " SEMAFORO", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        slug, txt, _ = interpretar_salud(row['valor'], row['momento'])
        pdf.cell(35, 9, f" {row['fecha']}", 1)
        pdf.cell(30, 9, f" {row['hora']}", 1)
        pdf.cell(55, 9, f" {row['momento']}", 1)
        pdf.cell(30, 9, f" {row['valor']} mg/dL", 1)
        cx, cy = pdf.get_x(), pdf.get_y()
        pdf.cell(40, 9, f"      {txt}", 1, 1)
        pdf.dibujar_semaforo(cx + 3, cy + 2.5, slug)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

def generar_pdf_bitacora(contenido):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(190, 10, "BITÁCORA DE NOTAS", ln=True, align='C'); pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(190, 10, contenido.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 4. INICIALIZACIÓN ---
db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 0.0

# --- 5. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 NEXUS CONTROL</h2>", unsafe_allow_html=True)
    menu = st.radio("MENÚ PRINCIPAL", ["🏠 INICIO", "💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 6. PANTALLAS ---
if menu == "🏠 INICIO":
    st.title(f"Bienvenido, Sr. Quevedo")
    st.info(f"📅 {f_str} | 🕒 {h_str}")
    
    st.markdown("### 🔔 PANEL DE ALERTA TEMPRANA")
    c1, c2, c3 = st.columns(3)
    
    with c1: # Alerta Citas
        citas = db.execute("SELECT doctor, fecha, motivo FROM citas").fetchall()
        hay_citas = False
        for c in citas:
            try:
                diff = (datetime.strptime(c[1], '%Y-%m-%d').date() - f_obj).days
                if 0 <= diff <= 3:
                    color = "#e74c3c" if diff == 0 else "#f1c40f"
                    st.markdown(f"<div class='alerta-card' style='border-left-color: {color};'><strong>📅 CITA</strong><br>{c[0]}<br>{'HOY' if diff==0 else f'En {diff} días'}</div>", unsafe_allow_html=True)
                    hay_citas = True
            except: pass
        if not hay_citas: st.success("✅ Sin citas próximas")

    with c2: # Alerta Salud
        ult_g = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
        if ult_g:
            slug, txt, _ = interpretar_salud(ult_g[0], ult_g[1])
            color = "#27ae60" if slug == "VERDE" else ("#f1c40f" if slug == "AMARILLO" else "#e74c3c")
            st.markdown(f"<div class='alerta-card' style='border-left-color: {color};'><strong>🩸 GLUCOSA</strong><br>{ult_g[0]} mg/dL<br>{txt}</div>", unsafe_allow_html=True)
        else: st.info("ℹ️ Sin datos de salud")

    with c3: # Alerta Finanzas
        gastos = abs(db.execute("SELECT SUM(monto) FROM finanzas WHERE tipo='GASTO' AND mes=?", (mes_str,)).fetchone()[0] or 0)
        if presupuesto_mensual > 0:
            porc = gastos / presupuesto_mensual
            color = "#27ae60" if porc < 0.8 else "#e74c3c"
            st.markdown(f"<div class='alerta-card' style='border-left-color: {color};'><strong>💰 GASTOS</strong><br>{porc*100:.1f}% usado<br>Resta: RD$ {max(0, presupuesto_mensual-gastos):,.2f}</div>", unsafe_allow_html=True)

elif menu == "💰 FINANZAS":
    st.title("💰 Finanzas")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1 style='color:#2ecc71;'>RD$ {disponible:,.2f}</h1></div>", unsafe_allow_html=True)
    
    with st.form("f_fin", clear_on_submit=True):
        col1, col2, col3 = st.columns([1,1,2])
        t_mov = col1.selectbox("Tipo", ["GASTO", "INGRESO"])
        f_mov = col2.date_input("Fecha", value=f_obj)
        cat = col3.text_input("Categoría").upper()
        det = st.text_input("Detalle").upper()
        monto = st.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            val = -monto if t_mov == "GASTO" else monto
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_mov.strftime("%d/%m/%Y"), f_mov.strftime("%m-%Y"), t_mov, cat, det, val))
            db.commit(); st.rerun()
    
    if not df_f.empty:
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
        st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
        if st.button("🗑️ BORRAR ÚLTIMO MOVIMIENTO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🩺 SALUD":
    st.title("🩺 Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])
    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            c_pdf, c_wa = st.columns(2)
            c_pdf.download_button("📥 REPORTE PDF SEMÁFORO", generar_pdf_salud(df_g), f"Salud_{f_str}.pdf", use_container_width=True)
            u = df_g.iloc[0]
            msg = f"🩸 *GLUCOSA*: {u['valor']} mg/dL ({u['momento']})"
            c_wa.link_button("📲 ENVIAR POR WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(msg)}", use_container_width=True)
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark"), use_container_width=True)
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']].style.apply(lambda r: [interpretar_salud(r['valor'], r['momento'])[2]]*4, axis=1), use_container_width=True)
            st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMA LECTURA"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with st.form("f_glu", clear_on_submit=True):
            v = st.number_input("Valor Glucosa", min_value=0); m = st.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR MEDICIÓN"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()
    with t2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows():
            ci, cd = st.columns([5,1])
            ci.info(f"💊 {r['nombre']} | {r['dosis']} | {r['horario']}")
            if cd.button("🗑️", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("f_med"):
            n = st.text_input("Nombre Medicina").upper(); d = st.text_input("Dosis").upper(); h = st.text_input("Horario").upper()
            if st.form_submit_button("AÑADIR MEDICAMENTO"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n,d,h)); db.commit(); st.rerun()
    with t3:
        df_c = pd.read_sql_query("SELECT * FROM citas", db)
        if not df_c.empty: st.table(df_c[['doctor', 'fecha', 'motivo']])
        with st.form("f_cit"):
            dr = st.text_input("Doctor").upper(); fe = st.date_input("Fecha Cita"); mo = st.text_input("Motivo").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (dr, str(fe), mo)); db.commit(); st.rerun()

elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    path = "nexus_notas.txt"
    cont = open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""
    n_nota = st.text_area("Nueva nota personal:")
    if st.button("💾 GUARDAR NOTA"):
        with open(path, "a", encoding="utf-8") as f: f.write(f"[{f_str} {h_str}]: {n_nota}\n\n")
        st.rerun()
    if cont:
        st.download_button("📥 DESCARGAR BITÁCORA PDF", generar_pdf_bitacora(cont), "Bitacora.pdf")
        st.text_area("Historial de Notas:", cont, height=300)

elif menu == "⚙️ CONFIG":
    st.title("⚙️ Configuración")
    st.subheader("Ajuste de Presupuesto Mensual")
    st.write(f"Presupuesto actual registrado: **RD$ {presupuesto_mensual:,.2f}**")
    with st.form("config_pres"):
        nuevo_p = st.number_input("Establecer nuevo presupuesto (RD$):", min_value=0.0, value=float(presupuesto_mensual))
        if st.form_submit_button("GUARDAR CAMBIOS"):
            db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
            db.commit(); st.success("¡Presupuesto actualizado!"); st.rerun()
