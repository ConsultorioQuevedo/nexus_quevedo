import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px

# --- 1. CONFIGURACIÓN VISUAL Y ESTILO ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .tendencia-box { padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 48px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD ---
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

# --- 3. FUNCIONES DE BASE DE DATOS Y TIEMPO ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def iniciar_db():
    conn = sqlite3.connect("nexus_pro_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    # Tabla para configuración de presupuesto
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL</h2>", unsafe_allow_html=True)
    st.info(f"📅 {f_str} | ⏰ {h_str}")
    
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.divider()
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. MÓDULO: FINANZAS (CON TERMÓMETRO Y GRÁFICO) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera Inteligente")
    
    # Obtener Presupuesto
    res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
    presupuesto_mensual = res_conf[0] if res_conf else 20000.0

    # Formulario
    with st.form("f_fin", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("MOVIMIENTO", ["GASTO", "INGRESO"])
        f_mov = c2.date_input("FECHA", value=f_obj)
        cat = st.text_input("CATEGORÍA (Comida, Salud, Casa...):").upper()
        det = st.text_input("DETALLE:").upper()
        monto = st.number_input("VALOR RD$:", min_value=0.0)
        if st.form_submit_button("REGISTRAR"):
            if monto > 0:
                m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
                db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)",
                           (f_mov.strftime("%d/%m/%Y"), mes_str, tipo, cat, det, m_real))
                db.commit(); st.rerun()

    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    
    if not df_f.empty:
        col_m1, col_m2 = st.columns(2)
        total_disp = df_f["monto"].sum()
        gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum())
        
        col_m1.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1 style='color:#2ecc71;'>RD$ {total_disp:,.2f}</h1></div>", unsafe_allow_html=True)
        
        # Termómetro de Gasto
        porcentaje = min(gastos_mes / presupuesto_mensual, 1.0)
        color_barra = "green" if porcentaje < 0.7 else "orange" if porcentaje < 0.9 else "red"
        col_m2.markdown(f"<h3>Termómetro Mensual</h3>", unsafe_allow_html=True)
        col_m2.progress(porcentaje)
        col_m2.write(f"Gastado: RD$ {gastos_mes:,.2f} de RD$ {presupuesto_mensual:,.2f}")
        if porcentaje >= 0.9: col_m2.warning("⚠️ ¡Cuidado! Está llegando al límite de su presupuesto.")

        # Gráfico de Tarta
        st.divider()
        c_t1, c_t2 = st.columns([1, 1])
        with c_t1:
            st.subheader("📊 Gastos por Categoría")
            df_gastos = df_f[df_f['tipo'] == 'GASTO']
            if not df_gastos.empty:
                fig = px.pie(df_gastos, values=abs(df_gastos['monto']), names='categoria', hole=.4, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        with c_t2:
            st.subheader("🗓️ Resumen Quincenal")
            df_f['Fecha_dt'] = pd.to_datetime(df_f['fecha'], format='%d/%m/%Y')
            df_f['Quincena'] = df_f['Fecha_dt'].apply(lambda x: f"1ra Q" if x.day <= 15 else f"2da Q")
            res_q = df_f.groupby(['Quincena', 'tipo'])['monto'].sum().unstack().fillna(0)
            st.table(res_q.style.format("RD$ {:,.2f}"))

# --- 6. MÓDULO: SALUD (INDICADOR TENDENCIA) ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud con Tendencia")
    t1, t2 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS"])

    with t1:
        # Lógica de Tendencia
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            ultimo_val = df_g.iloc[0]['valor']
            if len(df_g) > 1:
                promedio_prev = df_g.iloc[1:6]['valor'].mean() # Promedio de las últimas 5
                if ultimo_val < promedio_prev - 5: 
                    st.markdown("<div class='tendencia-box' style='background-color:#166534;'>🟢 TENDENCIA: MEJORANDO (Bajando respecto al promedio)</div>", unsafe_allow_html=True)
                elif ultimo_val > promedio_prev + 5:
                    st.markdown("<div class='tendencia-box' style='background-color:#991b1b;'>🔴 TENDENCIA: ALERTA (Subiendo respecto al promedio)</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='tendencia-box' style='background-color:#854d0e;'>🟡 TENDENCIA: ESTABLE</div>", unsafe_allow_html=True)

        with st.form("f_gluc", clear_on_submit=True):
            c1, c2 = st.columns(2)
            valor = c1.number_input("Nivel mg/dL:", min_value=0)
            mom = c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
            if st.form_submit_button("REGISTRAR LECTURA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, mom, valor))
                db.commit(); st.rerun()

        st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, title="Histórico de Glucosa", template="plotly_dark"))
        
        # Botón para exportar (Simulado con tabla simple limpia)
        if st.button("📄 GENERAR TABLA PARA MÉDICO"):
            st.subheader("REPORTE DE SALUD - NEXUS")
            st.table(df_g[['fecha', 'momento', 'valor']].head(15))

    with t2:
        st.subheader("💊 Medicinas")
        with st.form("f_med", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1, 1.5])
            n = c1.text_input("Medicamento:").upper()
            d = c2.text_input("Dosis:").upper()
            h = c3.selectbox("Frecuencia:", ["CADA 8 HORAS", "CADA 12 HORAS", "UNA VEZ AL DÍA", "SI HAY DOLOR"])
            if st.form_submit_button("AÑADIR"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT id, nombre, dosis, horario FROM medicamentos", db)
        for _, r in df_m.iterrows():
            col_a, col_b = st.columns([5, 1])
            col_a.info(f"💊 {r['nombre']} - {r['dosis']} ({r['horario']})")
            if col_b.button("Borrar", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()

# --- 7. BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora Personal")
    with st.form("f_nota", clear_on_submit=True):
        entrada = st.text_area("Nota del día:", height=100)
        if st.form_submit_button("GUARDAR"):
            with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_str}]: {entrada}\n\n")
            st.rerun()
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f:
            st.text_area("Historial de Notas:", f.read(), height=300)
    except: st.info("Sin notas.")

# --- 8. CONFIGURACIÓN (PRESUPUESTO) ---
elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes del Sistema")
    nuevo_p = st.number_input("Definir Presupuesto Mensual (RD$):", min_value=0.0, value=20000.0)
    if st.button("GUARDAR CONFIGURACIÓN"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
        db.commit()
        st.success("Presupuesto actualizado.")
