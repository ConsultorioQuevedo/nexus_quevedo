import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, date
import pytz
import plotly.express as px

# --- CONFIGURACIÓN Y ESTILO NEXUS ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .alert-box { background-color: #450a0a; color: #fecaca; padding: 15px; border-radius: 10px; border-left: 5px solid #ef4444; margin-bottom: 20px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 45px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    
    /* Ajuste para que las filas de medicamentos se vean siempre horizontales */
    .med-row { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        padding: 10px; 
        border-bottom: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE SEGURIDAD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([1,2,1])
        with col_b:
            with st.form("login"):
                pwd = st.text_input("Contraseña Maestra:", type="password")
                if st.form_submit_button("ACCEDER AL SISTEMA"):
                    if pwd == "admin123":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("❌ Acceso Denegado")
        return False
    return True

if check_password():
    # --- FUNCIONES NÚCLEO ---
    def obtener_tiempo_rd():
        zona = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(zona)
        return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

    def iniciar_db_salud():
        conn = sqlite3.connect("nexus_salud_core.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, notas TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
        cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
        conn.commit()
        return conn

    def aplicar_colores_salud(row):
        v, m = row['valor'], row['momento']
        if "Post" in m:
            estilo = "#166534" if v < 140 else "#854d0e" if v <= 199 else "#991b1b"
        else:
            estilo = "#166534" if 70 <= v <= 99 else "#854d0e" if 100 <= v <= 125 else "#991b1b" if v >= 126 else "#4b5563"
        return [f"background-color: {estilo}; color: white"] * len(row)

    db = iniciar_db_salud()
    f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🌐 NEXUS</h2>", unsafe_allow_html=True)
        st.write(f"📅 {f_str} | ⏰ {h_str}")
        st.divider()
        menu = st.radio("NAVEGACIÓN", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
        st.divider()
        if st.button("SALIR"):
            del st.session_state["password_correct"]
            st.rerun()

    # --- MÓDULO 1: FINANZAS ---
    if menu == "💰 FINANZAS":
        st.title("💰 Control Financiero")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_f = conn.read(ttl=0).dropna(how="all")
            with st.form("f_fin", clear_on_submit=True):
                col1, col2 = st.columns(2)
                tipo = col1.selectbox("TIPO", ["GASTO", "INGRESO"])
                fecha_sel = col2.date_input("FECHA", value=f_obj)
                cat_libre = st.text_input("CATEGORÍA:").upper()
                det_libre = st.text_input("DETALLE:").upper()
                monto = st.number_input("MONTO RD$", min_value=0.0, step=1.0, format="%f")
                if st.form_submit_button("REGISTRAR"):
                    if monto > 0 and cat_libre:
                        m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
                        nueva = pd.DataFrame([{"Fecha": fecha_sel.strftime("%d/%m/%Y"), "Mes": mes_str, "Tipo": tipo, "Categoría": cat_libre, "Detalle": det_libre, "Monto": float(m_real)}])
                        conn.update(data=pd.concat([df_f, nueva], ignore_index=True))
                        st.success("Guardado correctamente"); st.rerun()
            st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
            if not df_f.empty:
                df_f["Monto"] = pd.to_numeric(df_f["Monto"])
                st.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1 style='color:#e74c3c;'>RD$ {df_f['Monto'].sum():,.2f}</h1></div>", unsafe_allow_html=True)
        except Exception as e: st.error(f"Error: {e}")

    # --- MÓDULO 2: SALUD ---
    elif menu == "🩺 SALUD":
        st.title("🩺 Mi Salud")
        t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

        with t1:
            with st.form("f_glu", clear_on_submit=True):
                v = st.number_input("Valor mg/dL:", min_value=0, step=1, format="%d")
                m = st.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
                notas_g = st.text_input("Notas:").upper()
                if st.form_submit_button("GUARDAR MEDICIÓN"):
                    if v > 0:
                        db.execute("INSERT INTO glucosa (fecha, hora, momento, valor, notas) VALUES (?,?,?,?,?)", (f_str, h_str, m, v, notas_g))
                        db.commit(); st.rerun()
            df_g = pd.read_sql_query("SELECT id, fecha, momento, valor, notas FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                st.dataframe(df_g.drop(columns=['id']).style.apply(aplicar_colores_salud, axis=1), use_container_width=True)

        with t2:
            st.subheader("💊 Gestión de Medicamentos")
            with st.form("f_med", clear_on_submit=True):
                c1, c2, c3 = st.columns([2,1,1.5])
                n = c1.text_input("Nombre:").upper()
                d = c2.text_input("Dosis:").upper()
                h = c3.selectbox("Horario:", ["CADA 4 HORAS", "CADA 6 HORAS", "CADA 8 HORAS", "CADA 12 HORAS", "UNA VEZ AL DÍA", "SOLO SI HAY DOLOR"])
                if st.form_submit_button("REGISTRAR MEDICINA"):
                    if n:
                        db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                        db.commit(); st.rerun()
            
            # --- LISTADO TOTALMENTE HORIZONTAL ---
            df_meds = pd.read_sql_query("SELECT id, nombre, dosis, horario FROM medicamentos", db)
            if not df_meds.empty:
                st.write("---")
                # Cabecera fija
                head1, head2, head3, head4 = st.columns([2.5, 1.5, 2, 1])
                head1.caption("NOMBRE")
                head2.caption("DOSIS")
                head3.caption("HORARIO")
                head4.caption("ACCIÓN")
                
                for _, row in df_meds.iterrows():
                    # Usamos st.columns dentro del loop para forzar la horizontalidad
                    r1, r2, r3, r4 = st.columns([2.5, 1.5, 2, 1])
                    r1.write(row['nombre'])
                    r2.write(row['dosis'])
                    r3.write(row['horario'])
                    if r4.button("BORRAR", key=f"del_{row['id']}"):
                        db.execute("DELETE FROM medicamentos WHERE id=?", (row['id'],))
                        db.commit(); st.rerun()
                
                st.write("---")
                if st.button("🗑️ VACIAR TODA LA LISTA"):
                    db.execute("DELETE FROM medicamentos"); db.commit(); st.rerun()

        with t3:
            with st.form("f_cit"):
                doc = st.text_input("Doctor:").upper(); f_cit = st.date_input("Fecha"); mot = st.text_input("Motivo").upper()
                if st.form_submit_button("AGENDAR CITA"):
                    if doc:
                        db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_cit), mot))
                        db.commit(); st.rerun()
            df_citas = pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
            st.table(df_citas)

    # --- MÓDULO 3: BITÁCORA ---
    elif menu == "📝 BITÁCORA":
        st.title("📝 Mis Notas")
        with st.form("f_n", clear_on_submit=True):
            txt = st.text_area("Nota:", height=200)
            if st.form_submit_button("GUARDAR"):
                if txt:
                    with open("notas_nexus.txt", "a") as f: f.write(f"[{f_str}]: {txt}\n---\n")
                    st.rerun()
        try:
            with open("notas_nexus.txt", "r") as f: st.text_area("Historial:", f.read(), height=400)
        except: st.info("Vacío.")
