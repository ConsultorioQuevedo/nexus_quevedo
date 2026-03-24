import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import pytz
import plotly.express as px

# 1. CONFIGURACIÓN DE IDENTIDAD Y ESTILO
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🩺")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    [data-testid="stSidebar"] { background-image: linear-gradient(#1e3a8a, #0f172a); color: white; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #1e40af; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #1e40af; font-weight: bold; }
    .stButton > button { border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES NÚCLEO
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora

def iniciar_db_salud():
    conn = sqlite3.connect("nexus_salud_core.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

def color_glucosa(valor):
    if valor < 70: return "background-color: #fee2e2; color: #991b1b"
    if valor <= 140: return "background-color: #dcfce7; color: #166534"
    return "background-color: #fef9c3; color: #854d0e"

# Inicialización
db = iniciar_db_salud()
f_rd, h_rd, mes_rd, objeto_fecha = obtener_tiempo_rd()

# 3. BARRA LATERAL
with st.sidebar:
    st.markdown("<h1 style='color: white; text-align: center;'>NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio("SELECCIONE MÓDULO:", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    st.divider()
    st.info("v2.1 - Con Botones de Borrado")

# --- MÓDULO 1: FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Control Financiero")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_f = conn.read(ttl=0).dropna(how="all")
        
        if not df_f.empty:
            df_f["Monto"] = pd.to_numeric(df_f["Monto"])
            m1, m2 = st.columns(2)
            m1.metric("BALANCE TOTAL", f"RD$ {df_f['Monto'].sum():,.2f}")
            
            df_f['Fecha_dt'] = pd.to_datetime(df_f['Fecha'], format="%d/%m/%Y")
            hace_7 = objeto_fecha.replace(tzinfo=None) - timedelta(days=7)
            total_7 = df_f[(df_f['Monto'] < 0) & (df_f['Fecha_dt'] >= hace_7)]['Monto'].abs().sum()
            m2.metric("GASTOS 7 DÍAS", f"RD$ {total_7:,.2f}")

        with st.expander("📝 REGISTRAR MOVIMIENTO", expanded=False):
            with st.form("f_fin", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([1,1,2,1])
                tipo = c1.selectbox("TIPO", ["GASTO", "INGRESO"])
                monto = c2.number_input("MONTO RD$", min_value=0.0)
                cat = c3.text_input("CATEGORÍA").upper()
                det = c4.text_input("DETALLE").upper()
                if st.form_submit_button("GUARDAR"):
                    if cat and monto > 0:
                        m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
                        nueva = pd.DataFrame([{"Fecha": f_rd, "Mes": mes_rd, "Tipo": tipo, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                        df_final = pd.concat([df_f.drop(columns=['Fecha_dt'], errors='ignore'), nueva], ignore_index=True)
                        conn.update(data=df_final)
                        st.rerun()

        st.subheader("📑 Historial")
        st.dataframe(df_f.drop(columns=['Fecha_dt'], errors='ignore').sort_index(ascending=False), use_container_width=True)
        
        with st.expander("🗑️ BORRAR REGISTRO FINANCIERO"):
            if not df_f.empty:
                f_del = st.number_input("Fila a borrar:", min_value=0, max_value=len(df_f)-1, step=1)
                if st.button("BORRAR DE GOOGLE SHEETS"):
                    df_f = df_f.drop(df_f.index[f_del]).drop(columns=['Fecha_dt'], errors='ignore')
                    conn.update(data=df_f)
                    st.rerun()
    except Exception as e: st.error(f"Error: {e}")

# --- MÓDULO 2: SALUD (DISEÑO ÁPERO CON BORRADO) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Panel de Salud Nexus")
    
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
    
    # Dashboard
    col_s1, col_s2, col_s3 = st.columns(3)
    if not df_g.empty:
        col_s1.metric("PROMEDIO", f"{df_g['valor'].mean():.1f}")
        col_s2.metric("ÚLTIMA", f"{df_g['valor'].iloc[0]}")
        col_s3.metric("ESTADO", "ESTABLE" if 70 <= df_g['valor'].iloc[0] <= 140 else "REVISAR")

        st.subheader("📈 Evolución")
        fig_glu = px.line(df_g.sort_values(by='id'), x='fecha', y='valor', color='momento', markers=True)
        st.plotly_chart(fig_glu, use_container_width=True)

    t1, t2, t3 = st.tabs(["🩸 Glucosa", "💊 Medicación", "📅 Citas"])

    with t1: # GLUCOSA
        with st.form("f_glu", clear_on_submit=True):
            c_g1, c_g2 = st.columns(2)
            v = c_g1.number_input("Valor:", min_value=0)
            m = c_g2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
            if st.form_submit_button("REGISTRAR"):
                if v > 0:
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_rd, h_rd, m, v))
                    db.commit(); st.rerun()
        
        if not df_g.empty:
            st.dataframe(df_g.style.applymap(color_glucosa, subset=['valor']), use_container_width=True)
            if st.button("🗑️ BORRAR ÚLTIMA LECTURA DE GLUCOSA"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                db.commit(); st.rerun()

    with t2: # MEDICACIÓN
        c_m1, c_m2 = st.columns([1, 2])
        with c_m1:
            with st.form("f_med", clear_on_submit=True):
                n = st.text_input("Medicamento:").upper()
                d = st.text_input("Dosis:")
                h = st.text_input("Horario:")
                if st.form_submit_button("AGREGAR"):
                    if n:
                        db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                        db.commit(); st.rerun()
        with c_m2:
            df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
            if not df_m.empty:
                st.table(df_m[['nombre', 'dosis', 'horario']])
                m_del = st.selectbox("Seleccione para borrar:", ["---"] + df_m['nombre'].tolist())
                if st.button("🗑️ ELIMINAR MEDICAMENTO"):
                    if m_del != "---":
                        db.execute("DELETE FROM medicamentos WHERE nombre = ?", (m_del,))
                        db.commit(); st.rerun()

    with t3: # CITAS
        with st.form("f_citas", clear_on_submit=True):
            doc = st.text_input("Doctor:").upper()
            f_c = st.date_input("Fecha:")
            mot = st.text_area("Motivo:")
            if st.form_submit_button("AGENDAR"):
                if doc:
                    db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_c), mot.upper()))
                    db.commit(); st.rerun()
        df_c = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        if not df_c.empty:
            st.dataframe(df_c, use_container_width=True)
            id_c = st.number_input("ID de cita a borrar:", min_value=1)
            if st.button("🗑️ CANCELAR CITA"):
                db.execute("DELETE FROM citas WHERE id = ?", (id_c,))
                db.commit(); st.rerun()

# --- MÓDULO 3: BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Notas")
    with st.form("f_nota", clear_on_submit=True):
        nota = st.text_area("Escriba...", height=150)
        if st.form_submit_button("GUARDAR"):
            if nota:
                with open("notas_nexus.txt", "a") as f: f.write(f"[{f_rd}]: {nota}\n---\n")
                st.rerun()
    if st.button("🗑️ LIMPIAR BITÁCORA"):
        open("notas_nexus.txt", "w").close(); st.rerun()
    try:
        with open("notas_nexus.txt", "r") as f: st.text_area("Historial:", f.read(), height=300)
    except: st.info("Vacía.")
