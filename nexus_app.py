import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import io
from fpdf import FPDF

# --- 1. RELOJ DOMINICANO ---
def obtener_fecha_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date(), ahora

# --- 2. BASE DE DATOS (ESTRUCTURA ORIGINAL) ---
def conectar_db():
    conn = sqlite3.connect("control_quevedo.db", check_same_thread=False)
    c = conn.cursor()
    # Tablas necesarias para salud, medicinas y finanzas
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS registro_medico (id INTEGER PRIMARY KEY, fecha TEXT, medicamento TEXT, hora_confirmada TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    conn.commit()
    return conn

# --- 3. DISEÑO Y ESTILO ---
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SEGURIDAD DE ACCESO ---
if "password_correct" not in st.session_state:
    st.title("🌐 ACCESO NEXUS SYSTEM")
    with st.form("login"):
        pwd = st.text_input("Ingrese su Clave:", type="password")
        if st.form_submit_button("DESBLOQUEAR"):
            if pwd == "admin123":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Clave incorrecta")
    st.stop()

# --- 5. INICIALIZACIÓN ---
db = conectar_db()
f_txt, h_txt, m_txt, f_obj, ahora_obj = obtener_fecha_rd()

# --- 6. MENÚ DE NAVEGACIÓN (DASHBOARD QUEVEDO) ---
with st.sidebar:
    st.markdown("<h2 style='color:#58a6ff;'>🌐 NEXUS PRO</h2>", unsafe_allow_html=True)
    st.info(f"📅 {f_txt}\n⏰ {h_txt}")
    st.markdown("---")
    opcion = st.radio("SECCIONES:", [
        "🏠 DASHBOARD", 
        "💰 FINANZAS RD$", 
        "🩺 SALUD & GLUCOSA", 
        "💊 BOTIQUÍN", 
        "📅 AGENDA", 
        "📝 BITÁCORA"
    ])
    st.markdown("---")
    if st.button("🔴 CERRAR SESIÓN"):
        del st.session_state["password_correct"]
        st.rerun()

# --- 7. LÓGICA DE ALERTAS INTELIGENTES (INICIO) ---
if opcion == "🏠 DASHBOARD":
    st.title(f"Panel de Control - Sr. Quevedo")
    st.markdown("---")
    
    # Planificación horaria de sus medicamentos
    plan_medico = [
        {"med": "Jarinu Max", "hora": "07:00 AM", "rango": [6, 9]},
        {"med": "Aspirin / Pregabalina", "hora": "08:00 AM", "rango": [7, 10]},
        {"med": "Pregabalina (Tarde)", "hora": "06:00 PM", "rango": [17, 20]},
        {"med": "Insulina", "hora": "08:00 PM", "rango": [19, 22]},
        {"med": "Triglicer / Libal", "hora": "09:00 PM", "rango": [20, 23]}
    ]

    st.subheader("🔔 Alertas de Salud (Tiempo Real)")
    hora_actual_24 = ahora_obj.hour
    alertas_vivas = 0

    for item in plan_medico:
        # Si la hora actual está dentro del rango permitido para la medicina
        if item["rango"][0] <= hora_actual_24 <= item["rango"][1]:
            alertas_vivas += 1
            st.warning(f"💊 **ATENCIÓN:** Es hora de su **{item['med']}** ({item['hora']})")
            
            if st.button(f"CONFIRMAR TOMA: {item['med']}", key=f"btn_{item['med']}"):
                db.execute("INSERT INTO registro_medico (fecha, medicamento, hora_confirmada) VALUES (?,?,?)", 
                           (f_txt, item['med'], h_txt))
                db.commit()
                st.success(f"✅ Toma de {item['med']} registrada a las {h_txt}")
                st.rerun()

    if alertas_vivas == 0:
        st.success("✅ No tiene medicamentos pendientes en este momento.")

    # Mostrar últimos registros de tomas para tranquilidad
    st.markdown("---")
    st.markdown("#### 📋 Últimas Tomas Registradas")
    df_tomas = pd.read_sql_query("SELECT medicamento, hora_confirmada FROM registro_medico ORDER BY id DESC LIMIT 5", db)
    if not df_tomas.empty:
        st.table(df_tomas)
    else:
        st.caption("No hay registros de tomas el día de hoy.")

# --- 8. MÓDULO DE FINANZAS (CONTROL QUEVEDO RD$) ---
elif opcion == "💰 FINANZAS RD$":
    st.title("💰 Gestión Financiera - NEXUS PRO")
    st.markdown("---")

    # Cargar datos financieros
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    
    # Cálculos de Balance Real
    if not df_f.empty:
        t_ingresos = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
        # Los gastos se restan (se asume que se guardan negativos o se calculan así)
        t_gastos = abs(df_f[df_f['tipo'] == 'GASTO']['monto'].sum())
        balance_actual = t_ingresos - t_gastos
    else:
        t_ingresos, t_gastos, balance_actual = 0.0, 0.0, 0.0

    # Visualización de Métricas (Tarjetas de Dinero)
    c1, c2, c3 = st.columns(3)
    c1.metric("DISPONIBLE TOTAL", f"RD$ {balance_actual:,.2f}")
    c2.metric("GASTOS ACUMULADOS", f"RD$ {t_gastos:,.2f}", delta_color="inverse")
    c3.metric("INGRESOS TOTALES", f"RD$ {t_ingresos:,.2f}")

    st.markdown("---")
    
    # Formulario de Registro Rápido
    with st.form("f_movimiento", clear_on_submit=True):
        st.subheader("📝 Registrar Nuevo Movimiento")
        col_a, col_b = st.columns(2)
        with col_a:
            tipo_mov = st.selectbox("Tipo de Movimiento", ["GASTO", "INGRESO"])
            monto_mov = st.number_input("Monto (RD$)", min_value=0.0, step=100.0)
        with col_b:
            categoria_mov = st.text_input("Categoría (Ej: Comida, Farmacia, Pago)").upper()
            detalle_mov = st.text_input("Detalle o Nota").upper()
        
        if st.form_submit_button("💾 GUARDAR MOVIMIENTO"):
            # Lógica: Los gastos se guardan negativos para que la suma sea automática
            valor_final = -monto_mov if tipo_mov == "GASTO" else monto_mov
            db.execute("""
                INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f_txt, m_txt, tipo_mov, categoria_mov, detalle_mov, valor_final))
            db.commit()
            st.success("✅ Movimiento registrado correctamente.")
            st.rerun()

    # Historial de Movimientos
    st.markdown("#### 📜 Historial de Transacciones")
    if not df_f.empty:
        # Formatear la tabla para que se vea profesional
        df_display = df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']].copy()
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No hay movimientos registrados en la base de datos.")

# --- 9. MÓDULO DE SALUD (SEMÁFORO DE GLUCOSA QUEVEDO) ---
elif opcion == "🩺 SALUD & GLUCOSA":
    st.title("🩺 Monitoreo de Salud Inteligente")
    st.markdown("---")

    # Función interna para el Semáforo de Salud
    def analizar_glucosa(v, m):
        if "Ayunas" in m:
            if 70 <= v <= 100: return "🟢 NORMAL", "#1b5e20"
            elif 101 <= v <= 125: return "🟡 PRE-DIABETES", "#fbc02d"
            else: return "🔴 ALTO (REVISAR)", "#b71c1c"
        else: # Después de comer (Post-Prandial)
            if v < 140: return "🟢 NORMAL", "#1b5e20"
            elif 140 <= v <= 199: return "🟡 ELEVADO", "#fbc02d"
            else: return "🔴 CRÍTICO", "#b71c1c"

    # Formulario de Entrada Médica
    with st.form("f_salud_v4", clear_on_submit=True):
        st.subheader("📝 Registrar Nivel de Glucosa")
        col1, col2 = st.columns(2)
        with col1:
            valor_g = st.number_input("Nivel (mg/dL):", min_value=0, step=1)
        with col2:
            momento_g = st.selectbox("Momento de la Medición:", 
                                     ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de Dormir"])
        
        if st.form_submit_button("💾 GUARDAR REGISTRO MÉDICO"):
            db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", 
                       (f_txt, h_txt, momento_g, valor_g))
            db.commit()
            # Alerta visual inmediata del resultado
            estado, color = analizar_glucosa(valor_g, momento_g)
            st.markdown(f"<div style='background-color:{color}; padding:15px; border-radius:10px; color:white; font-weight:bold; text-align:center;'>"
                        f"RESULTADO: {estado} ({valor_g} mg/dL)</div>", unsafe_allow_html=True)
            st.rerun()

    st.markdown("---")

    # Visualización de Datos Históricos
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
    
    if not df_g.empty:
        # Gráfico de Tendencia Profesional
        fig = px.line(df_g, x='fecha', y='valor', color='momento', 
                      title="📈 Evolución de Glucosa (NEXUS PRO)", markers=True, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        # Tabla con Semáforos Visuales
        st.subheader("📋 Historial Detallado")
        
        # Aplicamos el análisis a cada fila para mostrar el color
        for i, row in df_g.head(10).iterrows():
            est, col_hex = analizar_glucosa(row['valor'], row['momento'])
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center; 
                background-color: #161b22; padding: 10px; margin-bottom: 5px; border-radius: 8px; border-left: 8px solid {col_hex};'>
                    <div style='flex: 1;'><b>{row['fecha']}</b> ({row['hora']})</div>
                    <div style='flex: 1; text-align: center;'><b>{row['momento']}</b></div>
                    <div style='flex: 1; text-align: right; color: {col_hex}; font-weight: bold;'>{row['valor']} mg/dL - {est}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No hay registros de salud todavía.")

# --- 10. MÓDULO: BOTIQUÍN (CATÁLOGO DE MEDICAMENTOS) ---
elif opcion == "💊 BOTIQUÍN":
    st.title("💊 Catálogo de Medicamentos Personal")
    st.markdown("---")
    
    with st.form("f_nuevo_med", clear_on_submit=True):
        st.subheader("➕ Añadir Nueva Medicina")
        c1, c2, c3 = st.columns(3)
        with c1: n_med = st.text_input("Nombre de Medicina").upper()
        with c2: d_med = st.text_input("Dosis (Ej: 500mg)").upper()
        with c3: h_med = st.text_input("Frecuencia (Ej: Cada 8h)").upper()
        
        if st.form_submit_button("💾 REGISTRAR EN BOTIQUÍN"):
            db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", 
                       (n_med, d_med, h_med))
            db.commit()
            st.success(f"✅ {n_med} añadida al catálogo.")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Medicinas Registradas")
    df_meds = pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", db)
    if not df_meds.empty:
        st.table(df_meds)
    else:
        st.info("El botiquín está vacío.")

# --- 11. MÓDULO: AGENDA DE CITAS ---
elif opcion == "📅 AGENDA":
    st.title("📅 Gestión de Citas Médicas")
    st.markdown("---")
    
    with st.form("f_cita_nueva", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            doc = st.text_input("Doctor o Especialidad").upper()
            fec_c = st.date_input("Fecha de la Cita")
        with col_b:
            mot = st.text_area("Motivo de la Consulta").upper()
        
        if st.form_submit_button("🗓️ AGENDAR CITA"):
            # Usamos el cursor del objeto db para insertar directamente
            c = db.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
            db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", 
                       (doc, str(fec_c), mot))
            db.commit()
            st.success("✅ Cita agendada correctamente.")
            st.rerun()

    st.markdown("---")
    st.subheader("📌 Próximas Citas")
    try:
        df_citas = pd.read_sql_query("SELECT doctor, fecha, motivo FROM citas ORDER BY fecha ASC", db)
        if not df_citas.empty:
            st.dataframe(df_citas, use_container_width=True)
        else:
            st.info("No tiene citas pendientes.")
    except:
        st.info("Módulo de citas listo para el primer registro.")

# --- 12. MÓDULO: BITÁCORA PROFESIONAL (PDF + GESTIÓN) ---
elif opcion == "📝 BITÁCORA":
    st.title("📝 Bitácora de Notas Inteligente")
    st.markdown("---")
    
    # Campo de texto para nueva nota
    nota_nueva = st.text_area("Escriba sus observaciones del día:", height=150, placeholder="Ej: Hoy me sentí con mucha energía después del desayuno...")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 GUARDAR NOTA LOCAL"):
            if nota_nueva:
                with open("bitacora_quevedo.txt", "a", encoding="utf-8") as f:
                    f.write(f"{f_txt} {h_txt}: {nota_nueva}\n\n")
                st.success("✅ Nota guardada en el archivo del sistema.")
                st.rerun()
            else:
                st.warning("Escriba algo antes de guardar.")

    # --- FUNCIÓN PARA GENERAR PDF DE LA BITÁCORA ---
    with col_btn2:
        if st.button("📄 GENERAR REPORTE PDF"):
            try:
                with open("bitacora_quevedo.txt", "r", encoding="utf-8") as f:
                    contenido = f.read()
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt="NEXUS PRO - BITÁCORA PERSONAL", ln=True, align='C')
                pdf.set_font("Arial", size=12)
                pdf.ln(10)
                pdf.multi_cell(0, 10, txt=contenido)
                
                # Crear el archivo en memoria para descargar
                pdf_output = pdf.output(dest='S').encode('latin-1', 'replace')
                st.download_button(label="📥 Descargar PDF Ahora", 
                                   data=pdf_output, 
                                   file_name=f"Bitacora_Quevedo_{f_txt.replace('/','-')}.pdf",
                                   mime="application/pdf")
            except FileNotFoundError:
                st.error("No hay notas guardadas para generar un PDF.")

    st.markdown("---")
    
    # --- SECCIÓN DE BORRADO Y LIMPIEZA ---
    st.subheader("🗑️ Gestión de Archivos")
    expander = st.expander("Opciones de Limpieza (CUIDADO)")
    with expander:
        st.warning("Esta acción borrará todas las notas guardadas permanentemente.")
        if st.button("🔥 BORRAR TODA LA BITÁCORA"):
            with open("bitacora_quevedo.txt", "w", encoding="utf-8") as f:
                f.write("") # Sobreescribe el archivo dejándolo vacío
            st.error("Bitácora vaciada correctamente.")
            st.rerun()

    # Visualización rápida de lo que hay en el archivo
    st.markdown("#### 📖 Vista Previa de Notas Actuales")
    try:
        with open("bitacora_quevedo.txt", "r", encoding="utf-8") as f:
            notas_vivas = f.read()
            if notas_vivas:
                st.text_area("Contenido del archivo:", notas_vivas, height=300, disabled=True)
            else:
                st.info("La bitácora está vacía actualmente.")
    except FileNotFoundError:
        st.info("Aún no se ha creado el archivo de bitácora.") 
        
    st.markdown("---")
    st.caption("NEXUS PRO v4.5 | Desarrollado para Luis Rafael Quevedo | 2026")
