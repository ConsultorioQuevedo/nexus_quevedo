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

# ==========================================
# 1. MOTOR DE REPORTES PDF (CLASE EXTENSA)
# ==========================================
class PDF_Reporte(FPDF):
    def header(self):
        # Logo o Título
        self.set_fill_color(31, 41, 55)
        self.rect(0, 0, 210, 30, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'NEXUS - SISTEMA DE CONTROL PRO', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'REPORTE MÉDICO Y FINANCIERO - LUIS RAFAEL QUEVEDO', 0, 1, 'C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cell(0, 10, f'Generado por Nexus AI el {fecha_gen} - Página {self.page_no()}', 0, 0, 'C')

    def agregar_tabla_glucosa(self, df):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, 'HISTORIAL DE GLUCOSA', 0, 1, 'L')
        self.ln(2)
        
        # Encabezados
        self.set_fill_color(200, 200, 200)
        self.set_font('Arial', 'B', 10)
        headers = ['Fecha', 'Hora', 'Momento', 'Valor (mg/dL)', 'Estado']
        widths = [35, 30, 50, 35, 40]
        
        for i in range(len(headers)):
            self.cell(widths[i], 10, headers[i], 1, 0, 'C', True)
        self.ln()
        
        # Datos
        self.set_font('Arial', '', 10)
        for _, row in df.iterrows():
            slug, txt, _ = interpretar_salud(row['valor'], row['momento'])
            self.cell(widths[0], 9, str(row['fecha']), 1)
            self.cell(widths[1], 9, str(row['hora']), 1)
            self.cell(widths[2], 9, str(row['momento']), 1)
            self.cell(widths[3], 9, f"{row['valor']}", 1, 0, 'C')
            
            # Color según estado
            if slug == "VERDE": self.set_text_color(0, 100, 0)
            elif slug == "AMARILLO": self.set_text_color(150, 100, 0)
            elif slug == "ROJO": self.set_text_color(150, 0, 0)
            
            self.cell(widths[4], 9, txt, 1, 1, 'C')
            self.set_text_color(0, 0, 0)

