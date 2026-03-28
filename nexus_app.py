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
def conectar_db():
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
db, cursor = conectar_db()



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
# --- 7. LÓGICA DE ALERTAS INTELIGENTES (SISTEMA QUEVEDO) ---
if opcion == "🏠 DASHBOARD":
    st.title(f"🛡️ Panel de Control - SISTEMA QUEVEDO")
    st.markdown("---")
    
    # 1. Lista de sus medicamentos con sus horarios
    plan_medico = [
        {"med": "Jarinu Max", "hora": "07:00 AM", "rango": [6, 10]},
        {"med": "Aspirin / Pregabalina", "hora": "08:00 AM", "rango": [7, 11]},
        {"med": "Pregabalina (Tarde)", "hora": "06:00 PM", "rango": [17, 21]},
        {"med": "Insulina", "hora": "08:00 PM", "rango": [19, 23]},
        {"med": "Triglicer / Libal", "hora": "09:00 PM", "rango": [20, 23]}
    ]

    st.subheader("🔔 Recordatorios de Salud (Tiempo Real)")

    conn = sqlite3.connect("control_quevedo.db")
    tomas_hoy = pd.read_sql_query(f"SELECT medicamento FROM registro_medico WHERE fecha = '{f_txt}'", conn)
    lista_cumplidos = tomas_hoy['medicamento'].values

    hora_actual_24 = ahora_obj.hour
    alertas_visibles = 0

    for item in plan_medico:
        # ¿Estamos en el horario?
        en_horario = item["rango"][0] <= hora_actual_24 <= item["rango"][1]
        # ¿Ya se la tomó?
        ya_confirmado = item["med"] in lista_confirmados if 'lista_confirmados' in locals() else item["med"] in lista_cumplidos

        if en_horario and not ya_confirmado:
            alertas_visibles += 1
            col_msg, col_btn = st.columns([3, 1])
            
            with col_msg:
                st.warning(f"💊 **ATENCIÓN:** Es hora de su **{item['med']}** ({item['hora']})")
           
            with col_btn:
            # AQUÍ ESTÁ EL BOTÓN QUE USTED QUERÍA
            if st.button(f"✅ YA ME LA TOMÉ", key=f"btn_{item['med']}"):
                conn.execute("INSERT INTO registro_medico (fecha, medicamento, hora_confirmada) VALUES (?,?,?)", (f_txt, item['med'], h_txt))
                conn.commit()
                st.success(f"¡Registrado!")
                st.rerun()

    if alertas_visibles == 0:
        st.success("✅ No tiene medicamentos pendientes por confirmar en este momento.")

    # 3. Mostrar resumen de lo que ya se tomó para su tranquilidad
    st.markdown("---")
    st.markdown("#### 📋 Registro de Cumplimiento (Hoy)")
    if not tomas_hoy.empty:
        st.dataframe(tomas_hoy, use_container_width=True)
    else:
        st.caption("Aún no ha registrado tomas el día de hoy.")


 
 
  
