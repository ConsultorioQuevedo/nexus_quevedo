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

 # --- 2. BASE DE DATOS (SISTEMA QUEVEDO) ---
def conectar_conn():
    # Nombre profesional de su base de datos
    conn = sqlite3.connect("sistema_quevedo_pro.db", check_same_thread=False)
    c = conn.cursor()
    
    # 1. Tabla de Finanzas
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas 
               (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)''')
    
    # 2. Tabla de Glucosa
    c.execute('''CREATE TABLE IF NOT EXISTS glucosa 
               (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER, nota TEXT)''')
    
    # 3. TABLA MAESTRA DE REGISTRO MÉDICO (La que apaga las alertas)
    # Esta tabla anotará: QUÉ medicina, QUÉ día y a QUÉ hora se la tomó.
    c.execute('''CREATE TABLE IF NOT EXISTS registro_medico 
               (id INTEGER PRIMARY KEY, fecha TEXT, medicamento TEXT, hora_confirmada TEXT)''')
    
    # 4. Otras tablas de apoyo
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')

    conn.commit()
    return conn, c

# Ejecutamos la conexión
conn, cursor = conectar_conn()



# --- 3. DISEÑO Y ESTILO ---
st.set_page_config(page_title="SISTEMA QUEVEDO", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SEGURIDAD DE ACCESO ---
if "password_correct" not in st.session_state:
    st.title("🌐 SISTEMA QUEVEDO")
    with st.form("login"):
        pwd = st.text_input("Ingrese su Clave:", type="password")
        if st.form_submit_button("DESBLOQUEAR"):
            if pwd == "1628":
                st.session_state["password_correct"] = True
                st.rerun()
            else: st.error("Clave incorrecta")
    st.stop()

# --- 5. INICIALIZACIÓN ---
conn = conectar_conn()
f_txt, h_txt, m_txt, f_obj, ahora_obj = obtener_fecha_rd()

# --- 6. MENÚ DE NAVEGACIÓN (DASHBOARD QUEVEDO) ---
with st.sidebar:
   st.sidebar.markdown("<h1 style='color:#0056b3; text-align:center;'>📊 SISTEMA QUEVEDO</h1>", unsafe_allow_html=True)
   st.info(f"📅 {f_txt}\n⏰ {h_txt}")
   st.markdown("---")
   st.sidebar.markdown("<h1 style='color:#0056b3;...")
st.info(f"📅 {f_txt}\n⏰ {h_txt}")
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
# --- 7. LÓGICA DE ALERTAS INTELIGENTES (SISTEMA QUEVEDO DINÁMICO) ---
if opcion == "🏠 DASHBOARD":
    st.title(f"🛡️ Panel de Control - SISTEMA QUEVEDO")
    st.markdown("---")
    
    # Conectamos a la base de datos central
    conn = sqlite3.connect("control_quevedo.db")
    
    # 1. LEER MEDICAMENTOS DESDE EL BOTIQUÍN (DINÁMICO)
    # Buscamos en la tabla que tú alimentas en la sección 💊 BOTIQUÍN
    df_plan = pd.read_sql_query("SELECT nombre, dosis, horario FROM medicamentos", conn)
    
    st.subheader("🔔 Recordatorios de Salud (Basado en su Botiquín)")

    # 2. Revisar qué se ha tomado hoy
    tomas_hoy = pd.read_sql_query(f"SELECT medicamento FROM registro_medico WHERE fecha = '{f_txt}'", conn)
    lista_cumplidos = tomas_hoy['medicamento'].values
    
    # Hora actual para comparar
    hora_actual_24 = ahora_obj.hour
    alertas_visibles = 0

    if not df_plan.empty:
        for index, item in df_plan.iterrows():
            med_nombre = item['nombre']
            med_dosis = item['dosis']
            # Intentamos extraer la hora del texto "Cada Xh" o si pusiste la hora fija
            # Para que el sistema sea inteligente, asumiremos que en 'horario' pones algo como "08:00"
            # Si no hay hora válida, mostramos el registro general
            
            ya_confirmado = med_nombre in lista_cumplidos

            if not ya_confirmado:
                alertas_visibles += 1
                col_msg, col_btn = st.columns([3, 1])
                
                with col_msg:
                    st.warning(f"💊 **PENDIENTE:** {med_nombre} - Dosis: {med_dosis} ({item['horario']})")
                
                with col_btn:
                    if st.button(f"✅ REGISTRAR TOMA", key=f"btn_{med_nombre}_{index}"):
                        conn.execute("INSERT INTO registro_medico (fecha, medicamento, hora_confirmada) VALUES (?,?,?)", 
                                   (f_txt, med_nombre, h_txt))
                        conn.commit()
                        st.success(f"¡Registrado!")
                        st.rerun()
    else:
        st.info("💡 Su botiquín está vacío. Vaya a la sección 💊 BOTIQUÍN para agregar sus medicinas.")

    if alertas_visibles == 0 and not df_plan.empty:
        st.success("✅ ¡Excelente, Sr. Quevedo! Ha cumplido con todas sus medicinas registradas por hoy.")

    # 3. Resumen de cumplimiento
    st.markdown("---")
    st.markdown("#### 📋 Registro de lo tomado hoy")
    if not tomas_hoy.empty:
        st.dataframe(tomas_hoy, use_container_width=True)
    else:
        st.caption("No hay registros de toma todavía.")



 
 
  
# --- 8. MÓDULO: FINANZAS (VERSIÓN LIMPIA) ---
elif opcion == "💰 FINANZAS":
    st.title("💰 Control de Finanzas - NEXUS PRO")
    st.markdown("---")

    # Aseguramos que la tabla exista 
    conn = sqlite3.connect("control_quevedo.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS finanzas 
               (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)''')
    conn.commit()

    # Formulario de Registro
    with st.form("f_finanzas_vFinal", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo_f = st.selectbox("TIPO:", ["GASTO", "INGRESO"])
            mes_f = st.selectbox("MES:", ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"])
            monto_f = st.number_input("MONTO ($):", min_value=0.0)
        with col2:
            cat_f = st.selectbox("CATEGORÍA:", ["SALUD", "ALIMENTOS", "SERVICIOS", "TRANSPORTE", "OTROS"])
            det_f = st.text_input("DETALLE (Págó, Compra, etc):").upper()
        
        if st.form_submit_button("💾 GUARDAR MOVIMIENTO"):
            if monto_f > 0:
                conn.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                           (f_txt, mes_f, tipo_f, cat_f, det_f, monto_f))
                conn.commit()
                st.success("✅ Registro guardado con éxito.")
                st.rerun()

                st.markdown("---")

    # Mostrar Historial y Borrado
    try:
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", conn)
        if not df_f.empty:
            ing = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
            gas = df_f[df_f['tipo'] == 'GASTO']['monto'].sum()
            
            # Resumen de dinero
            st.subheader(f"Balance Actual: ${ing - gas:,.2f}")
            c1, c2 = st.columns(2)
            c1.metric("INGRESOS", f"${ing:,.2f}")
            c2.metric("GASTOS", f"${gas:,.2f}")

            st.markdown("---")
            # Tabla de movimientos con botón de borrar
            for i, row in df_f.iterrows():
                with st.container():
                    c_txt, c_mon, c_del = st.columns([3, 2, 1])
                    with c_txt:
                        st.write(f"**{row['detalle']}**")
                        st.caption(f"{row['fecha']} | {row['categoria']}")
                    with c_mon:
                        color = "green" if row['tipo'] == "INGRESO" else "red"
                        st.markdown(f"<h4 style='color:{color}; margin:0;'>${row['monto']:,.2f}</h4>", unsafe_allow_html=True)
                    with c_del:
                        if st.button("🗑️", key=f"del_fin_{row['id']}"):
                            conn.execute("DELETE FROM finanzas WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.rerun()
                            st.markdown("---")
        else:
            st.info("Aún no hay registros en su libro financiero.")
    except Exception as e:
        st.error(f"Error al cargar finanzas: {e}")
# --- 9. MÓDULO MAESTRO: CONTROL DE GLUCOSA (SÚPER ACTUALIZADO) ---
elif opcion == "🩺 SALUD & GLUCOSA":
    st.title("🩺 Panel de Control de Glucosa - NEXUS PRO")
    st.markdown("---")

    # --- LÓGICA DE COLORES Y SEMÁFOROS (CORREGIDA CON RANGOS MÉDICOS) ---
    def analizar_glucosa_full(v, m):
        """Devuelve Estado, Color y Mensaje de alerta (Rangos médicos reales)"""
        # A. ALERTA CRÍTICA: VALOR EXTREMADAMENTE BAJO (HIPOGLUCEMIA)
        if v < 70:
            return "🔴 CRÍTICO (BAJO)", "#b71c1c", "¡Alerta! Hipoglucemia. Tome azúcar rápido."

        # B. RANGOS EN AYUNAS (Antes de comer)
        elif "Ayunas" in m or "Antes" in m:
            if 70 <= v <= 100:
                return "🟢 NORMAL", "#1b5e20", "¡Excelente control en ayunas!"
            elif 101 <= v <= 125:
                return "🟡 PRE-DIABETES", "#fbc02d", "Cuidado con la dieta (Ayunas alta)."
            else: # v > 125
                return "🔴 ALTO", "#b71c1c", "Valor de Diabetes en Ayunas. Consulte al médico."

        # C. RANGOS POST-PRANDIAL (Después de comer)
        else:
            if v < 140:
                return "🟢 NORMAL", "#1b5e20", "Buen manejo post-comida."
            elif 140 <= v <= 199:
                return "🟡 ELEVADO", "#fbc02d", "Monitoree la siguiente toma (Post-comida alta)."
            else: # v >= 200
                return "🔴 CRÍTICO (ALTO)", "#b71c1c", "Alerta: Valor muy alto post-comida."
    # --- 1. FORMULARIO DE REGISTRO DETALLADO ---
    with st.form("f_glucosa_pro", clear_on_submit=True):
        st.subheader("📝 Registrar Nueva Medición Detallada")
        c_a, c_b, c_c = st.columns(3)
        with c_a:
            valor_g = st.number_input("VALOR (mg/dL):", min_value=0, step=1, help="Ingrese el número del glucómetro")
        with c_b:
            momento_g = st.selectbox("MOMENTO DE MEDICIÓN:", 
                                     ["Ayunas", "Post-Desayuno", "Antes de Almuerzo", "Post-Almuerzo", "Antes de Cena", "Post-Cena", "Antes de Dormir", "Madrugada"])
        with c_c:
            nota_g = st.text_input("NOTA (Ej: Comí mucho dulce, me siento mareado):").upper()
        
        if st.form_submit_button("💾 GUARDAR REGISTRO Y ANALIZAR"):
            if valor_g > 0:
               conn = sqlite3.connect("control_quevedo.db")
               conn.execute("INSERT INTO glucosa (fecha, hora, momento, valor, nota) VALUES (?,?,?,?,?)", (f_txt, h_txt, momento_g, valor_g, nota_g))
               conn.commit()
               estado, color, msn = analizar_glucosa_full(valor_g, momento_g)
               st.success("✅ Registro guardado")
               st.markdown(f"""
                    <div style='background-color:{color}; padding:20px; border-radius:10px; color:white; text-align:center; margin-bottom:15px;'>
                        <h2 style='color:white; margin:0;'>{valor_g} mg/dL - {estado}</h2>
                        <p style='margin:5px 0 0 0;'>{msn}</p>
                    </div>
                """, unsafe_allow_html=True)
               st.rerun()
            else:
                st.warning("⚠️ Ingrese un valor válido.")

    st.markdown("---")

    # Cargar datos históricos
    conn = sqlite3.connect("control_quevedo.db") 
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn)
    
    if not df_g.empty:
        # --- 2. GRÁFICO DE TENDENCIA PROFESIONAL ---
        st.subheader("📈 Tendencia Histórica (NEXUS GRAPH)")
        fig = px.line(df_g, x='fecha', y='valor', color='momento', 
                      title="Evolución de Niveles de Glucosa", markers=True, template="plotly_dark")
        # Líneas de referencia para guiar la vista
        fig.add_hline(y=100, line_dash="dash", line_color="#a5d6a7", annotation_text="Límite Ayunas Normal")
        fig.add_hline(y=140, line_dash="dash", line_color="#ef9a9a", annotation_text="Límite Post-Comida Normal")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- 3. PANEL DE HERRAMIENTAS (PDF, WHATSAPP, BORRADO) ---
        st.subheader("🛠️ Herramientas y Reportes")
        col_pdf, col_wa, col_del = st.columns(3)

   # A. GENERADOR DE PDF PROFESIONAL (CONEXIÓN FORZADA Y FIRMA QUEVEDO)
        with col_pdf:
            if st.button("📄 GENERAR REPORTE PDF"):
                try:
                    # FORZAMOS LA LECTURA DE LA BASE DE DATOS CORRECTA ANTES DE EMPEZAR
                    conn_pdf = sqlite3.connect("control_quevedo.db")
                    df_actualizado = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", conn_pdf)
                    
                    if df_actualizado.empty:
                        st.warning("No hay datos para generar el reporte.")
                    else:
                        pdf = FPDF()
                        pdf.add_page()
                        
                        # Encabezado Principal
                        pdf.set_font("Arial", 'B', 16)
                        pdf.set_text_color(33, 150, 243) 
                        pdf.cell(200, 10, txt="SISTEMA QUEVEDO - REPORTE MÉDICO", ln=True, align='C')
                        
                        pdf.set_font("Arial", size=10)
                        pdf.set_text_color(0)
                        pdf.cell(200, 10, txt=f"Fecha de Reporte: {f_txt} | Hora: {h_txt}", ln=True, align='C')
                        pdf.ln(10)

                        # Títulos de la Tabla
                        pdf.set_font("Arial", 'B', 10)
                        pdf.set_fill_color(230, 230, 230) 
                        pdf.cell(30, 8, "FECHA", 1, 0, 'C', True)
                        pdf.cell(35, 8, "MOMENTO", 1, 0, 'C', True)
                        pdf.cell(25, 8, "VALOR", 1, 0, 'C', True)
                        pdf.cell(45, 8, "ESTADO", 1, 0, 'C', True)
                        pdf.cell(55, 8, "NOTA", 1, 1, 'C', True)

                        # Datos de la Tabla
                        pdf.set_font("Arial", size=9)
                        for i, r in df_actualizado.iterrows():
                            # Limpieza de Emojis para el PDF
                            est_raw, _, _ = analizar_glucosa_full(r['valor'], r['momento'])
                            est_txt = est_raw.replace("🟢", "").replace("🟡", "").replace("🔴", "").strip()
                            
                            # Alerta visual en el texto si el valor es alto
                            if "ALTO" in est_txt or "CRÍTICO" in est_txt:
                                pdf.set_text_color(180, 0, 0) # Rojo para alertas
                            else:
                                pdf.set_text_color(0)

                            pdf.cell(30, 8, str(r['fecha']), 1)
                            pdf.cell(35, 8, str(r['momento']), 1)
                            pdf.cell(25, 8, f"{r['valor']} mg/dL", 1, 0, 'R')
                            pdf.cell(45, 8, est_txt, 1)
                            
                            # Limpieza de nota (quitar caracteres raros)
                            nota_p = str(r['nota']).encode('ascii', 'ignore').decode('ascii')
                            pdf.set_text_color(0)
                            pdf.cell(55, 8, nota_p[:30], 1, 1)

                        pdf.ln(15)
                        # --- EL PIE DE PÁGINA PROFESIONAL ---
                        pdf.set_font("Arial", 'B', 11)
                        pdf.cell(200, 10, txt="________________________________________________", ln=True, align='C')
                        pdf.set_font("Arial", 'I', 12)
                        pdf.cell(200, 8, txt="Luis Rafael Quevedo", ln=True, align='C')
                        pdf.set_font("Arial", size=8)
                        pdf.cell(200, 5, txt="Documento generado por NEXUS SYSTEM PRO", ln=True, align='C')
                        
                        # Generación del archivo
                        pdf_out = pdf.output(dest='S').encode('latin-1', 'replace')
                        st.download_button(
                            label="📥 DESCARGAR REPORTE PDF ACTUALIZADO", 
                            data=pdf_out, 
                            file_name=f"Reporte_Glucosa_Quevedo_{f_txt.replace('/','-')}.pdf", 
                            mime="application/pdf"
                        )
                        conn_pdf.close() # Cerramos para limpiar la memoria

                except Exception as e:
                    st.error(f"Hubo un inconveniente al generar el archivo: {e}")
        # B. VÍNCULO CON WHATSAPP
        with col_wa:
            st.markdown("##### 📱 Enviar por WhatsApp")
            num_wa = st.text_input("Número (Ej: 18091234567):", placeholder="18091234567", help="Incluya el 1 antes del número")
            if st.button("📲 Compartir Último Registro"):
                if num_wa and len(num_wa) >= 10:
                    ult = df_g.iloc[0] # Tomar el último registro
                    est_wa, _, _ = analizar_glucosa_full(ult['valor'], ult['momento'])
                    mensaje_wa = f"NEXUS PRO - Reporte de Glucosa Sr. Quevedo:\nFecha: {ult['fecha']}\nHora: {ult['hora']}\nMomento: {ult['momento']}\nValor: {ult['valor']} mg/dL\nEstado: {est_wa}\nNota: {ult['nota'] if 'nota' in ult else ''}"
                    
                    # Generar enlace de WhatsApp
                    import urllib.parse
                    msn_coded = urllib.parse.quote(mensaje_wa)
                    link_wa = f"https://wa.me/{num_wa}?text={msn_coded}"
                    st.markdown(f"[✅ Haga clic aquí para abrir WhatsApp y enviar]({link_wa})", unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Ingrese un número de teléfono válido (mínimo 10 dígitos).")

        # C. SECCIÓN DE BORRADO DE REGISTROS
        with col_del:
            st.markdown("##### 🗑️ Gestión de Historial")
            expander_del_g = st.expander("Opciones de Borrado (CUIDADO)")
            with expander_del_g:
                st.warning("Esta acción borrará registros permanentemente.")
                # Opción para borrar el último registro
                if st.button("🗑️ Borrar ÚLTIMO Registro (Deshacer)"):
                    conn.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                    conn.commit()
                    st.success("✅ Último registro eliminado.")
                    st.rerun()
                
                # Opción para limpieza total con seguro
                if st.checkbox("⚠️ Confirmar vaciado total de glucosa"):
                    if st.button("🔥 BORRAR TODO EL HISTORIAL"):
                        conn.execute("DELETE FROM glucosa")
                        conn.commit()
                        st.error("Historial de glucosa vaciado.")
                        st.rerun()

        st.markdown("---")

        # --- 4. TABLA CON SEMÁFOROS VISUALES Y NOTAS ---
        st.subheader("📋 Historial Detallado (Semáforos Inteligentes)")
        
        for i, row in df_g.iterrows():
            est, col_hex, msn_tbl = analizar_glucosa_full(row['valor'], row['momento'])
            nota_tbl = row['nota'] if 'nota' in row else ""
            
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center; 
                background-color: #161b22; padding: 15px; margin-bottom: 8px; border-radius: 8px; border-left: 10px solid {col_hex};'>
                    <div style='flex: 1.5;'>
                        <b>{row['fecha']}</b> ({row['hora']})<br>
                        <span style='color: #8b949e;'>Momento: {row['momento']}</span>
                    </div>
                    <div style='flex: 2; text-align: center; color: #8b949e;'>
                        <i>{nota_tbl}</i>
                    </div>
                    <div style='flex: 2; text-align: right; color: {col_hex}; font-weight: bold;'>
                        <h3 style='color: {col_hex}; margin: 0;'>{row['valor']} mg/dL</h3>
                        {est}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No hay registros de salud todavía. Use el formulario de arriba para el primer registro.")

# --- 10. MÓDULO: BOTIQUÍN (GESTIÓN DE MEDICAMENTOS) ---
elif opcion == "💊 BOTIQUÍN":
    st.title("💊 Inventario de Medicamentos - NEXUS PRO")
    st.markdown("---")
    
    # --- FORMULARIO PARA REGISTRAR ---
    with st.form("f_nuevo_med", clear_on_submit=True):
        st.subheader("➕ Añadir Nueva Medicina al Catálogo")
        c1, c2, c3 = st.columns(3)
        with c1: n_med = st.text_input("NOMBRE:").upper()
        with c2: d_med = st.text_input("DOSIS (Ej: 50mg):").upper()
        with c3: h_med = st.text_input("FRECUENCIA (Ej: Cada 12h):").upper()
        
       if st.form_submit_button("💾 REGISTRAR EN BOTIQUÍN"):
            if n_med:
                try:
                    # Conexión rápida y segura para evitar el error
                    conn_med = sqlite3.connect("control_quevedo.db")
                    cursor_med = conn_med.cursor()
                    
                    cursor_med.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", 
                                     (n_med, d_med, h_med))
                    
                    conn_med.commit()
                    conn_med.close() # Cerramos de inmediato
                    
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
    df_meds = pd.read_sql_query("SELECT * FROM medicamentos ORDER BY nombre ASC", conn)
    
    if not df_meds.empty:
        # Mostramos cada medicina con su propio botón de eliminar
        for i, row in df_meds.iterrows():
            with st.container():
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**💊 {row['nombre']}** | {row['dosis']} | {row['horario']}")
                with col_del:
                    # Botón individual para borrar esta medicina específica
                    if st.button("🗑️ Quitar", key=f"del_med_{row['id']}"):
                        conn.execute("DELETE FROM medicamentos WHERE id = ?", (row['id'],))
                        conn.commit()
                        st.warning(f"Se eliminó {row['nombre']}.")
                        st.rerun()
                st.markdown("<hr style='margin:5px; border:0.5px solid #30363d;'>", unsafe_allow_html=True)
        
        # Opción de Limpieza Masiva
        st.markdown("<br>", unsafe_allow_html=True)
        if st.checkbox("⚠️ Habilitar vaciado total del botiquín"):
            if st.button("🔥 BORRAR TODAS LAS MEDICINAS"):
                conn.execute("DELETE FROM medicamentos")
                conn.commit()
                st.error("Botiquín vaciado por completo.")
                st.rerun()
    else:
        st.info("El botiquín está vacío. Registre sus medicinas arriba.")
# --- 11. MÓDULO: AGENDA DE CITAS (CORREGIDO) ---
elif opcion == "🗓️ AGENDA":
    st.title("📅 Gestión de Citas Médicas - SISTEMA QUEVEDO")
    st.markdown("---")
    
    # 1. Asegurar Conexión
    conn = sqlite3.connect("control_quevedo.db")
    
    # --- FORMULARIO PARA AGENDAR ---
    with st.form("f_cita_nueva", clear_on_submit=True):
        st.subheader("🗓️ Agendar Nueva Consulta")
        col_a, col_b = st.columns(2)
        with col_a:
            doc = st.text_input("DOCTOR O ESPECIALIDAD:").upper()
            fec_c = st.date_input("FECHA DE LA CITA:", value=f_obj)
        with col_b:
            mot = st.text_area("MOTIVO O ESTUDIOS PENDIENTES:").upper()
        
        if st.form_submit_button("💾 GUARDAR CITA EN AGENDA"):
            if doc and mot:
                conn.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", 
                           (doc, str(fec_c), mot))
                conn.commit()
                st.success(f"✅ Cita con {doc} guardada para el {fec_c}")
                st.rerun()
            else:
                st.error("⚠️ Por favor, complete el nombre del Doctor y el Motivo.")

    st.markdown("---")
    st.subheader("📌 Citas Programadas")

    # --- LISTADO Y BORRADO DE CITAS ---
    try:
        # Aquí corregimos 'db' por 'conn'
        df_citas = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", conn)
        
        if not df_citas.empty:
            for i, row in df_citas.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([2, 3, 1])
                    with c1:
                        st.markdown(f"**📅 {row['fecha']}**")
                        st.caption(f"Dr/Especialidad: {row['doctor']}")
                    with c2:
                        st.write(f"📝 {row['motivo']}")
                    with c3:
                        if st.button("🗑️ Borrar", key=f"del_cita_{row['id']}"):
                            conn.execute("DELETE FROM citas WHERE id = ?", (row['id'],))
                            conn.commit()
                            st.warning("Cita eliminada.")
                            st.rerun()
                    st.markdown("---")
            
            if st.checkbox("⚠️ Activar botón de limpieza total"):
                if st.button("🔥 BORRAR TODA LA AGENDA"):
                    conn.execute("DELETE FROM citas")
                    conn.commit()
                    st.error("Agenda vaciada por completo.")
                    st.rerun()
        else:
            st.info("No tiene citas pendientes en su agenda.")
    except Exception as e:
        st.error(f"Error al cargar la agenda: {e}")
                

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
    st.caption("NEXUS PRO v4.5 | Por Luis Rafael Quevedo ayudado por IA| 2026")
