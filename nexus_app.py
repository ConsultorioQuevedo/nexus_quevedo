import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
from fpdf import FPDF
import os
import urllib.parse

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #00d4ff !important; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GESTIÓN DE TIEMPO (ZONA HORARIA RD)
# ==========================================
def obtener_tiempo():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return {
        "fecha": ahora.strftime("%d/%m/%Y"),
        "hora": ahora.strftime("%I:%M %p"),
        "mes": ahora.strftime("%B").upper(),
        "solo_fecha": ahora.date()
    }

tiempo = obtener_tiempo()

# ==========================================
# 3. BASE DE DATOS REFORZADA (NEXUS PRO)
# ==========================================
def inicializar_db():
    conn = sqlite3.connect("sistema_quevedo_pro.db", check_same_thread=False)
    c = conn.cursor()

    # FINANZAS (Añadido campo 'presupuesto')
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, mes TEXT, tipo TEXT, 
                  categoria TEXT, monto REAL, presupuesto REAL, nota TEXT)''') 

    # GLUCOSA
    c.execute('''CREATE TABLE IF NOT EXISTS glucosa
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, hora TEXT, momento TEXT, 
                  valor INTEGER, estado TEXT, notas TEXT)''')

    # MEDICAMENTOS (BOTIQUÍN)
    c.execute('''CREATE TABLE IF NOT EXISTS medicamentos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nombre TEXT, dosis TEXT, horario TEXT, 
                  stock_inicial INTEGER, stock_actual INTEGER)''') 
    
    # AGENDA UNIFICADA
    c.execute('''CREATE TABLE IF NOT EXISTS agenda
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT, hora TEXT, asunto TEXT, lugar TEXT, doctor TEXT)''')

    # BITÁCORA MÉDICA
    c.execute('''CREATE TABLE IF NOT EXISTS registro_medico
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, medicamento TEXT, hora_toma TEXT, 
                  cumplimiento TEXT)''')

    conn.commit()
    return conn

conn = inicializar_db()

# ==========================================
# 4. CONTROL DE ACCESO (SIMPLIFICADO)
# ==========================================
# Entra directo sin contraseña como pidió el usuario.
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = True

# ==========================================
# 5. BARRA LATERAL (NAVEGACIÓN ROBUSTA)
# ==========================================
with st.sidebar:
    st.title("🚀 NEXUS QUEVEDO")
    st.write(f"📅 {tiempo['fecha']}")
    st.write(f"⏰ {tiempo['hora']}")
    st.markdown("---")
    
    # Menú limpio sin errores de indentación
    menu = st.radio("SELECCIONE MÓDULO:", 
                    ["🏠 Dashboard", "📅 Agenda", "💊 Botiquín", "💰 Finanzas", "🩺 Glucosa & Salud", "📝 Bitácora"])
    
    st.markdown("---")
    if st.button("🔄 Refrescar Sistema"):
        st.rerun()

# ==========================================
# 6. FUNCIONES DE EXPORTACIÓN (PROTEGIDAS)
# ==========================================
def enviar_whatsapp(mensaje):
    msg_encoded = urllib.parse.quote(mensaje)
    # Su número por defecto para envío rápido
    url = f"https://wa.me/18290000000?text={msg_encoded}"
    return url

# El código continúa abajo con las funciones de los módulos...
# ==========================================
# 7. SECCIÓN: GLUCOSA & SALUD (NEXUS AI)
# ==========================================
if menu == "🩺 Glucosa & Salud":
    st.title("🩺 Control de Glucosa - Sr. Quevedo")
    st.markdown(f"**Paciente:** Luis Rafael Quevedo | **Fecha:** {tiempo['fecha']}")

    # --- 1. ENTRADA DE DATOS ---
    with st.expander("📝 REGISTRAR NUEVA LECTURA", expanded=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            valor_g = st.number_input("Nivel (mg/dL):", min_value=0, max_value=500, step=1)
        with c2:
            momento_g = st.selectbox("Momento:", ["Ayunas", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
        with c3:
            nota_g = st.text_input("Nota (Síntomas/Comida):").upper()

        if st.button("💾 GUARDAR REGISTRO", use_container_width=True):
            if valor_g > 0:
                try:
                    conn.execute("INSERT INTO glucosa (fecha, hora, momento, valor, notas) VALUES (?,?,?,?,?)",
                                (tiempo['fecha'], tiempo['hora'], momento_g, valor_g, nota_g))
                    conn.commit()
                    st.success("✅ ¡Guardado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("⚠️ Introduce un valor válido.")

    # --- 2. LECTURA Y ANÁLISIS ---
    try:
        df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    except:
        df_g = pd.DataFrame()

    if not df_g.empty:
        ultimo = df_g.iloc[0] # Al ser DESC, el 0 es el último
        v = ultimo['valor']
        m = ultimo['momento']

        # Reglas de Alerta
        if m == "Ayunas":
            if v < 70: color, msg = "🔵 CRÍTICO (BAJO)", "Hipoglucemia. Ingiere algo dulce."
            elif v <= 100: color, msg = "🟢 EXCELENTE", "Nivel perfecto en ayunas."
            else: color, msg = "🔴 ALTA", "Nivel elevado. Revise su dieta hoy."
        else:
            color, msg = ("🔴 ALTA", "Nivel alto después de comer.") if v > 180 else ("🟢 NORMAL", "Procesando bien.")

        st.subheader(f"🤖 Análisis: {color}")
        st.info(msg)

        # --- 3. WHATSAPP Y PDF (BLINDADOS) ---
        st.markdown("---")
        col_pdf, col_wa = st.columns(2)
        
        with col_pdf:
            if st.button("📄 GENERAR REPORTE PDF"):
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(200, 10, "CONTROL DE GLUCOSA - QUEVEDO", ln=True, align='C')
                    pdf.set_font("Arial", size=10)
                    for _, fila in df_g.head(15).iterrows():
                        pdf.cell(190, 8, f"{fila['fecha']} | {fila['momento']} | {fila['valor']} mg/dL | {fila['notas']}", 1, 1)
                    pdf.output("reporte_salud.pdf")
                    with open("reporte_salud.pdf", "rb") as f:
                        st.download_button("📥 Descargar PDF", f, file_name="reporte_salud.pdf")
                except:
                    st.error("Error al crear PDF. Cierre el archivo si lo tiene abierto.")

        with col_wa:
            msg_wa = f"Hola Dr., mi último nivel de glucosa fue {v} mg/dL en {m} ({tiempo['fecha']})."
            url_wa = f"https://wa.me/18290000000?text={urllib.parse.quote(msg_wa)}"
            st.markdown(f'''<a href="{url_wa}" target="_blank">
                <button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold;">
                📲 ENVIAR A WHATSAPP</button></a>''', unsafe_allow_html=True)

        st.markdown("### 📋 Historial Reciente")
        st.dataframe(df_g[["fecha", "momento", "valor", "notas"]].head(10), use_container_width=True)
        
        if st.button("🗑️ BORRAR ÚLTIMO REGISTRO"):
            conn.execute(f"DELETE FROM glucosa WHERE id = {ultimo['id']}")
            conn.commit()
            st.warning("Registro eliminado.")
            st.rerun() 
           # ==========================================
# ==========================================
# 14. SECCIÓN FINAL: FIRMA Y CIERRE SEGURO
# ==========================================
st.markdown("---")
col_f1, col_f2 = st.columns([3, 1])

with col_f1:
    # Firma oficial con estilo profesional - NEXUS PRO 2026
    st.markdown(f"""
        <div style="background-color:#1e1e1e; padding:20px; border-radius:15px; border-left: 6px solid #00d4ff; border-right: 1px solid #333;">
            <p style="margin:0; color:#888; font-size:12px; letter-spacing: 2px;">PROPIEDAD INTELECTUAL</p>
            <h2 style="margin:0; color:white; font-family: sans-serif;">NEXUS PRO © 2026</h2>
            <p style="margin:5px 0 0 0; color:#00d4ff; font-weight:bold; font-size:16px;">
                Autor Principal: Luis Rafael Quevedo
            </p>
            <p style="margin:2px 0 0 0; color:#555; font-size:11px;">
                Desarrollo en colaboración con Gemini AI | Sistema de Gestión de Alta Precisión
            </p>
        </div>
    """, unsafe_allow_html=True)

with col_f2:
    # Estado del sistema y ID de sesión
    st.markdown("<br>", unsafe_allow_html=True)
    st.status("SISTEMA ONLINE", state="complete")
    # Usamos un try para evitar errores si 'tiempo' no está definido aún
    try:
        id_sesion = tiempo['fecha'].replace('-', '')
        st.caption(f"ID Sesión: {id_sesion}")
    except:
        st.caption("ID Sesión: ACTIVA")

# --- NOTIFICACIÓN DE BIENVENIDA ---
st.toast(f"Bienvenido, Sr. Quevedo. Panel de control listo.", icon="🛡️")

# ==========================================
# CIERRE DE CONEXIÓN SEGURO (FINAL DEL SCRIPT)
# ==========================================
try:
    # Solo intentamos cerrar si la variable 'conn' existe y no es nula
    if 'conn' in globals() or 'conn' in locals():
        conn.close()
except:
    # Si ya está cerrada, no hacemos nada (evita pantallas rojas)
    pass
# ==========================================
# 9. MÓDULO DE BITÁCORA (CON WHATSAPP)
# ==========================================
if menu == "📝 Bitácora":
    st.title("📝 Bitácora de Actividades")
    st.markdown(f"**Fecha:** {tiempo['fecha']}")
    
    nota_rapida = st.text_area("¿Qué sucedió hoy o qué tiene pendiente?", height=150, placeholder="Escriba aquí...")
    
    if st.button("📲 ENVIAR REPORTE POR WHATSAPP", use_container_width=True):
        if nota_rapida:
            msg = f"BITÁCORA QUEVEDO ({tiempo['fecha']}): {nota_rapida}"
            url = enviar_whatsapp(msg)
            st.markdown(f'<a href="{url}" target="_blank" style="text-decoration:none;"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:5px; font-weight:bold; cursor:pointer;">ABRIR WHATSAPP AHORA</button></a>', unsafe_allow_html=True)
        else:
            st.warning("Escriba algo antes de enviar.")

    st.info("Utilice este espacio para centralizar notas que quiera recordar o enviar a su familia/médico.")
    # ==========================================
# 10. MÓDULO: BOTIQUÍN INTELIGENTE
# ==========================================
if menu == "💊 Botiquín":
    st.title("💊 Gestión de Medicamentos")
    st.subheader("Control Maestro: Sr. Quevedo")
    
    # Leer inventario
    try:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", conn)
    except:
        df_m = pd.DataFrame()

with st.expander("➕ AGREGAR MEDICAMENTO AL PLAN", expanded=False):
    c1, c2 = st.columns(2)
    n_med = c1.text_input("Nombre del Medicamento:", placeholder="Ej: Enalapril")
    d_med = c2.text_input("Dosis:", placeholder="Ej: 10mg").upper()

    c3, c4 = st.columns(2)
    h_med = c3.text_input("Horario (HH:MM):", value="08:00")
    s_med = c4.number_input("Cantidad Inicial (Pastillas):", min_value=1, value=30)

    if st.button("💾 REGISTRAR EN BOTIQUÍN", use_container_width=True):
        if n_med:
            try:
                # Conexión ultra-segura (Abre y Cierra automáticamente)
                with sqlite3.connect('nexus_data.db', timeout=10) as conn_med:
                    # 1. Aseguramos que la tabla exista con todas sus columnas
                    conn_med.execute("""
                        CREATE TABLE IF NOT EXISTS medicamentos 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nombre TEXT, dosis TEXT, horario TEXT, 
                        stock_inicial REAL, stock_actual REAL)
                    """)
                    
                    # 2. Insertamos el nuevo medicamento
                    sql = "INSERT INTO medicamentos (nombre, dosis, horario, stock_inicial, stock_actual) VALUES (?, ?, ?, ?, ?)"
                    conn_med.execute(sql, (n_med, d_med, h_med, s_med, s_med))
                    conn_med.commit()
                
                st.success(f"✅ {n_med} registrado con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.warning("⚠️ Por favor, ingrese el nombre del medicamento.")    # --- AGREGAR MEDICINA ---

# =========================================================
# 11. MÓDULO: AGENDA DE CITAS - LUIS RAFAEL QUEVEDO
# =========================================================
if menu == "📅 Agenda":
    st.title("📅 Agenda de Citas")
    
    # REGISTRO DE CITAS
    with st.expander("➕ PROGRAMAR NUEVA CITA", expanded=True):
        col1, col2 = st.columns(2)
        f_cita = col1.date_input("Fecha:", value=datetime.now())
        h_cita = col2.time_input("Hora:")
        asunto = st.text_input("MÉDICO O ESPECIALIDAD:").upper()
        lugar = st.text_input("CENTRO MÉDICO / LUGAR:").upper()
        
        if st.button("💾 GUARDAR CITA", use_container_width=True):
            if asunto:
                conn.execute("INSERT INTO agenda (fecha, hora, asunto, lugar) VALUES (?,?,?,?)",
                             (str(f_cita), str(h_cita), asunto, lugar))
                conn.commit()
                st.success("Cita guardada.")
                st.rerun()

    # VISUALIZACIÓN
    st.markdown("---")
    try:
        df_a = pd.read_sql_query("SELECT * FROM agenda ORDER BY fecha ASC", conn)
    except:
        df_a = pd.DataFrame()

    if not df_a.empty:
        for _, cita in df_a.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{cita['asunto']}**\n📅 {cita['fecha']} | ⏰ {cita['hora']}\n📍 {cita['lugar']}")
                
                # WhatsApp
                msg_wa = f"Recordatorio Cita: {cita['asunto']} el {cita['fecha']} a las {cita['hora']} en {cita['lugar']}."
                url_wa = enviar_whatsapp(msg_wa)
                c2.markdown(f'<a href="{url_wa}" target="_blank">📲 WA</a>', unsafe_allow_html=True)
                
                # Eliminar
                if c3.button("🗑️", key=f"del_cita_{cita['id']}"):
                    conn.execute("DELETE FROM agenda WHERE id = ?", (cita['id'],))
                    conn.commit()
                    st.rerun()
                st.markdown("---")

        # REPORTE PDF
        if st.button("📄 GENERAR PDF DE CITAS", use_container_width=True):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, "AGENDA MÉDICA - SR. QUEVEDO", ln=True, align='C')
            pdf.set_font("Arial", size=10)
            for _, c in df_a.iterrows():
                pdf.multi_cell(0, 10, f"FECHA: {c['fecha']} | HORA: {c['hora']}\nMEDICO: {c['asunto']}\nLUGAR: {c['lugar']}\n" + "-"*30)
            pdf.output("agenda_quevedo.pdf")
            with open("agenda_quevedo.pdf", "rb") as f:
                st.download_button("⬇️ Descargar Agenda", f, file_name="agenda_quevedo.pdf")
    else:
        st.info("No hay citas pendientes.")

# Cierre automático de conexión al final del script
conn.close()
# ==========================================
# 11. DASHBOARD & MOTOR DE INTELIGENCIA (ML)
# ==========================================
if menu == "🏠 Dashboard":
    st.title("🚀 PANEL NEXUS PRO - SR. QUEVEDO")
    
    # --- MÉTRICAS CRÍTICAS ---
    col_s1, col_s2, col_s3 = st.columns(3)
    
    # 🩺 Datos de Salud (Blindado)
    ultimo_v = 0
    try:
        df_salud = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 10", conn)
        if not df_salud.empty:
            ultimo_v = df_salud['valor'].iloc[0]
            promedio_v = df_salud['valor'].mean()
            col_s1.metric("ÚLTIMA GLUCOSA", f"{ultimo_v} mg/dL", f"{ultimo_v - promedio_v:.1f} vs prom")
        else:
            col_s1.metric("ÚLTIMA GLUCOSA", "0", "Sin datos")
    except:
        col_s1.metric("ÚLTIMA GLUCOSA", "Error", "BD no lista")

    # 💰 Datos de Finanzas (Blindado)
    gastos_totales = 0.0
    try:
        # Usamos try/except interno para evitar fallos por columnas inexistentes
        df_fin = pd.read_sql_query(f"SELECT tipo, monto FROM finanzas WHERE mes = '{tiempo['mes']}'", conn)
        if not df_fin.empty:
            gastos_totales = df_fin[df_fin['tipo'] == 'GASTO']['monto'].sum()
    except:
        pass
    
    col_s2.metric("GASTOS DEL MES", f"RD$ {gastos_totales:,.2f}")
    col_s3.metric("SISTEMA", "OPTIMIZADO", "Protección Activa")

    st.markdown("---")

    # --- ANÁLISIS PREDICTIVO (IA) ---
    st.subheader("🧠 Inteligencia Artificial: Tendencia")
    
    try:
        if 'df_salud' in locals() and len(df_salud) >= 2:
            # Motor ML Simple
            y = df_salud['valor'].values[::-1]
            x = list(range(len(y)))
            n = len(x)
            
            # Cálculo de tendencia
            denominador = (n * sum(i**2 for i in x) - sum(x)**2)
            if denominador != 0:
                pendiente = (n * sum(i*j for i,j in zip(x,y)) - sum(x)*sum(y)) / denominador
                prediccion = y[-1] + pendiente
                
                c_ml1, c_ml2 = st.columns(2)
                with c_ml1:
                    color_p = "normal" if 70 <= prediccion <= 140 else "inverse"
                    st.metric("PROYECCIÓN PRÓXIMA", f"{prediccion:.1f} mg/dL", f"{pendiente:.2f} tendencia", delta_color=color_p)
                
                with c_ml2:
                    if pendiente > 0.5:
                        st.warning("⚠️ Tendencia ALCISTA detectada.")
                    elif pendiente < -0.5:
                        st.info("📉 Tendencia BAJISTA detectada.")
                    else:
                        st.success("⚖️ Niveles ESTABLES.")
                
                st.area_chart(df_salud['valor'])
        else:
            st.info("📊 Sr. Quevedo, ingrese más datos de glucosa para activar la IA.")
    except:
        st.error("Error en motor IA.")

    # --- ACCIONES RÁPIDAS (PDF, WhatsApp, Borrado) ---
    st.markdown("---")
    ca1, ca2, ca3 = st.columns(3)
    
    with ca1:
        if st.button("📄 REPORTE PDF"):
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, "RESUMEN EJECUTIVO - NEXUS PRO", ln=True, align='C')
                pdf.set_font("Arial", size=12)
                pdf.ln(10)
                pdf.cell(200, 10, f"Usuario: Luis Rafael Quevedo", ln=True)
                pdf.cell(200, 10, f"Glucosa actual: {ultimo_v} mg/dL", ln=True)
                pdf.cell(200, 10, f"Gasto Mensual: RD$ {gastos_totales:,.2f}", ln=True)
                pdf.output("resumen_quevedo.pdf")
                with open("resumen_quevedo.pdf", "rb") as f:
                    st.download_button("📥 Bajar PDF", f, file_name="resumen_quevedo.pdf")
            except Exception as e:
                st.error(f"Error PDF: {e}")
    
    with ca2:
        msg = f"REPORTE NEXUS PRO: Sr. Quevedo, Glucosa: {ultimo_v}. Gastos: RD$ {gastos_totales:,.2f}."
        url_wa = f"https://wa.me/?text={msg}".replace(" ", "%20")
        st.markdown(f'<a href="{url_wa}" target="_blank" style="text-decoration:none;"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">📲 WA SEGURIDAD</button></a>', unsafe_allow_html=True)

    with ca3:
        if st.button("🧹 OPTIMIZAR"):
            st.cache_data.clear()
            st.success("Caché limpia.")
            st.rerun()
# ==========================================
# 12. BARRA LATERAL (REPORTE MAESTRO)
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.subheader("⚙️ Opciones Maestras")
    if st.button("📄 GENERAR PDF MAESTRO"):
        pdf_m = FPDF()
        pdf_m.add_page()
        pdf_m.set_font("Arial", 'B', 16)
        pdf_m.cell(200, 10, "SISTEMA INTEGRAL NEXUS PRO", ln=True, align='C')
        pdf_m.set_font("Arial", size=10)
        pdf_m.cell(200, 10, f"TITULAR: LUIS RAFAEL QUEVEDO", ln=True, align='C')
        pdf_m.cell(200, 10, f"FECHA: {tiempo['fecha']}", ln=True, align='C')
        pdf_m.output("Reporte_Completo_Quevedo.pdf")
        with open("Reporte_Completo_Quevedo.pdf", "rb") as f:
            st.download_button("📥 DESCARGAR REPORTE TOTAL", f, file_name="Reporte_Completo_Quevedo.pdf")

# ==========================================
# 14. SECCIÓN FINAL: FIRMA Y CIERRE SEGURO
# ==========================================
st.markdown("---")
col_f1, col_f2 = st.columns([3, 1])

with col_f1:
    # Firma oficial con estilo profesional
    st.markdown(f"""
        <div style="background-color:#1e1e1e; padding:20px; border-radius:15px; border-left: 6px solid #00d4ff; border-right: 1px solid #333;">
            <p style="margin:0; color:#888; font-size:12px; letter-spacing: 2px;">PROPIEDAD INTELECTUAL</p>
            <h2 style="margin:0; color:white; font-family: sans-serif;">NEXUS PRO © 2026</h2>
            <p style="margin:5px 0 0 0; color:#00d4ff; font-weight:bold; font-size:16px;">
                Autor Principal: Luis Rafael Quevedo
            </p>
            <p style="margin:2px 0 0 0; color:#555; font-size:11px;">
                Desarrollo en colaboración con Gemini AI | Sistema de Gestión de Alta Precisión
            </p>
        </div>
    """, unsafe_allow_html=True)

with col_f2:
    # Un pequeño toque visual de estatus
    st.markdown("<br>", unsafe_allow_html=True)
    st.status("SISTEMA ONLINE", state="complete")
    st.caption(f"ID Sesión: {tiempo['fecha'].replace('-', '')}")

# --- NOTIFICACIÓN DE BIENVENIDA ---
st.toast(f"Bienvenido, Sr. Quevedo. Panel de control listo.", icon="🛡️")

# ==========================================
# EL ÚNICO CIERRE DE CONEXIÓN (AL FINAL)
# ==========================================
try:
    if 'conn' in locals():
        conn.close()
except Exception as e:
    # Silenciamos cualquier error de cierre si la conexión ya no existe
    pass
