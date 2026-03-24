import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import pytz
import plotly.express as px

# 1. CONFIGURACIÓN DE IDENTIDAD Y ESTILO PROFESIONAL
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🩺")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    [data-testid="stSidebar"] { background-image: linear-gradient(#1e3a8a, #0f172a); color: white; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid #1e40af; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #1e40af; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton > button { border-radius: 10px; height: 3em; background-color: #1e40af; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #ffffff; border-radius: 5px; padding: 10px 20px; }
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
    if valor <= 130: return "background-color: #dcfce7; color: #166534"
    return "background-color: #fef9c3; color: #854d0e"

# Inicialización
db = iniciar_db_salud()
f_rd, h_rd, mes_rd, objeto_fecha = obtener_tiempo_rd()

# 3. BARRA LATERAL
with st.sidebar:
    st.markdown("<h1 style='color: white; text-align: center;'>NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #cbd5e1;'>{f_rd} | {h_rd}</p>", unsafe_allow_html=True)
    st.divider()
    menu = st.radio("SELECCIONE MÓDULO:", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    st.divider()
    st.info("SISTEMA ACTIVO v2.0")

# --- MÓDULO 1: FINANZAS ---
if menu == "💰 FINANZAS":
    st.title("💰 Centro de Control Financiero")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_f = conn.read(ttl=0).dropna(how="all")
        
        if not df_f.empty:
            df_f["Monto"] = pd.to_numeric(df_f["Monto"])
            total = df_f["Monto"].sum()
            
            # Dashboard Finanzas
            m1, m2, m3 = st.columns(3)
            m1.metric("DISPONIBLE TOTAL", f"RD$ {total:,.2f}")
            
            df_f['Fecha_dt'] = pd.to_datetime(df_f['Fecha'], format="%d/%m/%Y")
            hace_7 = objeto_fecha.replace(tzinfo=None) - timedelta(days=7)
            gastos_7 = df_f[(df_f['Monto'] < 0) & (df_f['Fecha_dt'] >= hace_7)]
            total_7 = gastos_7['Monto'].abs().sum()
            
            m2.metric("GASTOS SEMANALES", f"RD$ {total_7:,.2f}", delta="-Semana")
            
            g_max = df_f[df_f['Monto'] < 0]['Monto'].min()
            m3.metric("MAYOR GASTO REGISTRADO", f"RD$ {abs(g_max) if not pd.isna(g_max) else 0:,.2f}")

            # Gráficos
            c_izq, c_der = st.columns(2)
            with c_izq:
                df_gastos_pie = df_f[df_f["Monto"] < 0].copy()
                if not df_gastos_pie.empty:
                    df_gastos_pie["Monto"] = df_gastos_pie["Monto"].abs()
                    fig_pie = px.sunburst(df_gastos_pie, path=['Categoría', 'Tipo'], values='Monto', title='DISTRIBUCIÓN DE GASTOS')
                    st.plotly_chart(fig_pie, use_container_width=True)
            with c_der:
                st.subheader("📝 Nuevo Registro")
                with st.form("f_fin", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    tipo = c1.selectbox("TIPO", ["GASTO", "INGRESO"])
                    monto = c2.number_input("MONTO RD$", min_value=0.0)
                    cat = st.text_input("CATEGORÍA (Ej: COMIDA, SALUD)").upper()
                    det = st.text_input("DETALLE (Ej: SUPERMERCADO)").upper()
                    if st.form_submit_button("GUARDAR MOVIMIENTO"):
                        if cat and monto > 0:
                            m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
                            nueva = pd.DataFrame([{"Fecha": f_rd, "Mes": mes_rd, "Tipo": tipo, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                            df_final = pd.concat([df_f.drop(columns=['Fecha_dt'], errors='ignore'), nueva], ignore_index=True)
                            conn.update(data=df_final)
                            st.rerun()

        st.subheader("📑 Historial de Transacciones")
        st.dataframe(df_f.drop(columns=['Fecha_dt'], errors='ignore').sort_index(ascending=False), use_container_width=True)
    except Exception as e:
        st.error(f"Error conexión: {e}")

# --- MÓDULO 2: SALUD (DISEÑO ROBUSTO) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Panel de Salud Nexus")
    
    # 1. Dashboard de Salud arriba
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
    
    col_s1, col_s2, col_s3 = st.columns(3)
    if not df_g.empty:
        promedio = df_g['valor'].mean()
        col_s1.metric("PROMEDIO GLUCOSA", f"{promedio:.1f} mg/dL")
        ultima = df_g['valor'].iloc[0]
        col_s2.metric("ÚLTIMA LECTURA", f"{ultima} mg/dL")
        estado = "ESTABLE" if 70 <= ultima <= 140 else "REVISAR"
        col_s3.metric("ESTADO ACTUAL", estado)
    else:
        st.info("Registra tu primera lectura para ver estadísticas.")

    # 2. Gráfico de Evolución
    if not df_g.empty:
        st.subheader("📈 Evolución de Glucosa")
        df_g_sorted = df_g.sort_values(by='id')
        fig_glu = px.line(df_g_sorted, x='fecha', y='valor', color='momento', markers=True, 
                         title='Histórico de Niveles', color_discrete_sequence=px.colors.qualitative.Set1)
        st.plotly_chart(fig_glu, use_container_width=True)

    # 3. Pestañas de Gestión
    t1, t2, t3 = st.tabs(["🩸 Registrar Glucosa", "💊 Mi Medicación", "📅 Agenda Médica"])

    with t1:
        with st.form("f_glu", clear_on_submit=True):
            col_g1, col_g2 = st.columns(2)
            v = col_g1.number_input("Valor (mg/dL):", min_value=0)
            m = col_g2.selectbox("Momento del día:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
            if st.form_submit_button("GUARDAR LECTURA"):
                if v > 0:
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_rd, h_rd, m, v))
                    db.commit(); st.rerun()
        st.dataframe(df_g.style.applymap(color_glucosa, subset=['valor']), use_container_width=True)

    with t2:
        c_m1, c_m2 = st.columns([1, 2])
        with c_m1:
            st.subheader("📝 Agregar")
            with st.form("f_med", clear_on_submit=True):
                n = st.text_input("Nombre:").upper()
                d = st.text_input("Dosis:")
                h = st.text_input("Horario:")
                if st.form_submit_button("AGREGAR"):
                    if n:
                        db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                        db.commit(); st.rerun()
        with c_m2:
            st.subheader("📋 Lista Actual")
            df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
            if not df_m.empty:
                st.table(df_m[['nombre', 'dosis', 'horario']])
                opciones = ["--- Seleccione para borrar ---"] + df_m['nombre'].tolist()
                m_del = st.selectbox("Borrar:", opciones)
                if st.button("ELIMINAR MEDICAMENTO"):
                    if m_del != "--- Seleccione para borrar ---":
                        db.execute("DELETE FROM medicamentos WHERE nombre = ?", (m_del,))
                        db.commit(); st.rerun()

    with t3:
        with st.form("f_citas", clear_on_submit=True):
            c_c1, c_c2 = st.columns(2)
            doc = c_c1.text_input("Doctor:").upper()
            f_c = c_c2.date_input("Fecha:")
            mot = st.text_area("Motivo de consulta:")
            if st.form_submit_button("AGENDAR CITA"):
                if doc:
                    db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_c), mot.upper()))
                    db.commit(); st.rerun()
        df_c = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        st.dataframe(df_c, use_container_width=True)

# --- MÓDULO 3: BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Notas y Pendientes")
    with st.form("f_nota", clear_on_submit=True):
        nota = st.text_area("Escriba aquí...", height=150)
        if st.form_submit_button("GUARDAR NOTA"):
            if nota:
                with open("notas_nexus.txt", "a") as f: f.write(f"[{f_rd} {h_rd}]: {nota}\n---\n")
                st.rerun()
    
    col_n1, col_n2 = st.columns([1, 5])
    if col_n1.button("BORRAR TODO"):
        open("notas_nexus.txt", "w").close(); st.rerun()
    
    try:
        with open("notas_nexus.txt", "r") as f: st.text_area("Historial de Notas:", f.read(), height=400)
    except: st.info("Bitácora vacía.")
