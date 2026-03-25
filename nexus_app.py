import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import pytz
import plotly.express as px

# --- 1. CONFIGURACIÓN VISUAL (FULL) ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .info-box { background-color: #0c2d48; color: #5dade2; padding: 15px; border-radius: 10px; border-left: 5px solid #2e86c1; margin-bottom: 10px; }
    .alert-box { background-color: #450a0a; color: #fecaca; padding: 15px; border-radius: 10px; border-left: 5px solid #ef4444; margin-bottom: 20px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 48px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEGURIDAD DE ACCESO ---
def check_password():
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
        return False
    return True

if check_password():
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
        conn.commit()
        return conn

    def color_glucosa(row):
        v, m = row['valor'], row['momento']
        if "Post" in m:
            color = "#166534" if v < 140 else "#854d0e" if v <= 199 else "#991b1b"
        else:
            color = "#166534" if 70 <= v <= 99 else "#854d0e" if 100 <= v <= 125 else "#991b1b"
        return [f"background-color: {color}; color: white"] * len(row)

    db = iniciar_db()
    f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

    # --- 4. BARRA LATERAL (SIDEBAR) CON RECORDATORIO ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🌐 NEXUS CONTROL</h2>", unsafe_allow_html=True)
        st.info(f"📅 {f_str} | ⏰ {h_str}")
        
        # NUEVO: Recordatorio Sintomático de Citas
        st.markdown("### 🔔 RECORDATORIO DE CITAS")
        df_citas_aviso = pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        if not df_citas_aviso.empty:
            for _, r in df_citas_aviso.head(3).iterrows():
                st.markdown(f"""
                <div class='info-box'>
                <b>Dr:</b> {r['doctor']}<br>
                <b>Fecha:</b> {r['fecha']}<br>
                <b>Motivo:</b> {r['motivo']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("No hay citas pendientes.")

        st.divider()
        menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
        st.divider()
        if st.button("CERRAR SESIÓN"):
            del st.session_state["password_correct"]; st.rerun()

    # --- 5. MÓDULO: FINANZAS (CON RESUMEN QUINCENAL) ---
    if menu == "💰 FINANZAS":
        st.title("💰 Gestión Financiera")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_f = conn.read(ttl=0).dropna(how="all")
            
            with st.form("f_fin", clear_on_submit=True):
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("MOVIMIENTO", ["GASTO", "INGRESO"])
                f_gasto = c2.date_input("FECHA", value=f_obj)
                cat = st.text_input("CATEGORÍA (Ej: Comida, Renta):").upper()
                det = st.text_input("DETALLE:").upper()
                monto = st.number_input("VALOR RD$:", min_value=0.0)
                if st.form_submit_button("REGISTRAR EN GOOGLE SHEETS"):
                    m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
                    nueva_fila = pd.DataFrame([{"Fecha": f_gasto.strftime("%d/%m/%Y"), "Mes": mes_str, "Tipo": tipo, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                    conn.update(data=pd.concat([df_f, nueva_fila], ignore_index=True))
                    st.success("✅ Datos sincronizados"); st.rerun()

            st.subheader("Registros Recientes")
            st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
            
            if not df_f.empty:
                df_f["Monto"] = pd.to_numeric(df_f["Monto"])
                total = df_f["Monto"].sum()
                st.markdown(f"<div class='balance-box'><h3>DISPONIBLE TOTAL</h3><h1 style='color:#2ecc71;'>RD$ {total:,.2f}</h1></div>", unsafe_allow_html=True)
                
                # NUEVO: Resumen Quincenal
                st.divider()
                st.subheader("📊 Resumen por Quincenas")
                df_f['Fecha_dt'] = pd.to_datetime(df_f['Fecha'], format='%d/%m/%Y')
                df_f['Quincena'] = df_f['Fecha_dt'].apply(lambda x: f"1ra Q ({x.strftime('%B')})" if x.day <= 15 else f"2da Q ({x.strftime('%B')})")
                
                resumen_q = df_f.groupby(['Quincena', 'Tipo'])['Monto'].sum().unstack().fillna(0)
                st.table(resumen_q.style.format("RD$ {:,.2f}"))
                
        except: st.error("Conecte Google Sheets en el dashboard.")

    # --- 6. MÓDULO: SALUD (TODO EL CÓDIGO RESTAURADO) ---
    elif menu == "🩺 SALUD":
        st.title("🩺 Control de Salud NEXUS")
        t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

        with t1:
            with st.form("f_gluc"):
                c1, c2 = st.columns(2)
                valor = c1.number_input("Nivel mg/dL:", min_value=0)
                momento = c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Comida", "Post-Almuerzo", "Post-Cena"])
                notas_glu = st.text_input("Observaciones:").upper()
                if st.form_submit_button("GUARDAR EN HISTORIAL"):
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor, notas) VALUES (?,?,?,?,?)", (f_str, h_str, momento, valor, notas_glu))
                    db.commit(); st.rerun()
            
            df_g = pd.read_sql_query("SELECT id, fecha, hora, momento, valor, notas FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                st.subheader("Histórico de Medidas")
                st.dataframe(df_g.drop(columns=['id']).style.apply(color_glucosa, axis=1), use_container_width=True)
                
                c_rep, c_del = st.columns(2)
                if c_rep.button("📄 GENERAR TABLA DE REPORTE"):
                    st.table(df_g.head(20))
                if c_del.button("🗑️ ELIMINAR ÚLTIMO REGISTRO"):
                    db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
                
                st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, title="Tendencia de Glucosa", template="plotly_dark"))

        with t2:
            st.subheader("💊 Medicamentos Actuales")
            with st.form("f_med", clear_on_submit=True):
                col_n, col_d, col_h = st.columns([2, 1, 1.5])
                n_med = col_n.text_input("Medicamento:").upper()
                d_med = col_d.text_input("Dosis:").upper()
                h_med = col_h.selectbox("Frecuencia:", ["CADA 8 HORAS", "CADA 12 HORAS", "UNA VEZ AL DÍA", "SI HAY DOLOR", "ANTES DE DORMIR"])
                if st.form_submit_button("REGISTRAR MEDICINA"):
                    if n_med:
                        db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n_med, d_med, h_med))
                        db.commit(); st.rerun()
            
            df_meds = pd.read_sql_query("SELECT id, nombre AS MEDICAMENTO, dosis AS DOSIS, horario AS HORARIO FROM medicamentos", db)
            if not df_meds.empty:
                st.dataframe(df_meds.drop(columns=['id']), use_container_width=True, hide_index=True)
                with st.expander("🗑️ ELIMINAR MEDICAMENTO"):
                    m_del = st.selectbox("Seleccione para borrar:", df_meds['MEDICAMENTO'].tolist())
                    if st.button("CONFIRMAR BORRADO"):
                        db.execute("DELETE FROM medicamentos WHERE nombre = ?", (m_del,)); db.commit(); st.rerun()
                    if st.button("VACIAR TODA LA LISTA"):
                        db.execute("DELETE FROM medicamentos"); db.commit(); st.rerun()

        with t3:
            st.subheader("📅 Agenda Médica")
            with st.form("f_citas"):
                doc = st.text_input("Doctor/Especialidad:").upper()
                f_cita = st.date_input("Fecha de Cita")
                mot = st.text_input("Motivo de la visita:").upper()
                if st.form_submit_button("AGENDAR"):
                    db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_cita), mot))
                    db.commit(); st.rerun()
            
            df_c = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
            if not df_c.empty:
                st.table(df_c.drop(columns=['id']))
                if st.button("LIMPIAR TODAS LAS CITAS"):
                    db.execute("DELETE FROM citas"); db.commit(); st.rerun()

    # --- 7. MÓDULO: BITÁCORA (TXT HISTORIAL COMPLETO) ---
    elif menu == "📝 BITÁCORA":
        st.title("📝 Bitácora de Eventos")
        with st.form("f_nota", clear_on_submit=True):
            entrada = st.text_area("Nueva anotación:", height=150)
            if st.form_submit_button("GUARDAR EN ARCHIVO"):
                if entrada:
                    with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                        f.write(f"[{f_str} {h_str}]: {entrada}\n" + "-"*40 + "\n")
                    st.rerun()
        
        st.subheader("📖 Historial de Notas")
        try:
            with open("nexus_notas.txt", "r", encoding="utf-8") as f:
                notas_hist = f.read()
                st.text_area("Contenido:", notas_hist, height=450)
        except:
            st.info("No hay notas registradas todavía.")
