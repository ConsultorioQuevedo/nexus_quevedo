import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import pytz
import plotly.express as px
import io
import urllib.parse
import os
from fpdf import FPDF

# =========================================================
# 1. MOTOR DE REPORTES PDF PROFESIONAL (CLASE COMPLETA)
# =========================================================
class NEXUS_PDF(FPDF):
    def header(self):
        # Fondo del encabezado
        self.set_fill_color(22, 27, 34)
        self.rect(0, 0, 210, 35, 'F')
        self.set_font('Arial', 'B', 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'NEXUS - REPORTE DE CONTROL', 0, 1, 'C')
        self.set_font('Arial', 'I', 11)
        self.cell(0, 5, 'SISTEMA DE GESTIÓN PERSONAL - LUIS RAFAEL QUEVEDO', 0, 1, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150)
        self.cell(0, 10, f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")} | Página ' + str(self.page_no()), 0, 0, 'C')

    def draw_status_circle(self, x, y, status):
        if status == "VERDE": self.set_fill_color(34, 139, 34)
        elif status == "AMARILLO": self.set_fill_color(218, 165, 32)
        elif status == "ROJO": self.set_fill_color(178, 34, 34)
        self.ellipse(x, y, 4, 4, 'F')

# =========================================================
# 2. CONFIGURACIÓN DE ESTILOS UI (INTERFAZ OSCURA)
# =========================================================
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* Tarjetas de Métricas */
    .metric-card {
        background: #1c2128;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Alertas de Inicio */
    .alerta-box {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        border-left: 6px solid;
        background: #21262d;
    }
    
    /* Botones y Inputs */
    .stButton>button {
        background: linear-gradient(180deg, #21262d 0%, #0d1117 100%);
        color: #58a6ff;
        border: 1px solid #30363d;
        border-radius: 6px;
        width: 100%;
        font-weight: 600;
    }
    .stButton>button:hover { border-color: #58a6ff; color: #fff; }
    
    /* WhatsApp Green Button */
    .wa-button {
        background-color: #238636 !important;
        color: white !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 3. LÓGICA DE DATOS Y TIEMPO (SANTO DOMINGO)
# =========================================================
def get_time():
    tz = pytz.timezone('America/Santo_Domingo')
    now = datetime.now(tz)
    return now.strftime("%d/%m/%Y"), now.strftime("%I:%M %p"), now.strftime("%m-%Y"), now.date(), now

def init_db():
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def check_health(val, moment):
    if moment == "Ayunas":
        if 70 <= val <= 100: return "VERDE", "NORMAL", "color: #4ade80;"
        if 101 <= val <= 125: return "AMARILLO", "PRE-DIABETES", "color: #fbbf24;"
        return "ROJO", "ALTO", "color: #f87171;"
    else: # Post-Prandial o general
        if val < 140: return "VERDE", "NORMAL", "color: #4ade80;"
        if 140 <= val <= 199: return "AMARILLO", "PRE-DIABETES", "color: #fbbf24;"
        return "ROJO", "ALTO", "color: #f87171;"

# =========================================================
# 4. SEGURIDAD Y LOGIN
# =========================================================
if "authenticated" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🌐 NEXUS CORE</h1>", unsafe_allow_html=True)
    with st.container():
        _, col, _ = st.columns([1,2,1])
        with col:
            with st.form("login_form"):
                passwd = st.text_input("Contraseña Maestra", type="password")
                if st.form_submit_button("ACCEDER"):
                    if passwd == "admin123":
                        st.session_state.authenticated = True
                        st.rerun()
                    else: st.error("Acceso Denegado")
    st.stop()

# =========================================================
# 5. ESTRUCTURA PRINCIPAL (MENÚ)
# =========================================================
db = init_db()
f_hoy, h_ahora, mes_act, f_obj, dt_now = get_time()

with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>NEXUS PRO</h2>", unsafe_allow_html=True)
    st.info(f"📅 {f_hoy}\n\n🕒 {h_ahora}")
    menu = st.radio("SISTEMA", ["🏠 DASHBOARD", "💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.markdown("---")
    if st.button("LOGOUT"):
        del st.session_state.authenticated
        st.rerun()

# ---------------------------------------------------------
# MÓDULO: DASHBOARD
# ---------------------------------------------------------
if menu == "🏠 DASHBOARD":
    st.title("Panel de Control")
    
    # Notificaciones Rápidas
    c1, c2, c3 = st.columns(3)
    
    # 1. Alerta Citas
    prox_c = db.execute("SELECT doctor, fecha FROM citas WHERE fecha >= ? ORDER BY fecha LIMIT 1", (str(f_obj),)).fetchone()
    with c1:
        color = "#58a6ff" if not prox_c else "#f1c40f"
        st.markdown(f"<div class='alerta-box' style='border-left-color:{color}'><strong>PRÓXIMA CITA:</strong><br>{prox_c[0] if prox_c else 'No hay citas pendientes'}<br>{prox_c[1] if prox_c else ''}</div>", unsafe_allow_html=True)
    
    # 2. Alerta Glucosa
    ult_g = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
    with c2:
        if ult_g:
            s, t, _ = check_health(ult_g[0], ult_g[1])
            c_hex = "#238636" if s=="VERDE" else ("#d29922" if s=="AMARILLO" else "#da3633")
            st.markdown(f"<div class='alerta-box' style='border-left-color:{c_hex}'><strong>ÚLTIMA GLUCOSA:</strong><br>{ult_g[0]} mg/dL<br>Estado: {t}</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alerta-box'><strong>SALUD:</strong><br>Sin registros</div>", unsafe_allow_html=True)

    # 3. Alerta Presupuesto
    gastos_m = abs(db.execute("SELECT SUM(monto) FROM finanzas WHERE tipo='GASTO' AND mes=?", (mes_act,)).fetchone()[0] or 0)
    pres_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
    with c3:
        p_val = pres_conf[0] if pres_conf else 0
        porcentaje = (gastos_m / p_val * 100) if p_val > 0 else 0
        c_p = "#238636" if porcentaje < 80 else "#da3633"
        st.markdown(f"<div class='alerta-box' style='border-left-color:{c_p}'><strong>GASTO MENSUAL:</strong><br>{porcentaje:.1f}% del presupuesto<br>Restan: RD$ {max(0, p_val-gastos_m):,.2f}</div>", unsafe_allow_html=True)

    # Gráfico de Glucosa Reciente
    df_chart = pd.read_sql_query("SELECT fecha, valor FROM glucosa ORDER BY id DESC LIMIT 10", db)
    if not df_chart.empty:
        st.markdown("### Tendencia de Glucosa")
        fig = px.area(df_chart.iloc[::-1], x='fecha', y='valor', template="plotly_dark", color_discrete_sequence=['#58a6ff'])
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# MÓDULO: FINANZAS
# ---------------------------------------------------------
elif menu == "💰 FINANZAS":
    st.title("Gestión Financiera")
    
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        with st.form("form_f", clear_on_submit=True):
            tipo = st.selectbox("Movimiento", ["GASTO", "INGRESO"])
            monto = st.number_input("Monto RD$", min_value=0.0, step=50.0)
            cat = st.selectbox("Categoría", ["Salud", "Supermercado", "Servicios", "Transporte", "Inversión", "Otros"])
            det = st.text_input("Detalle").upper()
            if st.form_submit_button("REGISTRAR"):
                m_final = -monto if tipo == "GASTO" else monto
                db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_hoy, mes_act, tipo, cat, det, m_final))
                db.commit(); st.rerun()

    with col_f2:
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
        st.markdown(f"### Historial de {mes_act}")
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
        if st.button("🗑️ ELIMINAR ÚLTIMO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()

# ---------------------------------------------------------
# MÓDULO: SALUD
# ---------------------------------------------------------
elif menu == "🩺 SALUD":
    st.title("Control Médico Pro")
    
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS"])
    
    with t1:
        c_g1, c_g2 = st.columns([1, 2])
        with c_g1:
            with st.form("form_g", clear_on_submit=True):
                val_g = st.number_input("Nivel (mg/dL)", 100)
                mom_g = st.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
                if st.form_submit_button("GUARDAR LECTURA"):
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_hoy, h_ahora, mom_g, val_g))
                    db.commit(); st.rerun()
        
        with c_g2:
            df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                # Botones de Acción
                col_btn1, col_btn2 = st.columns(2)
                
                # WhatsApp
                ult = df_g.iloc[0]
                msg = f"*NEXUS SALUD*\nPaciente: Luis Rafael Quevedo\nValor: {ult['valor']} mg/dL\nMomento: {ult['momento']}\nFecha: {f_hoy}"
                link = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                col_btn1.markdown(f'<a href="{link}" target="_blank"><button class="wa-button" style="width:100%; height:40px; border-radius:6px; cursor:pointer;">📲 ENVIAR WHATSAPP</button></a>', unsafe_allow_html=True)
                
                # PDF
                pdf = NEXUS_PDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "HISTORIAL MÉDICO DE GLUCOSA", 0, 1)
                pdf.ln(5)
                for _, r in df_g.head(20).iterrows():
                    s_slug, s_text, _ = check_health(r['valor'], r['momento'])
                    pdf.set_font("Arial", '', 10)
                    pdf.cell(40, 10, f"{r['fecha']}")
                    pdf.cell(50, 10, f"{r['momento']}")
                    pdf.cell(30, 10, f"{r['valor']} mg/dL")
                    curr_x = pdf.get_x()
                    pdf.cell(40, 10, f"      {s_text}", 1, 1)
                    pdf.draw_status_circle(curr_x + 2, pdf.get_y() - 7, s_slug)
                
                col_btn2.download_button("📥 DESCARGAR PDF", pdf.output(dest='S').encode('latin-1'), "Reporte_Salud_Quevedo.pdf")
                
                # Tabla Visual
                st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']].head(10), use_container_width=True)

    with t2:
        with st.form("form_m"):
            col_m1, col_m2, col_m3 = st.columns(3)
            m_nom = col_m1.text_input("Medicamento")
            m_dos = col_m2.text_input("Dosis")
            m_hor = col_m3.text_input("Horario")
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (m_nom.upper(), m_dos.upper(), m_hor.upper()))
                db.commit(); st.rerun()
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        st.table(df_m[['nombre', 'dosis', 'horario']])

    with t3:
        with st.form("form_c"):
            col_c1, col_c2 = st.columns(2)
            c_doc = col_c1.text_input("Doctor")
            c_fec = col_c2.date_input("Fecha")
            c_mot = st.text_input("Motivo")
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (c_doc.upper(), str(c_fec), c_mot.upper()))
                db.commit(); st.rerun()
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        st.dataframe(df_c[['doctor', 'fecha', 'motivo']], use_container_width=True)

# ---------------------------------------------------------
# MÓDULO: BITÁCORA
# ---------------------------------------------------------
elif menu == "📝 BITÁCORA":
    st.title("Notas Personales")
    path_b = "nexus_bitacora.txt"
    
    nota = st.text_area("¿Qué tienes en mente hoy, Quevedo?", height=150)
    if st.button("💾 GUARDAR EN BITÁCORA"):
        if nota:
            with open(path_b, "a", encoding="utf-8") as f:
                f.write(f"--- {f_hoy} {h_ahora} ---\n{nota}\n\n")
            st.success("Nota almacenada con éxito.")
            st.rerun()
    
    if os.path.exists(path_b):
        with open(path_b, "r", encoding="utf-8") as f:
            st.text_area("Historial de Notas", f.read(), height=300)
        if st.button("🗑️ LIMPIAR BITÁCORA"):
            os.remove(path_b); st.rerun()

# ---------------------------------------------------------
# MÓDULO: CONFIG
# ---------------------------------------------------------
elif menu == "⚙️ CONFIG":
    st.title("Configuración del Sistema")
    p_actual = pres_conf[0] if pres_conf else 0.0
    nuevo_p = st.number_input("Establecer Presupuesto Mensual (RD$)", value=float(p_actual))
    if st.button("ACTUALIZAR PARÁMETROS"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
        db.commit()
        st.success("Configuración actualizada correctamente.")

db.close()
