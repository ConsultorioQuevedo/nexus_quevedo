import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
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
    if valor <= 130: return "background-color: #dcfce7; color: #166534"
    return "background-color: #fef9c3; color: #854d0e"

# Inicialización
db = iniciar_db_salud()
f_rd, h_rd, mes_rd, objeto_fecha = obtener_tiempo_rd()

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
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_f = conn.read(ttl=0).dropna(how="all")
        
        if not df_f.empty:
            df_f["Monto"] = pd.to_numeric(df_f["Monto"])
            total = df_f["Monto"].sum()
            
            # --- NUEVA SECCIÓN: RESUMEN SEMANAL ---
            st.subheader("📊 Análisis de Gastos")
            col_met1, col_met2 = st.columns(2)
            col_met1.metric("BALANCE TOTAL", f"RD$ {total:,.2f}")
            
            # Cálculo de la última semana
            df_f['Fecha_dt'] = pd.to_datetime(df_f['Fecha'], format="%d/%m/%Y")
            hace_una_semana = objeto_fecha.replace(tzinfo=None) - timedelta(days=7)
            gastos_semana = df_f[(df_f['Monto'] < 0) & (df_f['Fecha_dt'] >= hace_una_semana)]
            total_semana = gastos_semana['Monto'].abs().sum()
            
            col_met2.metric("GASTOS ÚLTIMOS 7 DÍAS", f"RD$ {total_semana:,.2f}", delta_color="inverse")
            
            if not gastos_semana.empty:
                with st.expander("👁️ Ver detalle de gastos de esta semana"):
                    st.table(gastos_semana[['Fecha', 'Categoría', 'Detalle', 'Monto']].sort_values(by='Fecha_dt', ascending=False))

            # Gráfico Circular
            df_gastos_total = df_f[df_f["Monto"] < 0].copy()
            if not df_gastos_total.empty:
                df_gastos_total["Monto"] = df_gastos_total["Monto"].abs()
                fig = px.pie(df_gastos_total, values='Monto', names='Categoría', title='DISTRIBUCIÓN TOTAL DE GASTOS')
                st.plotly_chart(fig, use_container_width=True)

        with st.expander("📝 REGISTRAR NUEVO MOVIMIENTO", expanded=True):
            with st.form("f_fin", clear_on_submit=True):
                col1, col2, col3, col4 = st.columns([1,2,2,1])
                t = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
                cat = col2.text_input("CATEGORÍA").upper()
                det = col3.text_input("DETALLE").upper()
                mon = col4.number_input("MONTO RD$", min_value=0.0)
                if st.form_submit_button("GUARDAR EN LA NUBE"):
                    if cat and mon > 0:
                        m_real = -abs(mon) if t == "GASTO" else abs(mon)
                        nueva = pd.DataFrame([{"Fecha": f_rd, "Mes": mes_rd, "Tipo": t, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                        df_final = pd.concat([df_f.drop(columns=['Fecha_dt'], errors='ignore'), nueva], ignore_index=True)
                        conn.update(data=df_final)
                        st.success("✅ Sincronizado")
                        st.rerun()
                    else:
                        st.warning("⚠️ Completa Categoría y Monto.")

        st.subheader("📑 Historial Completo")
        st.dataframe(df_f.drop(columns=['Fecha_dt'], errors='ignore').sort_index(ascending=False), use_container_width=True)
        
        with st.expander("🗑️ ELIMINAR REGISTRO"):
            if not df_f.empty:
                idx = st.number_input("Número de fila a borrar:", min_value=0, max_value=len(df_f)-1, step=1)
                if st.button("ELIMINAR DE GOOGLE SHEETS"):
                    df_f = df_f.drop(df_f.index[idx]).drop(columns=['Fecha_dt'], errors='ignore')
                    conn.update(data=df_f)
                    st.rerun()
    except Exception as e:
        st.error(f"⚠️ Error: {e}")

# --- MÓDULO 2: SALUD (SQLITE LOCAL) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Gestión de Salud")
    t1, t2, t3 = st.tabs(["🩸 Glucosa", "💊 Medicación", "📅 Citas Médicas"])

    with t1:
        with st.form("f_glu", clear_on_submit=True):
            v = st.number_input("Nivel (mg/dL):", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
            if st.form_submit_button("REGISTRAR LECTURA"):
                if v > 0:
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_rd, h_rd, m, v))
                    db.commit()
                    st.rerun()
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.dataframe(df_g.style.applymap(color_glucosa, subset=['valor']), use_container_width=True)

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_med", clear_on_submit=True):
                n = st.text_input("Medicamento:").upper()
                d = st.text_input("Dosis:")
                h = st.text_input("Horario:")
                if st.form_submit_button("AGREGAR A LISTA"):
                    if n:
                        db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                        db.commit()
                        st.rerun()
        with c2:
            df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
            if not df_m.empty:
                st.table(df_m[['nombre', 'dosis', 'horario']])
                opciones = ["--- Seleccione para borrar ---"] + df_m['nombre'].tolist()
                m_del = st.selectbox("Borrar medicamento:", opciones)
                if st.button("ELIMINAR SELECCIONADO"):
                    if m_del != "--- Seleccione para borrar ---":
                        db.execute("DELETE FROM medicamentos WHERE nombre = ?", (m_del,))
                        db.commit()
                        st.rerun()

    with t3:
        with st.form("f_citas", clear_on_submit=True):
            doc = st.text_input("Doctor / Especialidad:").upper()
            f_c = st.date_input("Fecha de la Cita:")
            mot = st.text_area("Motivo:")
            if st.form_submit_button("AGENDAR CITA"):
                if doc:
                    db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_c), mot.upper()))
                    db.commit()
                    st.rerun()
        df_c = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        if not df_c.empty:
            st.dataframe(df_c, use_container_width=True)
            id_c = st.number_input("ID de cita a cancelar:", min_value=1)
            if st.button("BORRAR CITA"):
                db.execute("DELETE FROM citas WHERE id = ?", (id_c,))
                db.commit()
                st.rerun()

# --- MÓDULO 3: BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Notas Personales")
    with st.form("f_nota", clear_on_submit=True):
        nota = st.text_area("Escribe algo importante:", height=150)
        if st.form_submit_button("GUARDAR NOTA"):
            if nota:
                with open("notas_nexus.txt", "a") as f: 
                    f.write(f"[{f_rd} {h_rd}]: {nota}\n---\n")
                st.rerun()
    
    if st.button("LIMPIAR TODO"):
        open("notas_nexus.txt", "w").close()
        st.rerun()
        
    try:
        with open("notas_nexus.txt", "r") as f: 
            st.text_area("Historial de Notas:", f.read(), height=300)
    except: 
        st.info("No hay notas guardadas.")