# --- 8. MÓDULO: FINANZAS (VERSIÓN LIMPIA) ---
elif opcion == "💰 FINANZAS":
    st.title("💰 Control de Finanzas - NEXUS PRO")
    st.markdown("---")

    # Aseguramos que la tabla exista
    db.execute('''CREATE TABLE IF NOT EXISTS finanzas 
               (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)''')
    db.commit()

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
                db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                           (f_txt, mes_f, tipo_f, cat_f, det_f, monto_f))
                db.commit()
                st.success("✅ Registro guardado con éxito.")
                st.rerun()

                st.markdown("---")

    # Mostrar Historial y Borrado
    try:
        df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
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
                            db.execute("DELETE FROM finanzas WHERE id = ?", (row['id'],))
                            db.commit()
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

    # --- LÓGICA DE COLORES Y SEMÁFOROS (NEXUS INTELLIGENCE) ---
    def analizar_glucosa_full(v, m):
        """Devuelve Estado, Color y Mensaje de alerta"""
        if "Ayunas" in m or "Antes" in m:
            if 70 <= v <= 100: return "🟢 NORMAL", "#1b5e20", "¡Excelente control!"
            elif 101 <= v <= 125: return "🟡 PRE-DIABETES", "#fbc02d", "Cuidado con la dieta."
            else: return "🔴 ALTO (REVISAR)", "#b71c1c", "Consulte a su médico."
        else: # Después de comer (Post-Prandial)
            if v < 140: return "🟢 NORMAL", "#1b5e20", "Buen manejo post-comida."
            elif 140 <= v <= 199: return "🟡 ELEVADO", "#fbc02d", "Monitoree la siguiente toma."
            else: return "🔴 CRÍTICO", "#b71c1c", "Alerta: Valor muy alto."

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
                # Insertamos datos incluyendo la nueva nota
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor, nota) VALUES (?,?,?,?,?)", 
                           (f_txt, h_txt, momento_g, valor_g, nota_g))
                db.commit()
                # Análisis inmediato
                estado, color, msn = analizar_glucosa_full(valor_g, momento_g)
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
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
    
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

        # A. GENERADOR DE PDF PROFESIONAL CON FIRMA QUEVEDO
        with col_pdf:
            if st.button("📄 GENERAR REPORTE PDF"):
                try:
                    pdf = FPDF()
                    pdf.add_page()
                    # Encabezado NEXUS PRO
                    pdf.set_font("Arial", 'B', 18)
                    pdf.set_text_color(33, 150, 243) # AzulNexus
                    pdf.cell(200, 10, txt="NEXUS PRO - REPORTE DE SALUD", ln=True, align='C')
                    pdf.set_font("Arial", size=10)
                    pdf.set_text_color(0)
                    pdf.cell(200, 10, txt=f"Generado el: {f_txt} {h_txt}", ln=True, align='C')
                    pdf.ln(10)

                    # Títulos de Tabla
                    pdf.set_font("Arial", 'B', 11)
                    pdf.set_fill_color(30, 30, 30) # Fondo oscuro
                    pdf.set_text_color(255) # Texto blanco
                    pdf.cell(30, 8, "FECHA", 1, 0, 'C', True)
                    pdf.cell(40, 8, "MOMENTO", 1, 0, 'C', True)
                    pdf.cell(25, 8, "VALOR", 1, 0, 'C', True)
                    pdf.cell(30, 8, "ESTADO", 1, 0, 'C', True)
                    pdf.cell(65, 8, "NOTA", 1, 1, 'C', True)

                    # Datos
                    pdf.set_font("Arial", size=10)
                    pdf.set_text_color(0)
                    for i, r in df_g.iterrows():
                        pdf.cell(30, 8, r['fecha'], 1)
                        pdf.cell(40, 8, r['momento'], 1)
                        pdf.cell(25, 8, f"{r['valor']} mg/dL", 1, 0, 'R')
                        # Análisis rápido para el PDF
                        est_pdf, _, _ = analizar_glucosa_full(r['valor'], r['momento'])
                        pdf.cell(30, 8, est_pdf, 1)
                        # Nota (cortar si es muy larga)
                        nota_pdf = str(r['nota']) if 'nota' in r else ""
                        pdf.cell(65, 8, nota_pdf[:35], 1, 1) # Muestra los primeros 35 caracteres

                    pdf.ln(15)
                    # FIRMA QUEVEDO AL FINAL DE CADA PÁGINA
                    pdf.set_font("Arial", 'I', 9)
                    pdf.cell(200, 10, txt="__________________________________________________________", ln=True, align='C')
                    pdf.cell(200, 5, txt="Este reporte es propiedad exclusiva de: LUIS RAFAEL QUEVEDO | 2026", ln=True, align='C')
                    
                    pdf_out = pdf.output(dest='S').encode('latin-1', 'replace')
                    st.download_button(label="📥 Descargar Reporte PDF", data=pdf_out, file_name=f"Glucosa_Quevedo_{f_txt.replace('/','-')}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Error generando PDF: {e}")

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
                    db.execute("DELETE FROM glucosa WHERE id = (SELECT MAX(id) FROM glucosa)")
                    db.commit()
                    st.success("✅ Último registro eliminado.")
                    st.rerun()
                
                # Opción para limpieza total con seguro
                if st.checkbox("⚠️ Confirmar vaciado total de glucosa"):
                    if st.button("🔥 BORRAR TODO EL HISTORIAL"):
                        db.execute("DELETE FROM glucosa")
                        db.commit()
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
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", 
                           (n_med, d_med, h_med))
                db.commit()
                st.success(f"✅ {n_med} añadida correctamente.")
                st.rerun()
            else:
                st.warning("⚠️ Escriba el nombre de la medicina.")

    st.markdown("---")
    st.subheader("📋 Medicinas en Inventario")

    # --- LISTADO CON BOTÓN DE BORRAR ---
    df_meds = pd.read_sql_query("SELECT * FROM medicamentos ORDER BY nombre ASC", db)
    
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
                        db.execute("DELETE FROM medicamentos WHERE id = ?", (row['id'],))
                        db.commit()
                        st.warning(f"Se eliminó {row['nombre']}.")
                        st.rerun()
                st.markdown("<hr style='margin:5px; border:0.5px solid #30363d;'>", unsafe_allow_html=True)
        
        # Opción de Limpieza Masiva
        st.markdown("<br>", unsafe_allow_html=True)
        if st.checkbox("⚠️ Habilitar vaciado total del botiquín"):
            if st.button("🔥 BORRAR TODAS LAS MEDICINAS"):
                db.execute("DELETE FROM medicamentos")
                db.commit()
                st.error("Botiquín vaciado por completo.")
                st.rerun()
    else:
        st.info("El botiquín está vacío. Registre sus medicinas arriba.")
