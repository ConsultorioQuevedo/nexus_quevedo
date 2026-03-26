import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import pytz
import plotly.express as px
import io
import urllib.parse
import os
from fpdf import FPDF

# --- 1. CLASE PDF PROFESIONAL CON SEMÁFORO ---
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
        if color_tipo == "VERDE": self.set_fill_color(27, 94, 32) 
        elif color_tipo == "AMARILLO": self.set_fill_color(251, 192, 45) 
        elif color_tipo == "ROJO": self.set_fill_color(183, 28, 28) 
        else: self.set_fill_color(200, 200, 200) 
        self.ellipse(x, y, 4, 4, 'F')

# --- 2. CONFIGURACIÓN VISUAL Y ESTILOS CSS ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 10px 0; }
    .alerta-card { padding: 15px; border-radius: 10px; border-left: 5px solid; margin-bottom: 15px; background-color: #1c2128; border: 1px solid #30363d; border-left-width: 5px; }
    
    /* Botones */
    div.stButton > button, div.stDownloadButton > button { 
        background-color: #1f2937; color: white; border: 1px solid #30363d; 
        border-radius: 8px; width: 100%; font-weight: bold; height: 50px; transition: 0.3s;
    }
    div.stDownloadButton > button { background-color: #1e3a8a !important; border: 1px solid #3b82f6 !important; }
    .btn-borrar-rojo > div > button { background-color: #441111 !important; color: #ff9999 !important; border: 1px solid #662222 !important; height: 40px !important; }
    
    /* WhatsApp Link Button */
    a[data-testid="stLinkButton"] {
        background-color: #25D366 !important; color: white !important; height: 50px !important; 
        border-radius: 8px !important; display: flex !important; align-items: center; 
        justify-content: center; font-weight: bold !important; text-decoration: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SEGURIDAD ---
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

# --- 4. FUNCIONES DE TIEMPO Y BASE DE DATOS ---
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

# --- 5. LÓGICA DE INTERPRETACIÓN ---
def interpretar_salud(valor, momento):
    if "Ayunas" in momento:
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"
    else: # Post-prandial o dormir
        if valor < 140: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 140 <= valor <= 199: return "AMARILLO", "ELEVADO", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "MUY ALTO", "background-color: #b71c1c; color: white;"

# --- 6. GENERADORES DE PDF ---
def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"PACIENTE: LUIS RAFAEL QUEVEDO", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    cols = [("FECHA", 35), ("HORA", 30), ("MOMENTO", 55), ("VALOR", 30), ("ESTADO", 40)]
    for txt, w in cols: pdf.cell(w, 10, txt, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        c_slug, txt, _ = interpretar_salud(row['valor'], row['momento'])
        pdf.cell(35, 9, row['fecha'], 1)
        pdf.cell(30, 9, row['hora'], 1)
        pdf.cell(55, 9, row['momento'], 1)
        pdf.cell(30, 9, f"{row['valor']} mg/dL", 1)
        x, y = pdf.get_x(), pdf.get_y()
        pdf.cell(40, 9, f"      {txt}", 1, 1)
        pdf.dibujar_semaforo(x + 3, y + 2.5, c_slug)
    return pdf.output(dest='S').encode('latin-1', errors='replace')

# --- 7. PANEL DE ALERTAS PROACTIVO ---
def mostrar_panel_alertas(db, f_obj, pres_mensual):
    st.markdown("### 🔔 ALERTAS DEL SISTEMA")
    c1, c2, c3 = st.columns(3)
    
    # Citas
    with c1:
        citas = db.execute("SELECT doctor, fecha FROM citas").fetchall()
        encontrada = False
        for c in citas:
            try:
                f_cita = datetime.strptime(c[1], '%Y-%m-%d').date()
                diff = (f_cita - f_obj).days
                if 0 <= diff <= 3:
                    color = "#e74c3c" if diff == 0 else "#f1c40f"
                    st.markdown(f"<div class='alerta-card' style='border-left-color: {color};'><strong>📅 CITA PRÓXIMA</strong><br>{c[0]}<br>Faltan {diff} días</div>", unsafe_allow_html=True)
                    encontrada = True
            except: pass
        if not encontrada: st.success("✅ Sin citas próximas")

    # Glucosa
    with c2:
        ult = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
        if ult:
            c_slug, txt, _ = interpretar_salud(ult[0], ult[1])
            c_hex = "#2ecc71" if c_slug == "VERDE" else "#e74c3c"
            st.markdown(f"<div class='alerta-card' style='border-left-color: {c_hex};'><strong>🩸 ÚLTIMA GLUCOSA</strong><br>{ult[0]} mg/dL<br>{txt}</div>", unsafe_allow_html=True)
        else: st.info("ℹ️ Sin datos de salud")

    # Finanzas
    with c3:
        mes_act = f_obj.strftime("%m-%Y")
        gastos = db.execute("SELECT SUM(monto) FROM finanzas WHERE tipo='GASTO' AND mes=?", (mes_act,)).fetchone()[0] or 0
        gastos = abs(gastos)
        if pres_mensual > 0:
            porc = gastos / pres_mensual
            c_fin = "#2ecc71" if porc < 0.8 else "#e74c3c"
            st.markdown(f<div class='alerta-card' style='border-left-color: {c_fin};'><strong>💰 PRESUPUESTO</strong><br>{(porc*100):.1f}% usado<br>Restan RD$ {max(0, pres_mensual-gastos):,.2f}</div>, unsafe_allow_html=True)
        else: st.info("ℹ️ Configura tu presupuesto")

# --- 8. LÓGICA PRINCIPAL ---
db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
pres_mensual = res_conf[0] if res_conf else 0.0

with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 NEXUS PRO</h2>", unsafe_allow_html=True)
    menu = st.radio("NAVEGACIÓN", ["🏠 INICIO", "💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.markdown("---")
    if st.button("SALIR"): 
        del st.session_state["password_correct"]; st.rerun()

# --- SECCIÓN: INICIO ---
if menu == "🏠 INICIO":
    st.title(f"Bienvenido, Sr. Quevedo")
    st.info(f"📅 Fecha: {f_str} | 🕒 Hora: {h_str}")
    mostrar_panel_alertas(db, f_obj, pres_mensual)

# --- SECCIÓN: FINANZAS ---
elif menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    
    total = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_m = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0.0
    
    col_a, col_b = st.columns(2)
    col_a.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1 style='color:#2ecc71;'>RD$ {total:,.2f}</h1></div>", unsafe_allow_html=True)
    col_b.markdown(f"<div class='balance-box'><h3>GASTOS DEL MES</h3><h1 style='color:#e74c3c;'>RD$ {gastos_m:,.2f}</h1></div>", unsafe_allow_html=True)

    with st.form("f_finanzas", clear_on_submit=True):
        c1, c2, c3 = st.columns([1,1,2])
        t_m = c1.selectbox("Tipo", ["GASTO", "INGRESO"])
        f_m = c2.date_input("Fecha", value=f_obj)
        cat = c3.text_input("Categoría").upper()
        det = st.text_input("Detalle").upper()
        mon = st.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            final_m = -mon if t_m == "GASTO" else mon
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (f_m.strftime("%d/%m/%Y"), f_m.strftime("%m-%Y"), t_m, cat, det, final_m))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
        st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
        if st.button("🗑️ BORRAR ÚLTIMO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN: SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control Médico")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            c_a, c_b = st.columns(2)
            c_a.download_button("📥 DESCARGAR PDF SEMÁFORO", generar_pdf_salud(df_g), f"Salud_{f_str}.pdf")
            u = df_g.iloc[0]
            msg = f"🩸 *REPORTE GLUCOSA*\n👤 Luis Rafael Quevedo\n📍 Valor: {u['valor']} mg/dL\n📝 Momento: {u['momento']}"
            c_b.link_button("📲 ENVIAR WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(msg)}")
            
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark"), use_container_width=True)
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']].style.apply(lambda r: [interpretar_salud(r['valor'], r['momento'])[2]]*4, axis=1), use_container_width=True)
            
            st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
            if st.button("🗑️ BORRAR MEDICIÓN"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with st.form("f_glucosa", clear_on_submit=True):
            cv, cm = st.columns(2)
            val = cv.number_input("Valor mg/dL", min_value=0)
            mom = cm.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, mom, val)); db.commit(); st.rerun()

    with t2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows():
            col_i, col_d = st.columns([5,1])
            col_i.info(f"💊 **{r['nombre']}** | {r['dosis']} | 🕒 {r['horario']}")
            if col_d.button("🗑️", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("f_meds", clear_on_submit=True):
            n = st.text_input("Medicina").upper()
            d = st.text_input("Dosis").upper()
            h = st.text_input("Horario").upper()
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()

    with t3:
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        st.table(df_c[['doctor', 'fecha', 'motivo']])
        with st.form("f_citas", clear_on_submit=True):
            doc = st.text_input("Doctor").upper()
            fec = st.date_input("Fecha")
            mot = st.text_input("Motivo").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot)); db.commit(); st.rerun()

# --- SECCIÓN: BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    path = "nexus_notas.txt"
    if st.button("🗑️ LIMPIAR TODO EL HISTORIAL"):
        if os.path.exists(path): os.remove(path)
        st.rerun()
    nota = st.text_area("Nueva nota:", height=150)
    if st.button("💾 GUARDAR NOTA"):
        with open(path, "a", encoding="utf-8") as f: f.write(f"[{f_str}]: {nota}\n\n")
        st.rerun()
    if os.path.exists(path):
        st.text_area("Historial:", open(path, "r", encoding="utf-8").read(), height=300)

# --- SECCIÓN: CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Configuración")
    n_p = st.number_input("Presupuesto Mensual RD$", value=float(pres_mensual))
    if st.button("ACTUALIZAR"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (n_p,))
        db.commit(); st.success("¡Listo!"); st.rerun()
