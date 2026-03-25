import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, date
import pytz
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO NEXUS (COMPLETO) ---
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
    .alert-box { background-color: #450a0a; color: #fecaca; padding: 15px; border-radius: 10px; border-left: 5px solid #ef4444; margin-bottom: 20px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 45px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SISTEMA DE SEGURIDAD ---
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
    # --- 3. FUNCIONES NÚCLEO (TIEMPO Y DB) ---
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

    # --- 4. BARRA LATERAL ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🌐 NEXUS</h2>", unsafe_allow_html=True)
        st.write(f"📅 {f_str} | ⏰ {h_str}")
        st.divider()
        menu = st.radio("NAVEGACIÓN", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
        st.divider()
        if st.button("SALIR"):
            del st.session_state["password_correct"]
            st.rerun()

    # --- 5. MÓDULO: FINANZAS (CONEXIÓN GSHEETS) ---
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
                balance = df_f["Monto"].sum()
                st.markdown(f"<div class='balance-box'><h3>DISPONIBLE</h3><h1 style='color:#e74c3c;'>RD$ {balance:,.2f}</h1></div>", unsafe_allow_html=True)
        except Exception as e: st.error(f"Error: {e}")

    # --- 6. MÓDULO: SALUD (GLUCOSA, MEDICINAS, CITAS) ---
    elif menu == "🩺 SALUD":
        st.title("🩺 Mi Salud")
        prox_citas = pd.read_sql_query("SELECT doctor, fecha FROM citas", db)
        if not prox_citas.empty:
            st.markdown(f"<div class='alert-box'>🚨 Tienes {len(prox_citas)} cita(s) agendada(s).</div>", unsafe_allow_html=True)

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
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("📄 GENERAR REPORTE"):
                    st.table(df_g[['fecha', 'momento', 'valor', 'notas']].head(20))
                if col_btn2.button("🗑️ BORRAR ÚLTIMO"):
                    db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
                st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, template="plotly_dark"), use_container_width=True)

        with t2:
            st.subheader("💊 Gestión de Medicamentos")
            with st.form("f_med", clear_on_submit=True):
                col_n, col_d, col_h = st.columns([2, 1, 1.5])
                n = col_n.text_input("Nombre:").upper()
                d = col_d.text_input("Dosis:").upper()
                h = col_h.selectbox("Horario:", ["CADA 8 HORAS", "CADA 12 HORAS", "UNA VEZ AL DÍA", "SI HAY DOLOR", "ANTES DE DORMIR"])
                if st.form_submit_button("REGISTRAR MEDICINA"):
                    if n:
                        db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                        db.commit(); st.rerun()
            
            # --- MEJORA VISUAL: TABLA HORIZONTAL ---
            df_meds = pd.read_sql_query("SELECT id, nombre AS MEDICAMENTO, dosis AS DOSIS, horario AS HORARIO FROM medicamentos", db)
            if not df_meds.empty:
                st.markdown("<div class='info-box'>Lista de medicamentos actual en formato horizontal:</div>", unsafe_allow_html=True)
                # Mostramos la tabla directamente para que no se apile
                st.dataframe(df_meds.drop(columns=['id']), use_container_width=True, hide_index=True)
                
                # Gestión de borrado por debajo de la tabla
                with st.expander("🗑️ ELIMINAR REGISTROS"):
                    med_a_borrar = st.selectbox("Seleccione medicamento para quitar:", df_meds['MEDICAMENTO'].tolist())
                    if st.button("BORRAR SELECCIONADO"):
                        db.execute("DELETE FROM medicamentos WHERE nombre = ?", (med_a_borrar,))
                        db.commit(); st.rerun()
                    if st.button("VACIAR TODA LA LISTA"):
                        db.execute("DELETE FROM medicamentos"); db.commit(); st.rerun()
            else:
                st.info("No hay medicamentos registrados.")

        with t3:
            with st.form("f_cit"):
                doc = st.text_input("Doctor:").upper()
                f_cit = st.date_input("Fecha")
                mot = st.text_input("Motivo").upper()
                if st.form_submit_button("AGENDAR CITA"):
                    if doc:
                        db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_cit), mot))
                        db.commit(); st.rerun()
            df_citas = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
            if not df_citas.empty:
                st.table(df_citas.drop(columns=['id']))
                if st.button("LIMPIAR TODAS LAS CITAS"):
                    db.execute("DELETE FROM citas"); db.commit(); st.rerun()

    # --- 7. MÓDULO: BITÁCORA ---
    elif menu == "📝 BITÁCORA":
        st.title("📝 Mis Notas")
        with st.form("f_n", clear_on_submit=True):
            txt = st.text_area("Escriba algo importante:", height=200)
            if st.form_submit_button("GUARDAR EN BITÁCORA"):
                if txt:
                    with open("notas_nexus.txt", "a") as f:
                        f.write(f"[{f_str} {h_str}]: {txt}\n---\n")
                    st.rerun()
        try:
            with open("notas_nexus.txt", "r") as f:
                st.text_area("Historial de Notas:", f.read(), height=400)
        except:
            st.info("La bitácora está vacía.")