# --- 11. MÓDULO: AGENDA DE CITAS (CON GESTIÓN DE BORRADO) ---
elif opcion == "📅 AGENDA":
    st.title("📅 Gestión de Citas Médicas - NEXUS PRO")
    st.markdown("---")
    
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
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", 
                           (doc, str(fec_c), mot))
                db.commit()
                st.success(f"✅ Cita con {doc} guardada para el {fec_c}")
                st.rerun()
            else:
                st.error("⚠️ Por favor, complete el nombre del Doctor y el Motivo.")

    st.markdown("---")
    st.subheader("📌 Citas Programadas")

    # --- LISTADO Y BORRADO DE CITAS ---
    df_citas = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
    
    if not df_citas.empty:
        # Mostramos las citas en un formato limpio
        for i, row in df_citas.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2, 3, 1])
                with c1:
                    st.markdown(f"**📅 {row['fecha']}**")
                    st.caption(f"Dr/Especialidad: {row['doctor']}")
                with c2:
                    st.write(f"📝 {row['motivo']}")
                with c3:
                    # Botón único para borrar esta cita específica
                    if st.button("🗑️ Borrar", key=f"del_cita_{row['id']}"):
                        db.execute("DELETE FROM citas WHERE id = ?", (row['id'],))
                        db.commit()
                        st.warning("Cita eliminada.")
                        st.rerun()
                        st.markdown("---")
        
        # Botón para limpiar toda la agenda de un solo golpe
        if st.checkbox("⚠️ Activar botón de limpieza total"):
            if st.button("🔥 BORRAR TODA LA AGENDA"):
                db.execute("DELETE FROM citas")
                db.commit()
                st.error("Agenda vaciada por completo.")
                st.rerun()
    else:
        st.info("No tiene citas pendientes en su agenda.")


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
