import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
from fpdf import FPDF

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO (LA CARROCERÍA)
# ==========================================
st.set_page_config(page_title="SISTEMA QUEVEDO ", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #00d4ff !important; }
    .stAlert { border-radius: 10px; border: none; }
    .card { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. RELOJ DOMINICANO (SU LÓGICA ORIGINAL)
# ==========================================
def obtener_datos_tiempo():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    # Retornamos todo lo que su código viejo usaba
    return {
        "fecha": ahora.strftime("%d/%m/%Y"),
        "hora": ahora.strftime("%I:%M %p"),
        "mes_año": ahora.strftime("%m-%Y"),
        "objeto_fecha": ahora.date(),
        "ahora": ahora
    }

tiempo = obtener_datos_tiempo()

# ==========================================
# 3. BASE DE DATOS (SISTEMA QUEVEDO)
# ==========================================
def conectar_db():
    conn = sqlite3.connect("sistema_quevedo_pro.db", check_same_thread=False)
    c = conn.cursor()
    # Mantenemos sus tablas EXACTAMENTE igual
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, nota TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS registro_medico (id INTEGER PRIMARY KEY, fecha TEXT, medicamento TEXT, hora_confirmada TEXT)')
    conn.commit()
    return conn

conn = conectar_db()

# ==========================================
# 4. LÓGICA DE PREDICCIÓN Y SEMÁFORO (POTENCIADO)
# ==========================================
def mostrar_analisis_glucosa():
    st.subheader("🧐 Análisis de Tendencias - Sistema Quevedo")
    
    try:
        df_tendencia = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 7", conn)
        
        if len(df_tendencia) > 1:
            promedio_actual = df_tendencia['valor'].mean()
            ultimo_valor = int(df_tendencia['valor'].iloc[0])
            diferencia = ultimo_valor - promedio_actual
            
            # --- NUEVO: SEMÁFORO VISUAL ---
            if ultimo_valor < 70: color_semaforo, estado = "🔵", "Nivel Bajo (Hipoglucemia)"
            elif ultimo_valor <= 130: color_semaforo, estado = "🟢", "Nivel Óptimo (Normal)"
            elif ultimo_valor <= 180: color_semaforo, estado = "🟡", "Nivel Elevado (Cuidado)"
            else: color_semaforo, estado = "🔴", "Nivel Muy Alto (Alerta)"

            col_pred1, col_pred2 = st.columns([2, 1])
            
            with col_pred1:
                st.markdown(f"### {color_semaforo} {estado}")
                if diferencia > 10:
                    st.warning(f"⚠️ **Tendencia al Alza:** Su última medición ({ultimo_valor}) está {diferencia:.1f} mg/dL por encima de su promedio.")
                elif diferencia < -10:
                    st.info(f"📉 **Tendencia a la Baja:** Su nivel actual está bajando respecto al promedio.")
                else:
                    st.success("⚖️ **Estabilidad:** Sus niveles se mantienen constantes esta semana.")
            
            with col_pred2:
                st.metric(label="Promedio Semanal", value=f"{promedio_actual:.1f} mg/dL", 
                          delta=f"{diferencia:.1f}", delta_color="inverse")
        else:
            st.info("💡 Necesito al menos 2 registros para empezar a predecir tendencias.")
    except Exception as e:
        st.error(f"Error en análisis: {e}")

# Para probar que funciona, llamamos la función
mostrar_analisis_glucosa()
# ==========================================
# 5. SEGURIDAD DE ACCESO (SU CLAVE 1628)
# ==========================================
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #58a6ff;'>🌐 SISTEMA QUEVEDO PRO</h1>", unsafe_allow_html=True)
    with st.container():
        _, col_login, _ = st.columns([1, 1, 1])
        with col_login:
            with st.form("login"):
                pwd = st.text_input("Ingrese su Clave de Seguridad:", type="password")
                if st.form_submit_button("🔓 DESBLOQUEAR ACCESO"):
                    if pwd == "1628":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else: 
                        st.error("⚠️ Clave incorrecta. Intente de nuevo.")
    st.stop()

# ==========================================
# 6. MENÚ DE NAVEGACIÓN (BARRA LATERAL)
# ==========================================
with st.sidebar:
    st.markdown(f"<h2 style='color:#58a6ff; text-align:center;'>📊 SISTEMA QUEVEDO</h2>", unsafe_allow_html=True)
    st.info(f"📅 {tiempo['fecha']}\n\n⏰ {tiempo['hora']}")
    st.markdown("---")
    
    opcion = st.radio("SECCIONES:", [
        "🏠 DASHBOARD",
        "💰 FINANZAS",
        "🩺 SALUD & GLUCOSA",
        "💊 BOTIQUÍN",
        "🗓️ AGENDA",
        "📝 BITÁCORA"
    ])
    
    st.markdown("---")
    if st.button("🔴 CERRAR SESIÓN"):
        del st.session_state["password_correct"]
        st.rerun()

# ==========================================
# 7. LÓGICA DEL DASHBOARD (ALERTAS INTELIGENTES)
# ==========================================
if opcion == "🏠 DASHBOARD":
    st.title(f"🛡️ Panel de Control - Sr. Quevedo")
    
    # Usamos la función de análisis que definimos en el Bloque 1
    mostrar_analisis_glucosa()
    
    st.markdown("---")
    st.subheader("🔔 Recordatorios de Salud (Basado en su Botiquín)")

    # 1. Leer medicamentos y tomas del día
    try:
        df_plan = pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", conn)
        tomas_hoy = pd.read_sql_query(f"SELECT medicamento FROM registro_medico WHERE fecha = '{tiempo['fecha']}'", conn)
        lista_cumplidos = tomas_hoy['medicamento'].values
        
        alertas_visibles = 0

        if not df_plan.empty:
            for index, item in df_plan.iterrows():
                med_nombre = item['nombre']
                ya_confirmado = med_nombre in lista_cumplidos

                if not ya_confirmado:
                    alertas_visibles += 1
                    with st.container():
                        # Diseño de tarjeta para cada alerta
                        col_msg, col_btn = st.columns([3, 1])
                        with col_msg:
                            st.warning(f"💊 **PENDIENTE:** {med_nombre} - Dosis: {item['dosis']} ({item['horario']})")
                        with col_btn:
                            if st.button(f"✅ REGISTRAR TOMA", key=f"btn_{med_nombre}_{index}"):
                                conn.execute("INSERT INTO registro_medico (fecha, medicamento, hora_confirmada) VALUES (?,?,?)", 
                                           (tiempo['fecha'], med_nombre, tiempo['hora']))
                                conn.commit()
                                st.success(f"¡Registrado!")
                                st.rerun()
            
            if alertas_visibles == 0:
                st.success("✅ ¡Excelente, Sr. Quevedo! Ha cumplido con todas sus medicinas por hoy.")
        else:
            st.info("💡 Su botiquín está vacío. Vaya a la sección 💊 BOTIQUÍN para agregar sus medicinas.")

        # 3. Resumen visual de lo tomado
        with st.expander("📋 Ver registro de lo tomado hoy", expanded=False):
            if not tomas_hoy.empty:
                st.table(tomas_hoy)
            else:
                st.caption("No hay registros de toma todavía.")

    except Exception as e:
        st.error(f"Error al cargar alertas: {e}")
   # ==========================================
# 8. MÓDULO: 💰 FINANZAS (VERSIÓN NEXUS PRO)
# ==========================================
elif opcion == "💰 FINANZAS":
    st.title("💰 Gestión de Capital - Sr. Quevedo")
    
    # 1. FORMULARIO DE REGISTRO CON DISEÑO DE TARJETA
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    with st.form("f_finanzas_pro", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            tipo_f = st.selectbox("TIPO:", ["GASTO", "INGRESO"])
            monto_f = st.number_input("MONTO ($):", min_value=0.0, step=100.0)
        with col2:
            cat_f = st.selectbox("CATEGORÍA:", ["SALUD", "ALIMENTOS", "SERVICIOS", "TRANSPORTE", "OTROS"])
            mes_f = st.selectbox("MES:", ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"])
        with col3:
            det_f = st.text_input("DETALLE:").upper()
            st.write("") # Espacio estético
            btn_guardar = st.form_submit_button("💾 GUARDAR MOVIMIENTO")

        if btn_guardar:
            if monto_f > 0:
                conn.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                           (tiempo['fecha'], mes_f, tipo_f, cat_f, det_f, monto_f))
                conn.commit()
                st.success("✅ Registro guardado con éxito.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. CÁLCULOS Y GRÁFICOS (LA VISIÓN PRO)
    try:
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        
        if not df_f.empty:
            ing = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
            gas = df_f[df_f['tipo'] == 'GASTO']['monto'].sum()
            balance = ing - gas

            # Métricas en columnas limpias
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("INGRESOS TOTALES", f"${ing:,.2f}")
            m2.metric("GASTOS TOTALES", f"${gas:,.2f}", delta=f"-${gas:,.2f}", delta_color="normal")
            m3.metric("BALANCE DISPONIBLE", f"${balance:,.2f}")

            # FILA DE ANÁLISIS: Gráfico de Pastel y Resumen
            col_graf, col_hist = st.columns([1, 1.5])

            with col_graf:
                st.subheader("📊 Gastos por Categoría")
                df_gastos = df_f[df_f['tipo'] == 'GASTO']
                if not df_gastos.empty:
                    fig = px.pie(df_gastos, values='monto', names='categoria', 
                                 hole=0.4, template="plotly_dark",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay gastos para graficar.")

            with col_hist:
                st.subheader("📝 Últimos Movimientos")
                # Estilo de lista moderna con borrado
                for i, row in df_f.head(10).iterrows():
                    color_monto = "#2ea043" if row['tipo'] == "INGRESO" else "#f85149"
                    simbolo = "+" if row['tipo'] == "INGRESO" else "-"
                    
                    with st.container():
                        c_info, c_del = st.columns([4, 1])
                        with c_info:
                            st.markdown(f"""
                            **{row['detalle']}**  
                            <small>{row['fecha']} | {row['categoria']}</small>  
                            <span style='color:{color_monto}; font-weight:bold; font-size:1.1em;'>
                            {simbolo} ${row['monto']:,.2f}
                            </span>
                            """, unsafe_allow_html=True)
                        with c_del:
                            st.write("") # Alineación
                            if st.button("🗑️", key=f"del_fin_{row['id']}"):
                                conn.execute("DELETE FROM finanzas WHERE id = ?", (row['id'],))
                                conn.commit()
                                st.rerun()
                        st.markdown("---")
        else:
            st.info("Aún no hay registros en su libro financiero.")
    except Exception as e:
        st.error(f"Error al cargar finanzas: {e}")     
# ==========================================
# 9. MÓDULO MAESTRO: 🩺 SALUD & GLUCOSA
# ==========================================
elif opcion == "🩺 SALUD & GLUCOSA":
    st.title("🩺 Control de Glucosa - Sr. Quevedo")
    
    # --- LÓGICA DE COLORES (Rangos Médicos Reales) ---
    def analizar_glucosa_full(v, m):
        if v < 70:
            return "🔴 CRÍTICO (BAJO)", "#f85149", "¡Alerta! Hipoglucemia. Tome azúcar rápido."
        elif "Ayunas" in m or "Antes" in m:
            if 70 <= v <= 100:
                return "🟢 NORMAL", "#2ea043", "¡Excelente control en ayunas!"
            elif 101 <= v <= 125:
                return "🟡 PRE-DIABETES", "#f1e05a", "Cuidado con la dieta (Ayunas alta)."
            else:
                return "🔴 ALTO", "#f85149", "Valor de Diabetes en Ayunas. Consulte al médico."
        else:
            if v < 140:
                return "🟢 NORMAL", "#2ea043", "Buen manejo post-comida."
            elif 140 <= v <= 199:
                return "🟡 ELEVADO", "#f1e05a", "Monitoree la siguiente toma (Post-comida alta)."
            else:
                return "🔴 CRÍTICO (ALTO)", "#f85149", "Alerta: Valor muy alto post-comida."

    # 1. FORMULARIO DE REGISTRO
    with st.form("f_glucosa_pro", clear_on_submit=True):
        st.subheader("📝 Nueva Medición")
        c_a, c_b, c_c = st.columns([1, 1, 2])
        with c_a:
            valor_g = st.number_input("VALOR (mg/dL):", min_value=0, step=1)
        with c_b:
            momento_g = st.selectbox("MOMENTO:", ["Ayunas", "Post-Desayuno", "Antes de Almuerzo", "Post-Almuerzo", "Antes de Cena", "Post-Cena", "Antes de Dormir", "Madrugada"])
        with c_c:
            nota_g = st.text_input("NOTA / OBSERVACIÓN:").upper()
        
        if st.form_submit_button("💾 GUARDAR REGISTRO"):
            if valor_g > 0:
                conn.execute("INSERT INTO glucosa (fecha, hora, momento, valor, nota) VALUES (?,?,?,?,?)", 
                           (tiempo['fecha'], tiempo['hora'], momento_g, valor_g, nota_g))
                conn.commit()
                st.success("✅ Registro guardado")
                st.rerun()

    # 2. CARGA Y VISUALIZACIÓN
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    
    if not df_g.empty:
        # Gráfico de Tendencia
        st.subheader("📈 Tendencia Histórica")
        fig = px.line(df_g, x='fecha', y='valor', color='momento', markers=True, template="plotly_dark")
        fig.add_hline(y=100, line_dash="dash", line_color="#2ea043", annotation_text="Límite Ayunas")
        fig.add_hline(y=140, line_dash="dash", line_color="#f1e05a", annotation_text="Límite Post-Comida")
        st.plotly_chart(fig, use_container_width=True)

        # 3. PANEL DE HERRAMIENTAS
        st.markdown("---")
        col_pdf, col_wa, col_del = st.columns(3)

with col_pdf:
            if st.button("📄 GENERAR REPORTE PDF"):
                try:
                    # ESTA ES LA SOLUCIÓN: Volver a leer la base de datos justo al hacer clic
                    df_actualizado = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
                    
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(200, 10, txt="SISTEMA QUEVEDO - REPORTE MÉDICO", ln=True, align='C')
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(200, 10, txt=f"PACIENTE: LUIS RAFAEL QUEVEDO", ln=True, align='C')
                    pdf.ln(10)
                    
                    # Encabezados de tabla
                    pdf.set_font("Arial", 'B', 10)
                    pdf.cell(40, 8, "FECHA", 1); pdf.cell(40, 8, "MOMENTO", 1); pdf.cell(30, 8, "VALOR", 1); pdf.cell(80, 8, "NOTA", 1, 1)
                    pdf.set_font("Arial", size=9)
                    # USAMOS EL DATASET QUE ESTAMOS VIENDO EN PANTALLA
                    for _, r in df_g.head(20).iterrows():
                        pdf.cell(40, 8, str(r['fecha']), 1)
                        pdf.cell(40, 8, str(r['momento']), 1)
                        pdf.cell(30, 8, f"{r['valor']} mg/dL", 1)
                        # CORRECCIÓN: Usamos 'notas' para que coincida con la base de datos
                        texto_nota = str(r.get('notas', r.get('nota', '')))
                        nota_pdf = texto_nota[:40].encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(80, 8, nota_pdf, 1, 1)
                    
                    pdf_data = pdf.output(dest='S').encode('latin-1')
                    st.download_button(label="📥 DESCARGAR REPORTE", data=pdf_data, file_name=f"Reporte_Quevedo_{tiempo['fecha']}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Error PDF: {e}")

            with col_wa:
                num_wa = st.text_input("WhatsApp (Ej: 1809...):")
                if st.button("📲 COMPARTIR ÚLTIMO"):
                    if num_wa and not df_g.empty:
                        u = df_g.iloc[0]
                        # CORRECCIÓN: Sincronizado a 'notas'
                        msg = f"Reporte Sr. Quevedo: {u['fecha']} - {u['momento']}: {u['valor']} mg/dL. Nota: {u.get('notas', '')}"
                        link = f"https://wa.me/{num_wa}?text={msg.replace(' ', '%20')}"
                        st.markdown(f"[✅ ENVIAR POR WHATSAPP]({link})")

         with col_del:
            if st.checkbox("🔓 Activar Borrado"):
                if st.button("🗑️ Borrar Último"):
                    conn.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                    conn.commit()
                    st.rerun()
            
            st.subheader("📊 Historial con Semáforos")
            if not df_g.empty:
                for i, row in df_g.iterrows():
                    est, col, msn = analizar_glucosa_full(row['valor'], row['momento'])
                    st.markdown(f"""
                        <div style='background-color: #161b22; padding: 15px; margin-bottom: 8px; border-radius: 10px; border-left: 5px solid {col};'>
                            <div style='display: flex; justify-content: space-between;'>
                                <span><b>{row['fecha']}</b> | {row['momento']}</span>
                                <span style='color: {col}; font-weight: bold;'>{row['valor']} mg/dL</span>
                            </div>
                            <div style='color: #8b949e; font-size: 0.9em; margin-top: 5px;'><i>{row.get('notas', '')}</i></div>
                            <div style='color: {col}; font-size: 0.8em; font-weight: bold; margin-top: 5px;'>ESTADO: {est}</div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No hay registros todavía.")
                    
# --- 10. MÓDULO: BOTIQUÍN (GESTIÓN DE MEDICAMENTOS) ---
elif opcion == "💊 BOTIQUÍN":
    st.title("💊 Inventario de Medicamentos - NEXUS PRO")
    st.markdown("---")
    

    # --- ASEGURAR QUE LA TABLA EXISTA (PREVENCIÓN DE ERRORES) ---
    conn_init = sqlite3.connect("control_quevedo.db")
    conn_init.execute("""
        CREATE TABLE IF NOT EXISTS medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT, 
            dosis TEXT, 
            horario TEXT
        )
    """)
    conn_init.commit()
    conn_init.close()
    
    # --- FORMULARIO PARA REGISTRAR ---
    with st.form("f_nuevo_med", clear_on_submit=True):
        st.subheader("➕ Añadir Nueva Medicina al Catálogo")
        c1, c2, c3 = st.columns(3)
        with c1: n_med = st.text_input("NOMBRE:").upper()
        with c2: d_med = st.text_input("DOSIS (Ej: 50mg):").upper()
        with c3: h_med = st.text_input("HORA/FRECUENCIA (Ej: 08:00 AM):").upper()
        
        if st.form_submit_button("💾 REGISTRAR EN BOTIQUÍN"):
            if n_med:
                try:
                    conn_med = sqlite3.connect("control_quevedo.db")
                    cursor_med = conn_med.cursor()
                    cursor_med.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", 
                                     (n_med, d_med, h_med))
                    conn_med.commit()
                    conn_med.close()
                    st.success(f"✅ {n_med} añadida correctamente al sistema.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("⚠️ Escriba el nombre de la medicina.") 

    st.markdown("---")
    st.subheader("📋 Medicinas en Inventario")

# --- LISTADO CON BOTÓN DE BORRAR ---
    conn = sqlite3.connect("control_quevedo.db")
    # Verificamos si hay datos
    df_meds = pd.read_sql_query("SELECT * FROM medicamentos ORDER BY nombre ASC", conn)
    
    if not df_meds.empty:
        # Mostramos una tabla resumen primero para vista rápida
        from datetime import date
        fecha_limpia = date.today()        
        st.markdown("#### ⚙️ Gestionar Medicinas")

        # Mostramos cada medicina con su propio botón de eliminar
        for i, row in df_meds.iterrows():
            with st.container():
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**💊 {row['nombre']}** | {row['dosis']} | {row['horario']}")
                with col_del:
                    if st.button("🗑️ Quitar", key=f"del_med_{row['id']}"):
                        conn.execute("DELETE FROM medicamentos WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.warning(f"Se eliminó {row['nombre']}.")
                        st.rerun()
                st.markdown("<hr style='margin:5px; border:0.5px solid #30363d;'>", unsafe_allow_html=True)
        
        # Opción de Limpieza Masiva
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🚨 Zona de Peligro"):
            if st.checkbox("Confirmar vaciado total"):
                if st.button("🔥 BORRAR TODO EL BOTIQUÍN"):
                    conn.execute("DELETE FROM medicamentos")
                    conn.commit()
                    st.error("Botiquín vaciado por completo.")
                    st.rerun()
    else:
        st.info("El botiquín está vacío. Registre sus medicinas arriba.")
        conn.close()   

# 11. MÓDULO: 🗓️ AGENDA DE CITAS
# =========================================================
elif opcion == "🗓️ AGENDA":
    st.title("🗓️ Mi Agenda de Citas")
    st.markdown("---")
    
    # Preparamos la fecha actual de forma segura
    from datetime import date
    try:
        fecha_limpia = date.today() 
    except:
        fecha_limpia = date(2026, 1, 1)

    # 1. FORMULARIO PARA AGENDAR
    with st.form("f_cita_nueva", clear_on_submit=True):
        st.subheader("🗓️ Agendar Nueva Consulta")
        col_a, col_b = st.columns(2)
        
        with col_a:
            doc = st.text_input("DOCTOR O ESPECIALIDAD:").upper()
            fec_c = st.date_input("FECHA DE LA CITA:", value=fecha_limpia)
            
        with col_b:
            mot = st.text_area("MOTIVO O ESTUDIOS PENDIENTES:").upper()
        
        if st.form_submit_button("💾 GUARDAR CITA EN AGENDA"):
            if doc and mot:
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", 
                           (doc, str(fec_c), mot))
                db.commit()
                st.success(f"✅ Cita con {doc} guardada correctamente.")
                st.rerun()
            else:
                st.error("⚠️ Por favor, complete el nombre del Doctor y el Motivo.")

    st.markdown("---")
    st.subheader("📌 Citas Programadas")

    # 2. LISTADO VISUAL Y BORRADO
    try:
        df_citas = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        
        if not df_citas.empty:
            for i, row in df_citas.iterrows():
                fecha_hoy_str = fecha_limpia.strftime("%Y-%m-%d")
                cita_pasada = str(row['fecha']) < fecha_hoy_str
                
                fondo = "#ffffff" if not cita_pasada else "#f1f5f9"
                borde = "#3b82f6" if not cita_pasada else "#94a3b8"

                st.markdown(f"""
                <div style='background-color: {fondo}; padding: 15px; border-radius: 12px; 
                            border-left: 6px solid {borde}; margin-bottom: 12px; 
                            box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: #1e293b;'>
                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                        <span style='font-size: 1.1em;'><b>📅 FECHA: {row['fecha']}</b></span>
                        <span style='font-weight: bold; color: {borde};'>DR: {row['doctor']}</span>
                    </div>
                    <div style='margin-top: 8px; border-top: 1px solid #eee; padding-top: 8px;'>
                        <p style='margin: 0;'><b>📝 MOTIVO:</b> {row['motivo']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🗑️ Eliminar Cita de {row['doctor']}", key=f"del_cita_{row['id']}"):
                    db.execute("DELETE FROM citas WHERE id = ?", (row['id'],))
                    db.commit()
                    st.success("Cita eliminada.")
                    st.rerun()
        else:
            st.info("No tiene citas programadas.")
            
    except Exception:
        st.error("Aviso: La tabla de citas se está sincronizando...")

# =========================================================
# 12. MÓDULO: 📝 BITÁCORA PROFESIONAL
# =========================================================
elif menu == "📝 BITÁCORA":
    st.title("📝 Bitácora de Notas")
    st.markdown("---")
    
    nota_nueva = st.text_area("Escriba sus observaciones del día:", height=150, 
                             placeholder="Ej: Hoy me sentí con mucha energía...")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 GUARDAR NOTA"):
            if nota_nueva.strip():
                with open("bitacora_quevedo.txt", "a", encoding="utf-8") as f:
                    f.write(f"[{f_rd} {h_rd}]: {nota_nueva}\n\n")
                    f.write("-" * 30 + "\n")
                st.success("✅ Nota guardada.")
                st.rerun()

    with c2:
        if st.button("📄 EXPORTAR A PDF"):
            try:
                from fpdf import FPDF
                import os
                if os.path.exists("bitacora_quevedo.txt"):
                    with open("bitacora_quevedo.txt", "r", encoding="utf-8") as f:
                        contenido = f.read()
                    
                    if contenido:
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", 'B', 16)
                        pdf.cell(200, 10, txt="NEXUS PRO - BITÁCORA", ln=True, align='C')
                        pdf.set_font("Arial", size=11)
                        pdf.ln(10)
                        pdf.multi_cell(0, 7, txt=contenido.encode('latin-1', 'replace').decode('latin-1'))
                        
                        pdf_data = pdf.output(dest='S').encode('latin-1')
                        st.download_button(label="📥 DESCARGAR PDF", data=pdf_data, 
                                         file_name="Bitacora_Quevedo.pdf", mime="application/pdf")
                else:
                    st.warning("Bitácora vacía.")
            except:
                st.error("Error al generar PDF. Verifique la librería 'fpdf'.")

    st.markdown("---")
    st.subheader("📖 Vista Previa")
    try:
        import os
        if os.path.exists("bitacora_quevedo.txt"):
            with open("bitacora_quevedo.txt", "r", encoding="utf-8") as f:
                notas = f.read()
            if notas:
                st.text_area("Contenido actual:", notas, height=300)
                if st.checkbox("🔓 Habilitar Borrado Total"):
                    if st.button("🔥 VACIAR BITÁCORA"):
                        open("bitacora_quevedo.txt", "w").close()
                        st.rerun()
        else:
            st.info("No hay notas todavía.")
    except:
        st.caption("Esperando primer registro...")

# Pie de página final
st.markdown("---")

st.caption(f"NEXUS PRO v4.5 | {tiempo['fecha']} | Luis Rafael Quevedo")