# ==========================================
# 2. CONFIGURACIÓN Y ESTILOS CSS
# ==========================================
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main { background-color: #0b0e14; }
    .stApp { background-color: #0b0e14; color: #e6edf3; }
    
    /* Tarjetas de Indicadores */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-5px); border-color: #58a6ff; }
    
    /* Alertas Estilo Apple */
    .alerta {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid;
    }
    
    /* Botones Personalizados */
    div.stButton > button {
        background: linear-gradient(135deg, #1f6feb 0%, #094192 100%);
        color: white; border: none; border-radius: 8px;
        height: 45px; font-weight: bold; width: 100%;
    }
    
    /* Estilo para WhatsApp */
    .btn-whatsapp {
        background-color: #25D366 !important;
        color: white !important;
        text-decoration: none;
        padding: 10px 20px;
        border-radius: 8px;
        display: block;
        text-align: center;
        font-weight: bold;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. FUNCIONES CORE (SISTEMA)
# ==========================================
def obtener_tiempo():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date(), ahora

def iniciar_db():
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    # Creación de tablas si no existen
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def interpretar_salud(valor, momento):
    if momento == "Ayunas":
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "background-color: #1b5e20;"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "background-color: #795548;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c;"
    else: # Post-Prandial
        if valor < 140: return "VERDE", "NORMAL", "background-color: #1b5e20;"
        elif 140 <= valor <= 199: return "AMARILLO", "PRE-DIABETES", "background-color: #795548;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c;"

# ==========================================
# 4. LÓGICA DE NAVEGACIÓN Y VISTAS
# ==========================================
db = iniciar_db()
f_hoy, h_ahora, mes_act, f_obj, ahora_raw = obtener_tiempo()

# Seguridad Simple
if "autenticado" not in st.session_state:
    st.title("🌐 NEXUS CORE LOGIN")
    pw = st.text_input("Contraseña Maestra", type="password")
    if st.button("Acceder"):
        if pw == "admin123":
            st.session_state.autenticado = True
            st.rerun()
    st.stop()

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/179/179354.png", width=100)
    st.title("NEXUS PRO")
    st.write(f"📅 {f_hoy} | 🕒 {h_ahora}")
    st.markdown("---")
    opcion = st.radio("MENÚ PRINCIPAL", ["🏠 Dashboard", "💰 Finanzas", "🩺 Salud", "📝 Bitácora", "⚙️ Ajustes"])

# --- VISTA: DASHBOARD ---
if opcion == "🏠 Dashboard":
    st.title(f"Bienvenido, Sr. Quevedo")
    
    # KPIs Rápidos
    c1, c2, c3, c4 = st.columns(4)
    
    # Glucosa
    ult_g = db.execute("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
    val_g = ult_g[0] if ult_g else 0
    c1.markdown(f"<div class='metric-card'><h4>Última Glucosa</h4><h2 style='color:#58a6ff'>{val_g} mg/dL</h2></div>", unsafe_allow_html=True)
    
    # Balance
    bal = db.execute("SELECT SUM(monto) FROM finanzas").fetchone()[0] or 0.0
    c2.markdown(f"<div class='metric-card'><h4>Balance Total</h4><h2 style='color:#3fb950'>RD$ {bal:,.2f}</h2></div>", unsafe_allow_html=True)
    
    # Gastos Mes
    gastos = db.execute("SELECT SUM(monto) FROM finanzas WHERE tipo='GASTO' AND mes=?", (mes_act,)).fetchone()[0] or 0.0
    c3.markdown(f"<div class='metric-card'><h4>Gastos Mes</h4><h2 style='color:#f85149'>RD$ {abs(gastos):,.2f}</h2></div>", unsafe_allow_html=True)
    
    # Citas
    prox_c = db.execute("SELECT doctor FROM citas WHERE fecha >= ?", (str(f_obj),)).fetchone()
    c4.markdown(f"<div class='metric-card'><h4>Prox. Cita</h4><h2 style='color:#d2a8ff'>{prox_c[0] if prox_c else 'Ninguna'}</h2></div>", unsafe_allow_html=True)

    # Gráfica de Tendencia
    st.markdown("### 📈 Tendencia de Salud (Últimos 15 días)")
    df_chart = pd.read_sql_query("SELECT fecha, valor FROM glucosa ORDER BY id DESC LIMIT 15", db)
    if not df_chart.empty:
        fig = px.line(df_chart.iloc[::-1], x='fecha', y='valor', markers=True, template="plotly_dark", color_discrete_sequence=['#58a6ff'])
        st.plotly_chart(fig, use_container_width=True)

# --- VISTA: FINANZAS ---
elif opcion == "💰 Finanzas":
    st.title("Control de Finanzas")
    
    with st.form("form_fin"):
        col1, col2, col3 = st.columns([1,1,2])
        t = col1.selectbox("Tipo", ["INGRESO", "GASTO"])
        m = col2.number_input("Monto RD$", min_value=0.0)
        cat = col3.selectbox("Categoría", ["Salud", "Alimentos", "Servicios", "Otros", "Inversión"])
        det = st.text_input("Detalle (Ej: Compra Insulina)")
        if st.form_submit_button("Registrar Movimiento"):
            m_real = m if t == "INGRESO" else -m
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_hoy, mes_act, t, cat, det.upper(), m_real))
            db.commit()
            st.success("Registrado")
            st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)

# --- VISTA: SALUD ---
elif opcion == "🩺 Salud":
    st.title("Control Médico")
    
    tab1, tab2, tab3 = st.tabs(["🩸 Registro Glucosa", "💊 Medicamentos", "📅 Citas"])
    
    with tab1:
        c_i, c_d = st.columns([1,2])
        with c_i:
            with st.form("f_glu"):
                v = st.number_input("Valor mg/dL", 80)
                m = st.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
                if st.form_submit_button("Guardar"):
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_hoy, h_ahora, m, v))
                    db.commit()
                    st.rerun()
        
        with c_d:
            df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                # Botón WhatsApp
                ult = df_g.iloc[0]
                msg = f"Reporte Nexus: Glucosa {ult['valor']} mg/dL en {ult['momento']} ({f_hoy})"
                link_wa = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{link_wa}" class="btn-whatsapp">📲 Enviar Último Resultado a WhatsApp</a>', unsafe_allow_html=True)
                
                # Botón PDF
                pdf = PDF_Reporte()
                pdf.add_page()
                pdf.agregar_tabla_glucosa(df_g.head(20))
                btn_pdf = pdf.output(dest='S').encode('latin-1')
                st.download_button("📥 Descargar Reporte PDF", btn_pdf, "Reporte_Salud_Quevedo.pdf", "application/pdf")

    with tab2:
        with st.form("f_med"):
            col_n, col_d, col_h = st.columns(3)
            nom = col_n.text_input("Medicina")
            dos = col_d.text_input("Dosis")
            hor = col_h.text_input("Horario")
            if st.form_submit_button("Añadir"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (nom, dos, hor))
                db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        st.table(df_m)

# --- VISTA: AJUSTES ---
elif opcion == "⚙️ Ajustes":
    st.title("Configuración")
    pres = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
    val_pres = pres[0] if pres else 0.0
    
    nuevo_p = st.number_input("Presupuesto Mensual Sugerido RD$", value=val_pres)
    if st.button("Actualizar"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
        db.commit()
        st.success("Configuración Guardada")

# Cerrar conexión al final
db.close()
