
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px

# 1. CONFIGURACIÓN DE IDENTIDAD Y ESTILO PROFESIONAL
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-image: linear-gradient(#1e3a8a, #0f172a); color: white; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #1e40af; font-weight: bold; }
    div.stButton > button { border-radius: 8px; font-weight: bold; width: 100%; transition: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES NÚCLEO (TIEMPO Y BASES DE DATOS)
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y")

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
    if valor <= 130: return "background-color: #dcfce7; color: #166534"
    return "background-color: #fef9c3; color: #854d0e"

# Inicialización
db = iniciar_db_salud()
f_rd, h_rd, mes_rd = obtener_tiempo_rd()

# 3. BARRA LATERAL (CONTROL TOTAL)
with st.sidebar:
    st.markdown("<h1 style='color: white; text-align: center;'>NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    st.write(f"📅 **{f_rd}**")
    st.write(f"⏰ **{h_rd}**")
    st.divider()
    menu = st.radio("SELECCIONE MÓDULO:", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    st.divider()
    st.success("SISTEMA CONECTADO")

# --- MÓDULO 1: FINANZAS (GOOGLE SHEETS) ---
if menu == "💰 FINANZAS":
    st.title("💰 Control Financiero (Google Sheets)")
    try:
        # CONEXIÓN BLINDADA
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_f = conn.read(ttl=0).dropna(how="all")
        
        # Dashboard de Métricas
        if not df_f.empty:
            df_f["Monto"] = pd.to_numeric(df_f["Monto"])
            total = df_f["Monto"].sum()
            c1, c2 = st.columns([2, 1])
            c1.metric("BALANCE TOTAL DISPONIBLE", f"RD$ {total:,.2f}")
            
            # Gráfico de Gastos
            df_gastos = df_f[df_f["Monto"] < 0].copy()
            if not df_gastos.empty:
                df_gastos["Monto"] = df_gastos["Monto"].abs()
                fig = px.pie(df_gastos, values='Monto', names='Categoría', title='DISTRIBUCIÓN DE GASTOS')
                st.plotly_chart(fig, use_container_width=True)

        # Formulario de Registro
        with st.expander("📝 REGISTRAR NUEVO MOVIMIENTO", expanded=True):
            with st.form("f_fin", clear_on_submit=True):
                col1, col2, col3, col4 = st.columns([1,2,2,1])
                t = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
                cat = col2.text_input("CATEGORÍA").upper()
                det = col3.text_input("DETALLE").upper()
                mon = col4.number_input("MONTO RD$", min_value=0.0)
                if st.form_submit_button("GUARDAR EN LA NUBE"):
                    m_real = -abs(mon) if t == "GASTO" else abs(mon)
                    nueva = pd.DataFrame([{"Fecha": f_rd, "Mes": mes_rd, "Tipo": t, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                    df_final = pd.concat([df_f, nueva], ignore_index=True)
                    conn.update(data=df_final)
                    st.success("✅ Datos sincronizados")
                    st.rerun()

        # Tabla y Borrado
        st.subheader("📊 Historial de Transacciones")
        st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
        
        with st.expander("🗑️ ELIMINAR REGISTRO INCORRECTO"):
            idx = st.number_input("Número de fila a borrar:", min_value=0, max_value=len(df_f)-1 if not df_f.empty else 0, step=1)
            if st.button("ELIMINAR DE GOOGLE SHEETS"):
                df_f = df_f.drop(df_f.index[idx])
                conn.update(data=df_f)
                st.rerun()
    except:
        st.error("⚠️ Error de comunicación con Google Sheets. Revisa tu secrets.toml")

# --- MÓDULO 2: SALUD (SQLITE LOCAL) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Gestión de Salud y Citas")
    t1, t2, t3 = st.tabs(["🩸 Glucosa", "💊 Medicación", "📅 Citas Médicas"])

    with t1: # GLUCOSA
        with st.form("f_glu"):
            v = st.number_input("Nivel (mg/dL):")
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
            if st.form_submit_button("REGISTRAR LECTURA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_rd, h_rd, m, v))
                db.commit(); st.rerun()
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.dataframe(df_g.style.applymap(color_glucosa, subset=['valor']), use_container_width=True)
            if st.button("BORRAR ÚLTIMA LECTURA"):
                db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                db.commit(); st.rerun()

    with t2: # MEDICACIÓN
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_med"):
                n = st.text_input("Medicamento:").upper()
                d = st.text_input("Dosis:")
                h = st.text_input("Horario:")
                if st.form_submit_button("AGREGAR A LISTA"):
                    db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                    db.commit(); st.rerun()
        with c2:
            df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
            st.table(df_m[['nombre', 'dosis', 'horario']])
            if not df_m.empty:
                m_del = st.selectbox("Seleccione para borrar:", df_m['nombre'].tolist())
                if st.button("ELIMINAR MEDICAMENTO"):
                    db.execute("DELETE FROM medicamentos WHERE nombre = ?", (m_del,))
                    db.commit(); st.rerun()

    with t3: # CITAS MÉDICAS
        with st.form("f_citas"):
            doc = st.text_input("Doctor / Especialidad:").upper()
            f_c = st.date_input("Fecha de la Cita:")
            mot = st.text_area("Motivo:")
            if st.form_submit_button("AGENDAR CITA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_c), mot.upper()))
                db.commit(); st.rerun()
        df_c = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        st.dataframe(df_c, use_container_width=True)
        if not df_c.empty:
            id_c = st.number_input("ID de cita a cancelar:", min_value=1)
            if st.button("BORRAR CITA"):
                db.execute("DELETE FROM citas WHERE id = ?", (id_c,))
                db.commit(); st.rerun()

# --- MÓDULO 3: BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora de Notas")
    nota = st.text_area("Escribe algo importante:", height=150)
    if st.button("GUARDAR NOTA"):
        with open("notas_nexus.txt", "a") as f: f.write(f"[{f_rd} {h_rd}]: {nota}\n---\n")
        st.success("Nota guardada localmente.")
    if st.button("LIMPIAR BITÁCORA"):
        open("notas_nexus.txt", "w").close()
        st.rerun()
    try:
        with open("notas_nexus.txt", "r") as f: st.text_area("Historial:", f.read(), height=300)
    except: st.info("Bitácora vacía.")
