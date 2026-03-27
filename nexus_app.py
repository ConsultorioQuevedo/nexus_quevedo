import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import urllib.parse
import os
from fpdf import FPDF

# --- 1. CONFIGURACIÓN Y ESTILO NEXUS ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stForm { background-color: #1c2128; border-radius: 15px; border: 1px solid #30363d; padding: 25px; }
    h1, h2, h3 { color: #f0f6fc; font-weight: 700; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 45px; }
    /* Estilo para botones de borrado */
    div.stButton > button:first-child:contains("BORRAR") {
        background-color: #441111; color: #ff9999; border: 1px solid #662222;
    }
    /* Estilo WhatsApp */
    a[data-testid="stLinkButton"] {
        background-color: #238636 !important; color: white !important; font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD DE ACCESO ---
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 100px;'>🌐 NEXUS SYSTEM</h1>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1,1.2,1])
    with col_login:
        with st.form("login_nexus"):
            pwd = st.text_input("Introduzca Clave Maestra:", type="password")
            if st.form_submit_button("INGRESAR"):
                if pwd == "admin123":
                    st.session_state["auth"] = True
                    st.rerun()
                else: st.error("Acceso denegado")
    st.stop()

# --- 3. FUNCIONES DE TIEMPO Y BASE DE DATOS ---
def obtener_info_rd():
    rd_tz = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(rd_tz)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def conectar_db():
    conn = sqlite3.connect("control_nexus_quevedo.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

db_conn = conectar_db()
db = db_conn.cursor()
f_hoy, h_hoy, m_hoy, f_obj = obtener_info_rd()

# --- 4. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 NEXUS</h2>", unsafe_allow_html=True)
    st.write(f"📅 **Fecha:** {f_hoy}")
    st.write(f"🕒 **Hora:** {h_hoy}")
    st.markdown("---")
    menu = st.radio("MENÚ PRINCIPAL", ["🩺 SALUD", "💰 FINANZAS", "💊 MEDICINAS", "📅 CITAS", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.markdown("---")
    if st.button("SALIR"):
        del st.session_state["auth"]
        st.rerun()

# --- 5. SECCIÓN SALUD (SÓLIDA) ---
if menu == "🩺 SALUD":
    st.title("🩺 Control de Glucosa")
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db_conn)
    
    if not df_g.empty:
        col_wa, col_del = st.columns(2)
        with col_wa:
            u = df_g.iloc[0]
            wa_msg = f"Reporte Glucosa - Valor: {u['valor']} mg/dL ({u['momento']}) - Fecha: {u['fecha']} {u['hora']}"
            st.link_button("📲 ENVIAR POR WHATSAPP", f"https://wa.me/?text={urllib.parse.quote(wa_msg)}")
        with col_del:
            if st.button("🗑️ BORRAR ÚLTIMO REGISTRO"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                db_conn.commit(); st.rerun()
        
        st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', title="Tendencia de Niveles", markers=True, template="plotly_dark"))
        st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']], use_container_width=True)

    with st.form("form_glucosa", clear_on_submit=True):
        st.subheader("Registrar Nueva Lectura")
        c1, c2 = st.columns(2)
        v_g = c1.number_input("Valor (mg/dL):", min_value=0)
        m_g = c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
        if st.form_submit_button("GUARDAR EN BASE DE DATOS"):
            db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_hoy, h_hoy, m_g, v_g))
            db_conn.commit(); st.rerun()

# --- 6. SECCIÓN FINANZAS (ESTABLE) ---
elif menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera RD$")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db_conn)
    
    if not df_f.empty:
        if st.button("🗑️ ELIMINAR ÚLTIMO MOVIMIENTO"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)")
            db_conn.commit(); st.rerun()
            
        t_in = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
        t_out = abs(df_f[df_f['tipo'] == 'GASTO']['monto'].sum())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Totales", f"RD$ {t_in:,.2f}")
        c2.metric("Gastos Totales", f"RD$ {t_out:,.2f}")
        c3.metric("Balance Neto", f"RD$ {(t_in - t_out):,.2f}", delta_color="normal")

    with st.form("form_finanzas", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        tipo = col_f1.selectbox("Tipo de Movimiento:", ["GASTO", "INGRESO"])
        monto = col_f2.number_input("Monto (RD$):", min_value=0.0)
        cate = st.text_input("Categoría:").upper()
        deta = st.text_input("Detalle o Nota:").upper()
        if st.form_submit_button("REGISTRAR TRANSACCIÓN"):
            m_final = -monto if tipo == "GASTO" else monto
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (f_hoy, m_hoy, tipo, cate, deta, m_final))
            db_conn.commit(); st.rerun()
    
    if not df_f.empty:
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)

# --- 7. MEDICINAS (BORRADO INDIVIDUAL) ---
elif menu == "💊 MEDICINAS":
    st.title("💊 Medicamentos y Horarios")
    df_m = pd.read_sql_query("SELECT * FROM meds", db_conn)
    
    for _, r in df_m.iterrows():
        col_m1, col_m2 = st.columns([5,1])
        col_m1.info(f"💊 **{r['nombre']}** | Dosis: {r['dosis']} | Hora: {r['horario']}")
        if col_m2.button("🗑️", key=f"del_med_{r['id']}"):
            db.execute("DELETE FROM meds WHERE id=?", (r['id'],))
            db_conn.commit(); st.rerun()

    with st.form("form_meds"):
        st.subheader("Añadir Medicamento")
        n_m = st.text_input("Nombre del Fármaco:").upper()
        d_m = st.text_input("Dosis (ej. 500mg):").upper()
        h_m = st.text_input("Horario sugerido:").upper()
        if st.form_submit_button("AGREGAR AL PLAN"):
            db.execute("INSERT INTO meds (nombre, dosis, horario) VALUES (?,?,?)", (n_m, d_m, h_m))
            db_conn.commit(); st.rerun()

# --- 8. BITÁCORA Y CITAS ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Notas y Observaciones")
    if st.button("LIMPIAR BITÁCORA"):
        if os.path.exists("nexus_notas.txt"): os.remove("nexus_notas.txt")
        st.rerun()
    
    nota = st.text_area("Escribir nota del día:")
    if st.button("GUARDAR NOTA"):
        with open("nexus_notas.txt", "a", encoding="utf-8") as f:
            f.write(f"[{f_hoy} {h_hoy}]: {nota}\n\n")
        st.rerun()
    
    if os.path.exists("nexus_notas.txt"):
        st.markdown("### Historial de Notas")
        st.text_area("Contenido:", open("nexus_notas.txt", "r", encoding="utf-8").read(), height=300)

elif menu == "📅 CITAS":
    st.title("📅 Próximas Citas")
    df_c = pd.read_sql_query("SELECT * FROM citas", db_conn)
    if not df_c.empty: st.table(df_c)
    
    with st.form("form_citas"):
        doc = st.text_input("Especialista:").upper()
        fec = st.date_input("Fecha de la cita:")
        mot = st.text_input("Motivo:").upper()
        if st.form_submit_button("AGENDAR"):
            db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot))
            db_conn.commit(); st.rerun()

# --- 9. CONFIGURACIÓN (RESET) ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes del Sistema")
    st.error("¡Peligro! Esta acción no se puede deshacer.")
    if st.button("BORRAR TODA LA DATA DEL SISTEMA"):
        for t in ["glucosa", "finanzas", "meds", "citas"]:
            db.execute(f"DELETE FROM {t}")
        db_conn.commit(); st.success("Datos eliminados correctamente."); st.rerun()

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>SISTEMA NEXUS - PROPIEDAD DE LUIS RAFAEL QUEVEDO</p>", unsafe_allow_html=True)
