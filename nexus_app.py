import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px

# 1. ESTILO VISUAL "NEXUS QUEVEDO DARK" (Basado en sus capturas)
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .info-box { background-color: #0c2d48; color: #5dade2; padding: 15px; border-radius: 10px; border-left: 5px solid #2e86c1; font-size: 14px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 45px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES NÚCLEO
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y")

def iniciar_db_salud():
    conn = sqlite3.connect("nexus_salud_core.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, notas TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    conn.commit()
    return conn

# Lógica Médica Inteligente para Colores de Glucosa
def aplicar_colores_salud(row):
    valor = row['valor']
    momento = row['momento']
    estilo = ""
    
    # Caso: Después de comer (Post-Desayuno, Post-Cena, etc.)
    if "Post" in momento:
        if valor < 140: estilo = "background-color: #166534; color: white" # Normal
        elif 140 <= valor <= 199: estilo = "background-color: #854d0e; color: white" # Prediabetes
        else: estilo = "background-color: #991b1b; color: white" # Diabetes
    # Caso: Ayunas o Antes de comer
    else:
        if 70 <= valor <= 99: estilo = "background-color: #166534; color: white" # Normal
        elif 100 <= valor <= 125: estilo = "background-color: #854d0e; color: white" # Prediabetes
        elif valor >= 126: estilo = "background-color: #991b1b; color: white" # Diabetes
        else: estilo = "background-color: #4b5563; color: white" # Muy bajo (Gris)
    
    return [estilo] * len(row)

db = iniciar_db_salud()
f_rd, h_rd, mes_rd = obtener_tiempo_rd()

# 3. BARRA LATERAL
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 NEXUS</h2>", unsafe_allow_html=True)
    st.write(f"📅 **{f_rd}** | ⏰ **{h_rd}**")
    st.divider()
    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])

# --- MÓDULO 1: FINANZAS ---
if menu == "💰 FINANZAS":
    st.markdown("# 💰 CONTROL FINANCIERO QUEVEDO")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_f = conn.read(ttl=0).dropna(how="all")
        
        with st.form("f_fin", clear_on_submit=True):
            col1, col2 = st.columns(2)
            t = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
            cat = col2.text_input("CATEGORÍA").upper()
            det = st.text_input("DETALLE").upper()
            mon = st.number_input("MONTO RD$", min_value=0.0, format="%.2f")
            if st.form_submit_button("REGISTRAR"):
                if cat and mon > 0:
                    m_real = -abs(mon) if t == "GASTO" else abs(mon)
                    nueva = pd.DataFrame([{"Fecha": f_rd, "Mes": mes_rd, "Tipo": t, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                    df_final = pd.concat([df_f, nueva], ignore_index=True)
                    conn.update(data=df_final)
                    st.rerun()

        st.markdown("### 📋 MOVIMIENTOS DEL MES")
        st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)

        if not df_f.empty:
            df_f["Monto"] = pd.to_numeric(df_f["Monto"])
            ingresos = df_f[df_f["Monto"] > 0]["Monto"].sum()
            gastos = df_f[df_f["Monto"] < 0]["Monto"].abs().sum()
            balance = ingresos - gastos
            
            st.divider()
            st.write(f"🟢 **INGRESOS MES:** RD$ {ingresos:,.2f}")
            st.write(f"🔴 **GASTOS MES:** RD$ {gastos:,.2f}")
            
            st.markdown(f"""
                <div class="balance-box">
                    <h3 style='margin:0; color: #e74c3c;'>BALANCE DISPONIBLE:</h3>
                    <h1 style='margin:0; font-size: 50px; color: #e74c3c;'>RD$ {balance:,.2f}</h1>
                </div>
                <div class="info-box">
                    ℹ️ El Balance incluye el dinero que sobró de los meses anteriores.
                </div>
            """, unsafe_allow_html=True)
    except Exception as e: st.error(f"Error GSheets: {e}")

# --- MÓDULO 2: SALUD ---
elif menu == "🩺 SALUD":
    st.markdown("# 🩺 Gestor de Salud Personal")
    st.write(f"Bienvenido, **Sr. Quevedo**")
    
    tab1, tab2, tab3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas Médicas"])

    with tab1:
        st.markdown("### Registro de Glucosa")
        with st.form("f_glu", clear_on_submit=True):
            v = st.number_input("Valor mg/dL:", min_value=0)
            m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
            nt = st.text_area("Notas / Observaciones:")
            if st.form_submit_button("GUARDAR GLUCOSA"):
                if v > 0:
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor, notas) VALUES (?,?,?,?,?)", (f_rd, h_rd, m, v, nt))
                    db.commit(); st.rerun()
        
        df_g = pd.read_sql_query("SELECT fecha, hora, momento, valor FROM glucosa ORDER BY id DESC", db)
        if not df_g.empty:
            st.markdown("### Historial con Alertas de Color")
            st.dataframe(df_g.style.apply(aplicar_colores_salud, axis=1), use_container_width=True)
            
            st.markdown("### Gráfico de Evolución")
            fig = px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, template="plotly_dark", title="Tendencia de Glucosa")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### Medicamentos")
        with st.form("f_med", clear_on_submit=True):
            n = st.text_input("Nombre:").upper(); d = st.text_input("Dosis:"); h = st.text_input("Horario:")
            if st.form_submit_button("REGISTRAR MEDICAMENTO"):
                if n: db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()
        df_m = pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", db)
        st.table(df_m)
        if not df_m.empty:
            m_del = st.selectbox("Seleccione para borrar:", ["---"] + df_m['nombre'].tolist())
            if st.button("ELIMINAR"):
                if m_del != "---": db.execute("DELETE FROM medicamentos WHERE nombre = ?", (m_del,)); db.commit(); st.rerun()

    with tab3:
        st.markdown("### Citas Médicas")
        with st.form("f_citas", clear_on_submit=True):
            doc = st.text_input("Doctor:").upper(); fc = st.date_input("Fecha:"); mot = st.text_area("Motivo:")
            if st.form_submit_button("AGENDAR"):
                if doc: db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fc), mot.upper())); db.commit(); st.rerun()
        df_c = pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        st.table(df_c)

# --- MÓDULO 3: BITÁCORA ---
elif menu == "📝 BITÁCORA":
    st.markdown("# 📝 Bitácora Personal")
    with st.form("f_nota", clear_on_submit=True):
        nota = st.text_area("Escribe algo importante:", height=150)
        if st.form_submit_button("GUARDAR NOTA"):
            if nota:
                with open("notas_nexus.txt", "a") as f: f.write(f"[{f_rd} {h_rd}]: {nota}\n---\n")
                st.rerun()
    try:
        with open("notas_nexus.txt", "r") as f: st.text_area("Historial de Notas:", f.read(), height=400)
    except: st.info("Bitácora vacía.")
