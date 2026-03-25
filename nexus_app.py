import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, date
import pytz
import plotly.express as px

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

# --- ESTILO CSS PROFESIONAL (MODO OSCURO) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { background-color: #1f2937; padding: 20px; border-radius: 15px; border: 1px solid #30363d; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .alert-box { background-color: #450a0a; color: #fecaca; padding: 15px; border-radius: 10px; border-left: 5px solid #ef4444; margin-bottom: 20px; }
    
    /* Botones Estilo Nexus */
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 40px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    
    /* Etiquetas de datos */
    .data-label { color: #8b949e; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- SEGURIDAD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
        _, col_b, _ = st.columns([1,2,1])
        with col_b:
            with st.form("login"):
                pwd = st.text_input("Contraseña Maestra:", type="password")
                if st.form_submit_button("ACCEDER AL SISTEMA"):
                    if pwd == "admin123":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else: st.error("❌ Acceso Denegado")
        return False
    return True

if check_password():
    # --- FUNCIONES CORE ---
    def obtener_tiempo_rd():
        zona = pytz.timezone('America/Santo_Domingo')
        ahora = datetime.now(zona)
        return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

    def iniciar_db():
        conn = sqlite3.connect("nexus_salud.db", check_same_thread=False)
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

    # --- NAVEGACIÓN ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🌐 NEXUS</h2>", unsafe_allow_html=True)
        st.info(f"📅 {f_str}\n\n⏰ {h_str}")
        st.divider()
        menu = st.radio("MÓDULOS", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
        if st.button("SALIR"):
            del st.session_state["password_correct"]; st.rerun()

    # --- MÓDULO: FINANZAS ---
    if menu == "💰 FINANZAS":
        st.title("💰 Control Financiero")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_f = conn.read(ttl=0).dropna(how="all")
            
            with st.form("f_fin", clear_on_submit=True):
                c1, c2 = st.columns(2)
                tipo = c1.selectbox("OPERACIÓN", ["GASTO", "INGRESO"])
                fecha_sel = c2.date_input("FECHA", value=f_obj)
                cat = st.text_input("CATEGORÍA (Ej: Comida, Casa):").upper()
                det = st.text_input("DETALLE (Opcional):").upper()
                monto = st.number_input("MONTO RD$", min_value=0.0, step=100.0)
                
                if st.form_submit_button("REGISTRAR MOVIMIENTO"):
                    if monto > 0 and cat:
                        m_real = -abs(monto) if tipo == "GASTO" else abs(monto)
                        nueva_fila = pd.DataFrame([{"Fecha": fecha_sel.strftime("%d/%m/%Y"), "Mes": mes_str, "Tipo": tipo, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                        conn.update(data=pd.concat([df_f, nueva_fila], ignore_index=True))
                        st.success("✅ Registro Exitoso"); st.rerun()

            st.subheader("Historial de Transacciones")
            st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
            
            if not df_f.empty:
                balance = pd.to_numeric(df_f["Monto"]).sum()
                st.markdown(f"<div class='balance-box'><h3>DISPONIBLE ACTUAL</h3><h1 style='color:#2ecc71;'>RD$ {balance:,.2f}</h1></div>", unsafe_allow_html=True)
        except Exception as e: st.error(f"Error de conexión: {e}")

    # --- MÓDULO: SALUD ---
    elif menu == "🩺 SALUD":
        st.title("🩺 Gestión de Salud")
        t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

        with t1:
            st.subheader("Control de Glucemia")
            with st.form("f_glucosa", clear_on_submit=True):
                c1, c2 = st.columns(2)
                valor = c1.number_input("Nivel (mg/dL):", min_value=0, step=1)
                momento = c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
                notas_g = st.text_input("Notas:").upper()
                if st.form_submit_button("GUARDAR MEDICIÓN"):
                    if valor > 0:
                        db.execute("INSERT INTO glucosa (fecha, hora, momento, valor, notas) VALUES (?,?,?,?,?)", (f_str, h_str, momento, valor, notas_g))
                        db.commit(); st.rerun()
            
            df_g = pd.read_sql_query("SELECT id, fecha, momento, valor, notas FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                st.dataframe(df_g.drop(columns=['id']).style.apply(color_glucosa, axis=1), use_container_width=True)
                st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, template="plotly_dark", title="Tendencia de Glucosa"))

        with t2:
            st.subheader("Medicamentos Activos")
            with st.form("f_med", clear_on_submit=True):
                c1, c2, c3 = st.columns([2, 1, 1.5])
                n_med = c1.text_input("Nombre:").upper()
                d_med = c2.text_input("Dosis:").upper()
                h_med = c3.selectbox("Frecuencia:", ["UNA VEZ AL DÍA", "CADA 8 HORAS", "CADA 12 HORAS", "SI HAY DOLOR"])
                if st.form_submit_button("AÑADIR A LA LISTA"):
                    if n_med:
                        db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n_med, d_med, h_med))
                        db.commit(); st.rerun()
            
            # --- LISTADO HORIZONTAL ---
            df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
            if not df_m.empty:
                st.write("---")
                # Cabeceras
                h_col1, h_col2, h_col3, h_col4 = st.columns([3, 2, 3, 1.5])
                h_col1.markdown("<span class='data-label'>MEDICAMENTO</span>", unsafe_allow_html=True)
                h_col2.markdown("<span class='data-label'>DOSIS</span>", unsafe_allow_html=True)
                h_col3.markdown("<span class='data-label'>HORARIO</span>", unsafe_allow_html=True)
                h_col4.markdown("<span class='data-label'>ACCIÓN</span>", unsafe_allow_html=True)
                
                for _, fila in df_m.iterrows():
                    r1, r2, r3, r4 = st.columns([3, 2, 3, 1.5])
                    r1.write(fila['nombre'])
                    r2.write(fila['dosis'])
                    r3.write(fila['horario'])
                    if r4.button("ELIMINAR", key=f"del_{fila['id']}"):
                        db.execute("DELETE FROM medicamentos WHERE id=?", (fila['id'],))
                        db.commit(); st.rerun()
                
                if st.button("🗑️ LIMPIAR TODA LA LISTA"):
                    db.execute("DELETE FROM medicamentos"); db.commit(); st.rerun()

        with t3:
            st.subheader("Próximas Citas Médicas")
            with st.form("f_citas"):
                doc = st.text_input("Doctor/Especialidad:").upper()
                f_c = st.date_input("Fecha:")
                mot = st.text_input("Motivo:").upper()
                if st.form_submit_button("AGENDAR"):
                    db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_c), mot))
                    db.commit(); st.rerun()
            
            df_c = pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
            st.table(df_c)

    # --- MÓDULO: BITÁCORA ---
    elif menu == "📝 BITÁCORA":
        st.title("📝 Notas y Bitácora")
        with st.form("f_nota", clear_on_submit=True):
            nota_t = st.text_area("Escriba su nota aquí:", height=150)
            if st.form_submit_button("GUARDAR NOTA"):
                if nota_t:
                    with open("nexus_bitacora.txt", "a", encoding="utf-8") as f:
                        f.write(f"{f_str} {h_str}\n{nota_t}\n" + "-"*30 + "\n")
                    st.rerun()
        
        try:
            with open("nexus_bitacora.txt", "r", encoding="utf-8") as f:
                st.text_area("Historial de Notas:", f.read(), height=400)
        except FileNotFoundError: st.info("Bitácora vacía.")
