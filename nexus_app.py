import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import sqlite3
from datetime import datetime, date
import pytz
import plotly.express as px

# --- CONFIGURACIÓN Y ESTILO NEXUS PROFESIONAL ---
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
    .report-print { background-color: white !important; color: black !important; padding: 30px; border-radius: 10px; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 45px; }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

# --- SEGURIDAD ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([1,2,1])
        with col_b:
            with st.form("login"):
                pwd = st.text_input("Contraseña Maestra:", type="password")
                if st.form_submit_button("ACCEDER AL SISTEMA"):
                    if pwd == "admin123": # <--- CAMBIE AQUÍ SU CLAVE
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("❌ Acceso Denegado")
        return False
    return True

if check_password():
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

    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🌐 NEXUS</h2>", unsafe_allow_html=True)
        st.write(f"📅 {f_str} | ⏰ {h_str}")
        st.divider()
        menu = st.radio("NAVEGACIÓN", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
        st.divider()
        if st.button("SALIR"):
            del st.session_state["password_correct"]
            st.rerun()

    # --- FINANZAS ---
    if menu == "💰 FINANZAS":
        st.title("💰 Control Financiero")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_f = conn.read(ttl=0).dropna(how="all")
            
            with st.form("f_fin", clear_on_submit=True):
                c1, c2, c3 = st.columns([1,1,1])
                tipo = c1.selectbox("TIPO", ["GASTO", "INGRESO"])
                # Sugerencias de categorías para mayor rapidez
                cat = c2.selectbox("CATEGORÍA", ["ALIMENTACIÓN", "COMBUSTIBLE", "SERVICIOS", "SALUD", "HOGAR", "OTROS"])
                fecha_sel = c3.date_input("FECHA", value=f_obj)
                det = st.text_input("DETALLE (OPCIONAL)").upper()
                mon = st.number_input("MONTO RD$", min_value=0.0, step=100.0)
                
                if st.form_submit_button("REGISTRAR MOVIMIENTO"):
                    if mon > 0:
                        m_real = -abs(mon) if tipo == "GASTO" else abs(mon)
                        nueva = pd.DataFrame([{"Fecha": fecha_sel.strftime("%d/%m/%Y"), "Mes": mes_str, "Tipo": tipo, "Categoría": cat, "Detalle": det, "Monto": float(m_real)}])
                        conn.update(data=pd.concat([df_f, nueva], ignore_index=True))
                        st.success("Sincronizado con la nube"); st.rerun()

            st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)

            if not df_f.empty:
                df_f["Monto"] = pd.to_numeric(df_f["Monto"])
                ing, gas = df_f[df_f["Monto"] > 0]["Monto"].sum(), df_f[df_f["Monto"] < 0]["Monto"].abs().sum()
                st.markdown(f"<div class='balance-box'><h3 style='margin:0; color:#e74c3c;'>DISPONIBLE</h3><h1 style='margin:0; font-size:50px; color:#e74c3c;'>RD$ {ing-gas:,.2f}</h1></div>", unsafe_allow_html=True)
        except Exception as e: st.error(f"Error: {e}")

    # --- SALUD ---
    elif menu == "🩺 SALUD":
        st.title("🩺 Mi Salud")
        
        # Alerta Inteligente
        prox_citas = pd.read_sql_query("SELECT doctor, fecha FROM citas", db)
        if not prox_citas.empty:
            st.markdown(f"<div class='alert-box'>🚨 <b>RECORDATORIO:</b> Tienes {len(prox_citas)} cita(s) en tu historial. Revisa la pestaña de Citas.</div>", unsafe_allow_html=True)

        t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

        with t1:
            with st.form("f_glu", clear_on_submit=True):
                col_g1, col_g2 = st.columns(2)
                v = col_g1.number_input("Valor (mg/dL):", min_value=0)
                m = col_g2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Antes de Cena", "Post-Cena"])
                nt = st.text_input("Notas rápidas:")
                if st.form_submit_button("GUARDAR MEDICIÓN"):
                    if v > 0:
                        db.execute("INSERT INTO glucosa (fecha, hora, momento, valor, notas) VALUES (?,?,?,?,?)", (f_str, h_str, m, v, nt))
                        db.commit(); st.rerun()
            
            df_g = pd.read_sql_query("SELECT id, fecha, momento, valor, notas FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                st.dataframe(df_g.drop(columns=['id']).style.apply(aplicar_colores_salud, axis=1), use_container_width=True)
                
                c_rep, c_del = st.columns(2)
                if c_rep.button("📄 GENERAR REPORTE MÉDICO"):
                    st.markdown(f"<div class='report-print'><h2>HISTORIAL DE GLUCOSA - SR. QUEVEDO</h2><p>Reporte al: {f_str}</p>", unsafe_allow_html=True)
                    st.table(df_g[['fecha', 'momento', 'valor', 'notas']].head(20))
                    st.info("💡 Consejo: Guarde como PDF usando (Ctrl+P)")
                
                if c_del.button("🗑️ BORRAR ÚLTIMO"):
                    db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
                
                st.plotly_chart(px.line(df_g.iloc[::-1], x='fecha', y='valor', markers=True, template="plotly_dark"), use_container_width=True)

        with t2:
            with st.form("f_med", clear_on_submit=True):
                n = st.text_input("Nombre del Medicamento:").upper()
                d, h = st.text_input("Dosis:"), st.text_input("Horario:")
                if st.form_submit_button("REGISTRAR"):
                    if n: db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h)); db.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", db))

        with t3:
            with st.form("f_cit"):
                doc = st.text_input("Doctor:").upper(); f_cit = st.date_input("Fecha"); mot = st.text_input("Motivo")
                if st.form_submit_button("AGENDAR CITA"):
                    db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(f_cit), mot)); db.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas", db))
            if st.button("VACIAR TODAS LAS CITAS"):
                db.execute("DELETE FROM citas"); db.commit(); st.rerun()

    # --- BITÁCORA ---
    elif menu == "📝 BITÁCORA":
        st.title("📝 Mis Notas")
        with st.form("f_n", clear_on_submit=True):
            txt = st.text_area("Nota del día:", height=150)
            if st.form_submit_button("GUARDAR"):
                if txt:
                    with open("notas_nexus.txt", "a") as f: f.write(f"[{f_str}]: {txt}\n---\n")
                    st.rerun()
        try:
            with open("notas_nexus.txt", "r") as f: st.text_area("Historial:", f.read(), height=400)
        except: st.info("Sin notas.")
