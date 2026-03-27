import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
import urllib.parse
import os
from fpdf import FPDF

# --- CONFIGURACIÓN DE TIEMPO Y ZONA HORARIA ---
def obtener_fecha_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    # Retorna: Fecha texto, Hora texto, Mes-Año, Objeto fecha, Objeto completo
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date(), ahora

# --- MOTOR DE BASE DE DATOS (PROTECCIÓN DE DATOS) ---
def conectar_db():
    conn = sqlite3.connect("control_quevedo.db", check_same_thread=False)
    c = conn.cursor()
    # Creación de todas las tablas necesarias para el Sr. Quevedo
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS registro_medico (id INTEGER PRIMARY KEY, fecha TEXT, medicamento TEXT, hora_confirmada TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

# --- INTERPRETE MÉDICO (SEMAFORIZACIÓN) ---
def interpretar_salud(valor, momento):
    if "Ayunas" in momento:
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "#1b5e20"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "#fbc02d"
        else: return "ROJO", "ALTO", "#b71c1c"
    else:
        if valor < 140: return "VERDE", "NORMAL", "#1b5e20"
        elif 140 <= valor <= 199: return "AMARILLO", "ELEVADO", "#fbc02d"
        else: return "ROJO", "ALTO (REVISAR)", "#b71c1c"

# --- CONFIGURACIÓN VISUAL (MODO NOCHE PROFESIONAL) ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stMetric { background-color: #1c2128; padding: 20px; border-radius: 12px; border: 1px solid #30363d; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)
# --- SEGURIDAD: ACCESO RESTRINGIDO ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 100px; color: #58a6ff;'>🌐 NEXUS SYSTEM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Propiedad de: Luis Rafael Quevedo</p>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1,1.5,1])
    with col_login:
        with st.form("login_form"):
            user_pwd = st.text_input("Introduzca Contraseña Maestra:", type="password")
            if st.form_submit_button("INGRESAR AL SISTEMA"):
                if user_pwd == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: 
                    st.error("❌ Acceso Denegado. Contraseña incorrecta.")
    st.stop()

# --- CARGA INICIAL DE DATOS ---
db = conectar_db()
f_txt, h_txt, m_txt, f_obj, ahora_obj = obtener_fecha_rd()
hora_24 = ahora_obj.hour

# --- MENÚ LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #58a6ff;'>🌐 MENÚ NEXUS</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>📅 {f_txt}<br>⏰ {h_txt}</p>", unsafe_allow_html=True)
    st.markdown("---")
    opcion = st.radio("SECCIONES", ["🏠 INICIO", "💰 FINANZAS", "🩺 SALUD", "💊 MEDICINAS", "📅 CITAS", "📝 BITÁCORA", "⚙️ CONFIG"])
    st.markdown("---")
    if st.button("🔴 CERRAR SESIÓN"):
        del st.session_state["password_correct"]
        st.rerun()

# --- PANTALLA DE INICIO (CEREBRO MÉDICO) ---
if opcion == "🏠 INICIO":
    st.markdown(f"## Bienvenido, Sr. Quevedo")
    st.info(f"Sistema Operativo | Estado: Óptimo | {f_txt}")

    # CONFIGURACIÓN DE ALERTAS HORARIAS
    # Formato: Medicina, Hora ideal, Rango [Desde hora, Hasta hora]
    plan_medico = [
        {"med": "Jarinu Max", "hora": "07:00 AM", "rango": [6, 9]},
        {"med": "Aspirin / Pregabalina", "hora": "08:00 AM", "rango": [7, 10]},
        {"med": "Pregabalina (Tarde)", "hora": "06:00 PM", "rango": [17, 20]},
        {"med": "Insulina", "hora": "08:00 PM", "rango": [19, 22]},
        {"med": "Triglicer / Libal", "hora": "09:00 PM", "rango": [20, 23]}
    ]

    # COMPROBADOR DE ALERTAS EN TIEMPO REAL
    st.markdown("### 🔔 Alertas de Medicación")
    alertas_activas = 0
    for item in plan_medico:
        if item["rango"][0] <= hora_24 <= item["rango"][1]:
            alertas_activas += 1
            with st.container():
                st.warning(f"💊 **RECORDATORIO:** Es hora de tomar **{item['med']}** (Hora programada: {item['hora']})")
                if st.button(f"CONFIRMAR TOMA: {item['med']}", key=f"btn_{item['med']}"):
                    db.execute("INSERT INTO registro_medico (fecha, medicamento, hora_confirmada) VALUES (?, ?, ?)", 
                               (f_txt, item['med'], h_txt))
                    db.commit()
                    st.success(f"✅ Toma registrada a las {h_txt}")
                    st.rerun()
    
    if alertas_activas == 0:
        st.success("✅ No tiene medicamentos pendientes por confirmar en este rango de tiempo.")

    st.markdown("---")
    # RESUMEN RÁPIDO EN PANTALLA DE INICIO
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 📋 Últimos Registros")
        reg_data = db.execute("SELECT medicamento, hora_confirmada FROM registro_medico ORDER BY id DESC LIMIT 5").fetchall()
        if reg_data:
            df_reg = pd.DataFrame(reg_data, columns=["Medicamento", "Hora de Confirmación"])
            st.table(df_reg)
        else: st.write("No hay tomas registradas hoy.")
      # --- PANTALLA: SALUD (CONTROL DE GLUCOSA) ---
elif opcion == "🩺 SALUD":
    st.title("🩺 Control de Salud Integral")
    
    # Formulario de entrada de datos
    with st.form("form_salud", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            valor_g = st.number_input("Nivel de Glucosa (mg/dL):", min_value=0, step=1)
        with c2:
            momento_g = st.selectbox("Momento de la medición:", 
                                     ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de Dormir"])
        
        if st.form_submit_button("💾 GUARDAR MEDICIÓN"):
            if valor_g > 0:
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", 
                           (f_txt, h_txt, momento_g, valor_g))
                db.commit()
                st.success(f"✅ Registro guardado: {valor_g} mg/dL ({momento_g})")
                st.rerun()
            else: st.warning("Por favor, introduzca un valor válido.")

    # Visualización de datos y Gráficos
    df_salud = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
    if not df_salud.empty:
        st.markdown("---")
        # Gráfico de tendencia profesional
        fig = px.line(df_salud, x='fecha', y='valor', color='momento', 
                      title="📈 Tendencia de Glucosa en el Tiempo",
                      markers=True, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de registros recientes
        st.markdown("#### 📜 Historial de Mediciones")
        st.dataframe(df_salud[['fecha', 'hora', 'momento', 'valor']], use_container_width=True)
        
        if st.button("🗑️ Borrar último registro de salud"):
            db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
            db.commit(); st.rerun()

# --- PANTALLA: FINANZAS (CONTROL QUEVEDO) ---
elif opcion == "💰 FINANZAS":
    st.title("💰 Control Quevedo - Finanzas")
    
    # Obtener datos financieros
    df_fin = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    
    # Cálculos de Balance
    ingresos = df_fin[df_fin['tipo'] == 'INGRESO']['monto'].sum() if not df_fin.empty else 0
    gastos = abs(df_fin[df_fin['tipo'] == 'GASTO']['monto'].sum()) if not df_fin.empty else 0
    balance = ingresos - gastos
    
    # Métricas principales
    m1, m2, m3 = st.columns(3)
    m1.metric("INGRESOS TOTALES", f"RD$ {ingresos:,.2f}")
    m2.metric("GASTOS TOTALES", f"RD$ {gastos:,.2f}", delta=f"-{gastos:,.2f}", delta_color="inverse")
    m3.metric("DISPONIBLE (BALANCE)", f"RD$ {balance:,.2f}")

    # Formulario de registro
    with st.expander("➕ REGISTRAR NUEVO MOVIMIENTO", expanded=True):
        with st.form("form_finanzas", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                tipo_f = st.selectbox("Tipo de Movimiento:", ["GASTO", "INGRESO"])
                monto_f = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f")
            with f_col2:
                cate_f = st.text_input("Categoría (Ej: Supermercado, Farmacia, Pago):").upper()
                deta_f = st.text_input("Detalle específico:").upper()
            
            if st.form_submit_button("📝 REGISTRAR EN LIBRO"):
                if monto_f > 0:
                    monto_final = -monto_f if tipo_f == "GASTO" else monto_f
                    db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                               (f_txt, m_txt, tipo_f, cate_f, deta_f, monto_final))
                    db.commit()
                    st.success("✅ Movimiento registrado con éxito.")
                    st.rerun()
    
    # Tabla de transacciones
    if not df_fin.empty:
        st.markdown("#### 📑 Últimos Movimientos")
        st.dataframe(df_fin[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
# --- PANTALLA: MEDICINAS (CATÁLOGO PERSONAL) ---
elif opcion == "💊 MEDICINAS":
    st.title("💊 Catálogo de Medicamentos")
    st.markdown("Gestione aquí la lista de medicinas que tiene en su botiquín.")
    
    # Formulario para añadir medicinas
    with st.expander("➕ AÑADIR NUEVA MEDICINA AL CATÁLOGO"):
        with st.form("form_med_cat", clear_on_submit=True):
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                nom_med = st.text_input("Nombre de la Medicina:").upper()
            with col_m2:
                dos_med = st.text_input("Dosis (Ej: 500mg, 1 tableta):").upper()
            with col_m3:
                hor_med = st.text_input("Frecuencia (Ej: Cada 8 horas):").upper()
            
            if st.form_submit_button("💾 REGISTRAR MEDICINA"):
                if nom_med:
                    db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", 
                               (nom_med, dos_med, hor_med))
                    db.commit()
                    st.success(f"✅ {nom_med} añadida al catálogo.")
                    st.rerun()

    # Mostrar lista de medicinas
    df_meds = pd.read_sql_query("SELECT * FROM medicamentos", db)
    if not df_meds.empty:
        st.markdown("---")
        for _, fila in df_meds.iterrows():
            with st.container():
                st.markdown(f"""
                <div style='background-color: #1c2128; padding: 15px; border-radius: 10px; border-left: 5px solid #58a6ff; margin-bottom: 10px;'>
                    <h4 style='margin:0;'>💊 {fila['nombre']}</h4>
                    <p style='margin:0; color: #8b949e;'>Dosis: {fila['dosis']} | Frecuencia: {fila['horario']}</p>
                </div>
                """, unsafe_allow_html=True)
        
        if st.button("🗑️ Borrar toda la lista de medicinas"):
            db.execute("DELETE FROM medicamentos")
            db.commit(); st.rerun()

# --- PANTALLA: CITAS ---
elif opcion == "📅 CITAS":
    st.title("📅 Agenda de Citas Médicas")
    
    with st.form("form_citas", clear_on_submit=True):
        c_doc = st.text_input("Doctor / Especialidad:").upper()
        c_fec = st.date_input("Fecha de la Cita:")
        c_mot = st.text_area("Motivo o Instrucciones:").upper()
        
        if st.form_submit_button("📅 AGENDAR CITA"):
            db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", 
                       (c_doc, str(c_fec), c_mot))
            db.commit()
            st.success("✅ Cita agendada correctamente.")
            st.rerun()

    df_citas = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
    if not df_citas.empty:
        st.markdown("---")
        st.table(df_citas[['doctor', 'fecha', 'motivo']])
        if st.button("🗑️ Limpiar agenda"):
            db.execute("DELETE FROM citas"); db.commit(); st.rerun()

# --- PANTALLA: BITÁCORA ---
elif opcion == "📝 BITÁCORA":
    st.title("📝 Notas y Observaciones")
    st.info("Utilice este espacio para anotar síntomas, dudas para el médico o recordatorios generales.")
    
    nota_nueva = st.text_area("Escriba su nota aquí:", height=150)
    if st.button("💾 GUARDAR NOTA EN ARCHIVO"):
        if nota_nueva:
            with open("bitacora_quevedo.txt", "a", encoding="utf-8") as f:
                f.write(f"FECHA: {f_txt} {h_txt}\nNOTA: {nota_nueva}\n{'-'*30}\n")
            st.success("✅ Nota guardada físicamente en el servidor.")
        else: st.warning("Escriba algo antes de guardar.")

# --- PANTALLA: CONFIGURACIÓN ---
elif opcion == "⚙️ CONFIG":
    st.title("⚙️ Configuración del Sistema")
    st.markdown(f"**Usuario:** Sr. Quevedo")
    st.markdown(f"**Versión del Sistema:** NEXUS PRO v4.2")
    st.markdown("---")
    
    st.subheader("🛠️ Mantenimiento")
    if st.button("🔄 Reiniciar Aplicación"):
        st.rerun()
    
    if st.checkbox("Mostrar ID de registros (Avanzado)"):
        st.write("Esta opción permite ver los códigos internos de la base de datos.")

    st.markdown("---")
    st.caption("Desarrollado para el control integral de salud y finanzas personales.")
