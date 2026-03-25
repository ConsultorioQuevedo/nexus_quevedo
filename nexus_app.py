import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io  # <-- Nueva herramienta para la descarga mágica

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .tendencia-box { padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 20px; border: 1px solid #ffffff33; }
    div.stButton > button { background-color: #1f2937; color: white; border: 1px solid #30363d; border-radius: 8px; width: 100%; font-weight: bold; height: 48px; }
    .btn-borrar > div > button { background-color: #441111 !important; color: #ff9999 !important; border: 1px solid #662222 !important; height: 35px !important; font-size: 12px !important; }
    .stDownloadButton > button { background-color: #064e3b !important; color: #a7f3d0 !important; border: 1px solid #065f46 !important; }
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

# --- 3. FUNCIONES DE TIEMPO Y DB ---
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
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

db = iniciar_db()
f_str, h_str, mes_str, f_obj = obtener_tiempo_rd()

# CARGA DE CONFIGURACIÓN
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 20000.0

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🌐 CONTROL</h2>", unsafe_allow_html=True)
    st.info(f"📅 {f_str} | ⏰ {h_str}")
    
    df_citas_side = pd.read_sql_query("SELECT doctor, fecha FROM citas WHERE fecha >= date('now') ORDER BY fecha ASC LIMIT 2", db)
    if not df_citas_side.empty:
        st.markdown("📅 **PRÓXIMAS CITAS:**")
        for _, r in df_citas_side.iterrows():
            st.caption(f"🩺 {r['doctor']} - {r['fecha']}")

    menu = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.divider()
    if st.button("CERRAR SESIÓN"):
        del st.session_state["password_correct"]; st.rerun()

# --- 5. FINANZAS (CON EXCEL) ---
if menu == "💰 FINANZAS":
    st.title("💰 Gestión Financiera")
    
    with st.form("f_fin", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("TIPO", ["GASTO", "INGRESO"])
        f_mov = c2.date_input("FECHA", value=f_obj)
        cat = st.text_input("CATEGORÍA:").upper()
        det = st.text_input("DETALLE:").upper()
        monto = st.number_input("MONTO RD$:", min_value=0.0)
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
        
        porc = min(gastos_mes / presupuesto_mensual, 1.0) if presupuesto_mensual > 0 else 0
        col_m2.markdown(f"<h3>Presupuesto: {porc*100:.0f}%</h3>", unsafe_allow_html=True)
        col_m2.progress(porc)
        col_m2.write(f"Gastado este mes: RD$ {gastos_mes:,.2f}")

        # SECCIÓN DE ACCIONES (BORRAR Y EXCEL)
        c_acc1, c_acc2 = st.columns(2)
        with c_acc1:
            st.markdown("<div class='btn-borrar'>", unsafe_allow_html=True)
            if st.button("🗑️ BORRAR ÚLTIMO"):
                db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with c_acc2:
            # BOTÓN DE EXCEL SIN COMPLICACIONES
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_f.to_excel(writer, index=False, sheet_name='Finanzas')
            st.download_button(
                label="📥 DESCARGAR EXCEL",
                data=output.getvalue(),
                file_name=f"Finanzas_Nexus_{mes_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        df_gastos = df_f[df_f['tipo'] == 'GASTO']
        if not df_gastos.empty:
            st.plotly_chart(px.pie(df_gastos, values=abs(df_gastos['monto']), names='categoria', hole=.4, template="plotly_dark"), use_container_width=True)

# [El resto de las secciones Salud, Bitácora y Config se mantienen igual que la versión anterior]
# --- 6. SALUD ---
elif menu == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    t1, t2, t3 = st.tabs(["🩸 GLUCOSA", "💊 MEDICINAS", "📅 CITAS"])

    with t1:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
        if len(df_g) >= 2:
            ultimo = df_g.iloc[0]['valor']
            anterior = df_g.iloc[1:6]['valor'].mean()
            if ultimo < anterior - 5: st.markdown("<div class='tendencia-box' style='background-color:#166534;'>🟢 TENDENCIA: MEJORANDO</div>", unsafe_allow_html=True)
            elif ultimo > anterior + 5: st.markdown("<div class='tendencia-box' style='background-color:#991b1b;'>🔴 TENDENCIA: ALERTA (SUBIENDO)</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='tendencia-box' style='background-color:#854d0e;'>🟡 TENDENCIA: ESTABLE</div>", unsafe_allow_html=True)

        with st.form("f_gluc", clear_on_submit=True):
            c1, c2 = st.columns(2)
            val = c1.number_input("Valor mg/dL:", min_value=0)
            mom = c2.selectbox("Momento:", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena"])
            if st.form_submit_button("GUARDAR"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, mom, val))
                db.commit(); st.rerun()
        
        c_p1, c_p2 = st.columns([3,1])
        if c_p1.button("📄 GENERAR TABLA PARA MÉDICO"):
            st.table(df_g[['fecha', 'momento', 'valor']].head(15))
        
        st.markdown("<div class='btn-borrar'>", unsafe_allow_html=True)
        if c_p2.button("🗑️ BORRAR ÚLTIMA LECTURA"):
            db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)"); db.commit(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.sort_values('id'), x='fecha', y='valor', markers=True, template="plotly_dark", title="HISTÓRICO"), use_container_width=True)

    with t2:
        with st.form("f_med", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1, 1.5])
            n = c1.text_input("MEDICINA:").upper()
            d = c2.text_input("DOSIS:").upper()
            h = c3.selectbox("HORARIO:", ["UNA VEZ AL DÍA", "CADA 8 HORAS", "CADA 12 HORAS", "CADA 24 HORAS", "SI HAY DOLOR"])
            if st.form_submit_button("AÑADIR"):
                if n:
                    db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n, d, h))
                    db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT id, nombre, dosis, horario FROM medicamentos", db)
        for _, r in df_m.iterrows():
            col_a, col_b = st.columns([5,1])
            col_a.info(f"💊 {r['nombre']} - {r['dosis']} ({r['horario']})")
            if col_b.button("Borrar", key=f"m_{r['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (r['id'],)); db.commit(); st.rerun()

    with t3:
        st.subheader("🗓️ Agenda de Citas")
        with st.form("f_citas", clear_on_submit=True):
            doc = st.text_input("DOCTOR / CLÍNICA:").upper()
            fec = st.date_input("FECHA:")
            mot = st.text_input("MOTIVO:").upper()
            if st.form_submit_button("AGENDAR"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (doc, str(fec), mot))
                db.commit(); st.rerun()
        
        df_c = pd.read_sql_query("SELECT id, doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        for _, r in df_c.iterrows():
            c1, c2 = st.columns([5,1])
            c1.write(f"📅 **{r['fecha']}** | {r['doctor']} ({r['motivo']})")
            if c2.button("Eliminar", key=f"c_{r['id']}"):
                db.execute("DELETE FROM citas WHERE id=?", (r['id'],)); db.commit(); st.rerun()

elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora")
    with st.form("f_nota", clear_on_submit=True):
        entrada = st.text_area("Escriba aquí su anotación:", height=150)
        if st.form_submit_button("GUARDAR NOTA"):
            if entrada.strip():
                with open("nexus_notas.txt", "a", encoding="utf-8") as f:
                    f.write(f"[{f_str} {h_str}]: {entrada}\n\n")
                st.success("Nota guardada."); st.rerun()
    try:
        with open("nexus_notas.txt", "r", encoding="utf-8") as f:
            st.text_area("Historial:", f.read(), height=400)
    except FileNotFoundError: st.info("Bitácora lista.")

elif menu == "⚙️ CONFIG":
    st.title("⚙️ Ajustes")
    nuevo_p = st.number_input("Presupuesto Mensual (RD$):", min_value=0.0, value=float(presupuesto_mensual))
    if st.button("ACTUALIZAR"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
        db.commit(); st.success("Actualizado.")
