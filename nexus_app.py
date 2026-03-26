import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
from fpdf import FPDF

# --- CLASE ESPECIAL PARA EL PDF ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- 1. CONFIGURACIÓN VISUAL PRO (MODERNA) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    /* Importar fuente moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* Tarjetas con Efecto de Profundidad (Cards) */
    .stForm, .balance-box { 
        background-color: #161b22; 
        border-radius: 20px !important; 
        border: 1px solid #30363d !important; 
        padding: 30px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    
    .balance-box h3 { color: #8b949e; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }

    /* Botones Estilo Premium con Degradado */
    div.stButton > button { 
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        color: #f0f6fc; border: 1px solid #30363d; 
        border-radius: 12px; font-weight: 700; height: 50px; transition: 0.4s;
    }
    div.stButton > button:hover { border-color: #58a6ff; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.4); }
    
    /* Botón PDF (Azul Zafiro Neón) */
    div.stDownloadButton > button { 
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%) !important; /* Verde éxito para PDF */
        border: none !important; border-radius: 12px !important;
    }
    
    /* Inputs Estilizados */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #0d1117 !important; border-radius: 10px !important; border: 1px solid #30363d !important;
    }

    /* Línea divisoria elegante */
    hr { border: 0; height: 1px; background-image: linear-gradient(to right, rgba(48, 54, 61, 0), rgba(48, 54, 61, 0.75), rgba(48, 54, 61, 0)); margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 50px; font-weight:800;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
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

# --- 3. FUNCIONES CORE ---
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

# COLORES NEÓN MATE (PRO)
def color_glucosa_pro(valor, momento):
    if momento == "Ayunas":
        if 70 <= valor <= 100: return "background-color: rgba(63, 195, 128, 0.2); color: #40E0D0; font-weight: bold;" # Neón Menta
        elif 101 <= valor <= 125: return "background-color: rgba(255, 191, 0, 0.2); color: #FFBF00; font-weight: bold;" # Ámbar
        else: return "background-color: rgba(255, 127, 80, 0.2); color: #FF7F50; font-weight: bold;" # Coral
    elif momento == "Post-Desayuno (2h)":
        if valor < 140: return "background-color: rgba(63, 195, 128, 0.2); color: #40E0D0;"
        elif 140 <= valor <= 199: return "background-color: rgba(255, 191, 0, 0.2); color: #FFBF00;"
        else: return "background-color: rgba(255, 127, 80, 0.2); color: #FF7F50;"
    elif momento == "Antes de dormir":
        if 100 <= valor <= 140: return "background-color: rgba(63, 195, 128, 0.2); color: #40E0D0;"
        elif 141 <= valor <= 160: return "background-color: rgba(255, 191, 0, 0.2); color: #FFBF00;"
        else: return "background-color: rgba(255, 127, 80, 0.2); color: #FF7F50;"
    return ""

def generar_pdf_salud(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "REPORTE HISTORICO DE GLUCOSA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_fill_color(22, 27, 34); pdf.set_text_color(255, 255, 255)
    pdf.cell(40, 10, " FECHA", 1, 0, 'C', True)
    pdf.cell(40, 10, " HORA", 1, 0, 'C', True)
    pdf.cell(70, 10, " MOMENTO", 1, 0, 'C', True)
    pdf.cell(40, 10, " VALOR", 1, 1, 'C', True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        pdf.cell(40, 9, f" {row['fecha']}", 1)
        pdf.cell(40, 9, f" {row['hora']}", 1)
        pdf.cell(70, 9, f" {row['momento']}", 1)
        pdf.cell(40, 9, f" {row['valor']} mg/dL", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1', errors='replace')

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# Presupuesto
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 0.0

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #58a6ff;'>🌐 CONTROL</h1>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.markdown("---")
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión de Capital")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0.0
    
    # Barra de presupuesto PRO
    if presupuesto_mensual > 0:
        porc = (gastos_mes / presupuesto_mensual)
        color_p = "#40E0D0" if porc < 0.8 else "#FFBF00" if porc <= 1.0 else "#FF7F50"
        st.markdown(f"**Uso Presupuestario: {porc:.1%}**")
        st.progress(min(porc, 1.0))
        if gastos_mes > presupuesto_mensual:
            st.warning(f"⚠️ Alerta: Presupuesto excedido por RD$ {gastos_mes - presupuesto_mensual:,.2f}")

    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='balance-box'><h3>Disponible Total</h3><h1 style='color:#40E0D0; font-weight:800;'>RD$ {disponible:,.2f}</h1></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='balance-box'><h3>Gastos del Mes</h3><h1 style='color:#FF7F50; font-weight:800;'>RD$ {gastos_mes:,.2f}</h1></div>", unsafe_allow_html=True)
    
    with st.form("f_fin", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
        f_mov = col2.date_input("FECHA", value=f_obj)
        cat = st.text_input("CATEGORÍA (EJ: COMIDA, CASA)").upper()
        det = st.text_input("DETALLE DEL MOVIMIENTO").upper()
        monto = st.number_input("MONTO RD$:", min_value=0.0, format="%.2f")
        if st.form_submit_button("REGISTRAR EN LIBRO"):
            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_mov.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, m_real))
            db.commit(); st.rerun()
    
    if not df_f.empty:
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
        if st.button("🗑️ ELIMINAR ÚLTIMA ENTRADA"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()

# --- 6. SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Panel de Salud - Quevedo")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            c_p, c_w = st.columns(2)
            with c_p:
                pdf_data = generar_pdf_salud(df_g)
                st.download_button("📥 DESCARGAR REPORTE PDF", pdf_data, f"Salud_{f_str}.pdf", "application/pdf", use_container_width=True)
            with c_w:
                u = df_g.iloc[0]
                t_w = f"🩺 *REPORTE LUIS R. QUEVEDO*\n📅 {f_str} | ⌚ {u['hora']}\n📍 Glucosa: {u['valor']} mg/dL\n📝 {u['momento']}"
                st.link_button("📲 ENVIAR A WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(t_w)}", use_container_width=True)
            
            # Gráfica Neón
            fig = px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, template="plotly_dark")
            fig.update_traces(line_color='#58a6ff', marker=dict(size=10, color='#40E0D0'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla Estilizada
            st.write("### Registro Histórico")
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']].style.apply(lambda r: [color_glucosa_pro(r['valor'], r['momento'])] * len(r), axis=1), use_container_width=True)

        with st.form("f_gluc", clear_on_submit=True):
            cg1, cg2 = st.columns(2)
            v = cg1.number_input("Valor (mg/dL):", min_value=0)
            m = cg2.selectbox("Momento de la toma:", ["Ayunas", "Post-Desayuno (2h)", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR EN EXPEDIENTE"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v)); db.commit(); st.rerun()

    with t2:
        st.markdown(f"### 💊 Registro de Medicación - {f_str}")
        df_meds = pd.read_sql_query("SELECT * FROM medicamentos", db)
        tomas_hoy = pd.read_sql_query("SELECT medicina_id FROM tomas_diarias WHERE fecha = ?", db, params=(f_str,))['medicina_id'].tolist()
        
        if not df_meds.empty:
            for _, m in df_meds.iterrows():
                # Tarjetas individuales de medicina
                with st.container():
                    c_txt, c_chk = st.columns([5, 1])
                    c_txt.markdown(f"**{m['nombre']}**  \n<small style='color:#8b949e;'>{m['dosis']} — {m['horario']}</small>", unsafe_allow_html=True)
                    presionado = c_chk.checkbox("", key=f"chk_{m['id']}", value=(m['id'] in tomas_hoy))
                    
                    if presionado and m['id'] not in tomas_hoy:
                        db.execute("INSERT INTO tomas_diarias (fecha, medicina_id) VALUES (?,?)", (f_str, m['id'])); db.commit()
                    elif not presionado and m['id'] in tomas_hoy:
                        db.execute("DELETE FROM tomas_diarias WHERE fecha = ? AND medicina_id = ?", (f_str, m['id'])); db.commit()
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

        with st.form("f_med", clear_on_submit=True):
            st.write("Añadir Medicamento Nuevo:")
            n, d, h = st.text_input("NOMBRE").upper(), st.text_input("DOSIS").upper(), st.text_input("HORARIO").upper()
            if st.form_submit_button("AÑADIR A LISTA"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()

    with t3:
        st.markdown("### 📅 Agenda de Citas Médicas")
        with st.form("f_citas", clear_on_submit=True):
            doc, fec, mot = st.text_input("DOCTOR / ESPECIALISTA").upper(), st.date_input("FECHA"), st.text_input("MOTIVO").upper()
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot)); db.commit(); st.rerun()
        st.dataframe(pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db), use_container_width=True)

# --- 7. BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora Personal")
    nota = st.text_area("¿Qué tienes en mente hoy?", height=150, placeholder="Escribe aquí tus notas...")
    if st.button("GUARDAR NOTA"):
        if nota.strip():
            with open("nexus_notas.txt", "a", encoding="utf-8") as f: f.write(f"[{f_str} {h_str}]: {nota}\n\n")
            st.success("Nota almacenada con éxito.")
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f: st.text_area("Historial de Notas:", f.read(), height=400)
    except: st.info("La bitácora está vacía por ahora.")

# --- 8. CONFIGURACIÓN ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes del Sistema")
    new_p = st.number_input("Establecer Presupuesto Mensual (RD$):", min_value=0.0, value=float(presupuesto_mensual))
    if st.button("GUARDAR PREFERENCIAS"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (new_p,))
        db.commit(); st.success("Ajustes actualizados"); st.rerun()
