import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import os
from fpdf import FPDF

# --- CLASE PDF MODIFICADA ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(100)
        # Pie de página actualizado con tu nombre
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117 !important; }
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22 !important; border-radius: 20px !important; 
        border: 1px solid #30363d !important; padding: 25px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important; margin-bottom: 20px !important;
    }
    .neon-verde { color: #40E0D0 !important; font-weight: 800; font-size: 2.2rem; }
    .neon-rojo { color: #FF7F50 !important; font-weight: 800; font-size: 2.2rem; }
    .stButton > button { border-radius: 12px !important; font-weight: 700 !important; height: 45px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES Y BASE DE DATOS ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_final_v4.db", check_same_thread=False)
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

# --- 3. SEGURIDAD ---
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align:center; color:white;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Contraseña:", type="password")
        if st.form_submit_button("ENTRAR"):
            if pwd == "admin123": st.session_state["auth"] = True; st.rerun()
            else: st.error("Acceso denegado")
    st.stop()

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.title("🌐 MENÚ")
    menu = st.radio("", ["💰 PRESUPUESTO & FINANZAS", "🩺 CONTROL DE SALUD", "📝 BITÁCORA"])
    if st.button("CERRAR SESIÓN"): del st.session_state["auth"]; st.rerun()

# --- 5. MÓDULO: PRESUPUESTO & FINANZAS ---
if menu == "💰 PRESUPUESTO & FINANZAS":
    st.title("💰 Presupuesto y Finanzas")
    res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
    presupuesto_fijo = res_conf[0] if res_conf else 0.0
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    disponible = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='balance-box'><h3>Capital Total</h3><div class='neon-verde'>RD$ {disponible:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='balance-box'><h3>Gastos {mes_str}</h3><div class='neon-rojo'>RD$ {gastos_mes:,.2f}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='balance-box'><h3>Presupuesto Meta</h3><div style='color:#58a6ff; font-size:2rem; font-weight:800;'>RD$ {presupuesto_fijo:,.2f}</div></div>", unsafe_allow_html=True)

    with st.expander("⚙️ CONFIGURAR PRESUPUESTO MENSUAL"):
        nuevo_p = st.number_input("Establecer Presupuesto RD$:", min_value=0.0, value=presupuesto_fijo)
        if st.button("ACTUALIZAR META"):
            db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
            db.commit(); st.rerun()

    with st.form("registro_fin", clear_on_submit=True):
        st.subheader("Registrar Movimiento")
        col_a, col_b, col_c = st.columns(3)
        t = col_a.selectbox("Tipo", ["GASTO", "INGRESO"])
        f_g = col_b.date_input("Fecha", f_obj)
        m_g = col_c.number_input("Monto RD$:", min_value=0.0)
        cat = st.text_input("Categoría").upper()
        det = st.text_input("Detalle descriptivo").upper()
        if st.form_submit_button("GUARDAR TRANSACCIÓN"):
            m_final = -m_g if t == "GASTO" else m_g
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (f_g.strftime("%d/%m/%Y"), mes_str, t, cat, det, m_final))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.subheader("Historial de Movimientos")
        for _, r in df_f.iterrows():
            col_txt, col_del = st.columns([9,1])
            col_txt.info(f"**{r['fecha']}** | {r['tipo']} | {r['categoria']} | {r['detalle']} | **RD$ {r['monto']:,.2f}**")
            if col_del.button("🗑️", key=f"del_f_{r['id']}"):
                db.execute("DELETE FROM finanzas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- 6. MÓDULO: CONTROL DE SALUD ---
elif menu == "🩺 CONTROL DE SALUD":
    st.title("🩺 Gestión de Salud - Quevedo")
    tab_g, tab_m, tab_c = st.tabs(["🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS MÉDICAS"])

    with tab_g:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, title="Tendencia de Glucosa", template="plotly_dark"), use_container_width=True)
            for _, r in df_g.head(10).iterrows():
                col_t, col_b = st.columns([9,1])
                col_t.success(f"**{r['fecha']} {r['hora']}** - {r['momento']}: {r['valor']} mg/dL")
                if col_b.button("🗑️", key=f"del_g_{r['id']}"):
                    db.execute("DELETE FROM glucosa WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("add_glu"):
            v = st.number_input("Valor (mg/dL):", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Almuerzo", "Cena", "Noche"])
            if st.form_submit_button("REGISTRAR TOMA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, m, v))
                db.commit(); st.rerun()

    with tab_m:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, r in df_m.iterrows():
            col_i, col_b = st.columns([9,1])
            col_i.warning(f"💊 **{r['nombre']}** | Dosis: {r['dosis']} | Horario: {r['horario']}")
            if col_b.button("🗑️", key=f"del_m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("add_med"):
            n, d, h = st.text_input("Nombre"), st.text_input("Dosis"), st.text_input("Horario")
            if st.form_submit_button("AÑADIR MEDICAMENTO"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n.upper(), d, h))
                db.commit(); st.rerun()

    with tab_c:
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        for _, r in df_c.iterrows():
            col_i, col_b = st.columns([9,1])
            col_i.error(f"📅 **{r['fecha']}** | Dr. {r['doctor']} | Motivo: {r['motivo']}")
            if col_b.button("🗑️", key=f"del_c_{r['id']}"):
                db.execute("DELETE FROM citas WHERE id=?", (r['id'],)); db.commit(); st.rerun()
        with st.form("add_cita"):
            dr, fe, mo = st.text_input("Doctor"), st.date_input("Fecha"), st.text_input("Motivo")
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (dr.upper(), str(fe), mo.upper()))
                db.commit(); st.rerun()

# --- 7. MÓDULO: BITÁCORA (CORREGIDO) ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Notas y Bitácora")
    
    nota = st.text_area("Escribir pensamiento o nota del día:", height=150)
    if st.button("💾 GUARDAR NOTA"):
        if nota.strip():
            with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_str} {h_str}]: {nota.strip()}\n\n")
            st.success("Nota guardada.")
            st.rerun()
    
    st.markdown("---")
    
    if os.path.exists("nexus_notas.txt"):
        with open("nexus_notas.txt", "r", encoding="utf-8") as f:
            contenido = f.read()
    else:
        contenido = ""

    if contenido:
        # BOTONES DE ACCIÓN: PDF Y ELIMINAR
        col_pdf, col_del, col_sp = st.columns([1.5, 1.5, 4])
        
        with col_pdf:
            # Generador de PDF
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, "BITÁCORA PERSONAL", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(190, 8, contenido)
            
            st.download_button(
                label="📄 GENERAR PDF",
                data=pdf.output(dest='S').encode('latin-1', errors='replace'),
                file_name=f"Bitacora_{f_str}.pdf",
                mime="application/pdf"
            )

        with col_del:
            if st.button("🗑️ ELIMINAR TODO", type="secondary"):
                if os.path.exists("nexus_notas.txt"):
                    os.remove("nexus_notas.txt")
                    st.warning("Bitácora eliminada.")
                    st.rerun()
        
        st.text_area("Historial de Notas:", contenido, height=300)
    else:
        st.info("La bitácora está vacía.")
