import streamlit as st
import sqlite3
import pandas as pd
import datetime
from fpdf import FPDF  # Para los reportes PDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", initial_sidebar_state="expanded")

# --- FUNCIÓN DE CONEXIÓN SEGURA ---
def conectar_db():
    return sqlite3.connect('nexus_data.db', timeout=20)

# --- CREACIÓN DE TABLAS (BLINDAJE) ---
with conectar_db() as conn:
    # Finanzas con columna de presupuesto
    conn.execute("""CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tipo TEXT, 
                  categoria TEXT, monto REAL, nota TEXT, presupuesto REAL)""")
    
    # Medicamentos
    conn.execute("""CREATE TABLE IF NOT EXISTS medicamentos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, dosis TEXT, 
                  horario TEXT, stock_actual REAL)""")
    
    # Agenda
    conn.execute("""CREATE TABLE IF NOT EXISTS agenda 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, 
                  asunto TEXT, lugar TEXT)""")
    
    # Salud
    conn.execute("""CREATE TABLE IF NOT EXISTS salud 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, glucosa INTEGER, notas TEXT)""")

# --- ESTRUCTURA DE NAVEGACIÓN ---
st.sidebar.title("🚀 SISTEMA QUEVEDO")
menu = st.sidebar.selectbox("SELECCIONE MÓDULO:", 
    ["🏠 Dashboard", "💰 Finanzas & Presupuesto", "🩺 Glucosa & Salud", "💊 Botiquín", "📅 Agenda"])

st.title(f"🚀 {menu}")
st.write(f"📅 {datetime.date.today().strftime('%d/%m/%Y')} | Usuario: Sr. Quevedo")
if menu == "💰 Finanzas & Presupuesto":
    # 1. Configurar Presupuesto Mensual
    presupuesto_fijo = st.number_input("Definir Presupuesto Mensual (RD$):", min_value=0.0, value=10000.0)

    # 2. Formulario de Registro
    with st.expander("➕ REGISTRAR MOVIMIENTO", expanded=False):
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo:", ["GASTO", "INGRESO"])
        monto = c2.number_input("Monto (RD$):", min_value=0.0)
        cat = st.selectbox("Categoría:", ["Salud", "Comida", "Servicios", "Pensión", "Otros"])
        nota = st.text_input("Detalle/Nota:")
        
        if st.button("💾 GUARDAR"):
            with conectar_db() as conn:
                conn.execute("INSERT INTO finanzas (fecha, tipo, categoria, monto, nota, presupuesto) VALUES (?,?,?,?,?,?)",
                            (str(datetime.date.today()), tipo, cat, monto, nota, presupuesto_fijo))
            st.success("Guardado correctamente.")
            st.rerun()

    # 3. Análisis y Semáforo de Presupuesto
    df_f = pd.read_sql_query("SELECT * FROM finanzas", conectar_db())
    if not df_f.empty:
        gastos_totales = df_f[df_f['tipo'] == "GASTO"]['monto'].sum()
        porcentaje = (gastos_totales / presupuesto_fijo) * 100 if presupuesto_fijo > 0 else 0
        
        st.metric("Gastos Totales", f"RD$ {gastos_totales:,.2f}")
        
        # Semáforo de Presupuesto
        if porcentaje < 70:
            st.success(f"🟢 Uso del Presupuesto: {porcentaje:.1f}% (Bajo Control)")
        elif porcentaje < 90:
            st.warning(f"🟡 Uso del Presupuesto: {porcentaje:.1f}% (Cuidado)")
        else:
            st.error(f"🔴 Uso del Presupuesto: {porcentaje:.1f}% (Límite Alcanzado)")

        st.dataframe(df_f.tail(10), use_container_width=True)
        
        id_del = st.number_input("ID para borrar:", min_value=1, step=1, key="del_f")
        if st.button("🗑️ BORRAR REGISTRO"):
            with conectar_db() as conn:
                conn.execute("DELETE FROM finanzas WHERE id = ?", (id_del,))
            st.rerun()
# --- MÓDULO 3: GLUCOSA & SALUD (CON SEMÁFORO Y PDF) ---
elif menu == "🩺 Glucosa & Salud":
    st.header("🩺 Control de Glucosa")
    
    col1, col2 = st.columns(2)
    valor = col1.number_input("Nivel de Glucosa (mg/dL):", min_value=0, value=100)
    nota_s = col2.text_input("Nota (ej: Ayunas):")
    
    if st.button("💾 REGISTRAR GLUCOSA"):
        with conectar_db() as conn:
            conn.execute("INSERT INTO salud (fecha, glucosa, notas) VALUES (?,?,?)",
                        (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), valor, nota_s))
        st.success("Dato guardado.")
        st.rerun()

    # Semáforo de Salud
    if valor < 70:
        st.error(f"🔴 NIVEL BAJO: {valor} mg/dL (Hipoglucemia)")
    elif valor <= 130:
        st.success(f"🟢 NIVEL NORMAL: {valor} mg/dL")
    elif valor <= 180:
        st.warning(f"🟡 NIVEL ELEVADO: {valor} mg/dL")
    else:
        st.error(f"🔴 NIVEL MUY ALTO: {valor} mg/dL (Peligro)")

    df_s = pd.read_sql_query("SELECT * FROM salud ORDER BY id DESC", conectar_db())
    if not df_s.empty:
        st.line_chart(df_s.set_index('fecha')['glucosa'])
        st.dataframe(df_s, use_container_width=True)
        
        # BOTÓN DE PDF (SALUD)
        if st.button("📄 GENERAR REPORTE PDF SALUD"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, "REPORTE DE SALUD - NEXUS QUEVEDO", ln=True, align='C')
            pdf.set_font("Arial", "", 12)
            for i, row in df_s.iterrows():
                pdf.cell(200, 10, f"Fecha: {row['fecha']} | Glucosa: {row['glucosa']} | Notas: {row['notas']}", ln=True)
            pdf.output("reporte_salud.pdf")
            st.success("Reporte PDF generado con éxito.")

        id_s = st.number_input("ID para borrar registro de salud:", min_value=1, step=1, key="del_s")
        if st.button("🗑️ BORRAR REGISTRO SALUD"):
            with conectar_db() as conn:
                conn.execute("DELETE FROM salud WHERE id = ?", (id_s,))
            st.rerun()

# --- MÓDULO 4: BOTIQUÍN ---
elif menu == "💊 Botiquín":
    st.header("💊 Control de Medicamentos")
    with st.expander("➕ REGISTRAR MEDICAMENTO"):
        nombre = st.text_input("Nombre:")
        dosis = st.text_input("Dosis:")
        horario = st.text_input("Horario:")
        if st.button("💾 GUARDAR MEDICAMENTO"):
            with conectar_db() as conn:
                conn.execute("INSERT INTO medicamentos (nombre, dosis, horario, stock_actual) VALUES (?,?,?,?)",
                            (nombre, dosis, horario, 0))
            st.rerun()
    
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", conectar_db())
    st.dataframe(df_m, use_container_width=True)
    id_m = st.number_input("ID para borrar medicamento:", min_value=1, step=1, key="del_m")
    if st.button("🗑️ ELIMINAR MEDICAMENTO"):
        with conectar_db() as conn:
            conn.execute("DELETE FROM medicamentos WHERE id = ?", (id_m,))
        st.rerun()

# --- MÓDULO 5: AGENDA (CON WHATSAPP Y PDF) ---
elif menu == "📅 Agenda":
    st.header("📅 Agenda de Citas")
    with st.expander("➕ AGENDAR CITA"):
        f_cita = st.date_input("Fecha:")
        h_cita = st.time_input("Hora:")
        asunto = st.text_input("Asunto:")
        lugar = st.text_input("Lugar:")
        if st.button("💾 GUARDAR CITA"):
            with conectar_db() as conn:
                conn.execute("INSERT INTO agenda (fecha, hora, asunto, lugar) VALUES (?,?,?,?)",
                            (str(f_cita), str(h_cita), asunto, lugar))
            st.rerun()

    df_a = pd.read_sql_query("SELECT * FROM agenda ORDER BY fecha ASC", conectar_db())
    if not df_a.empty:
        for i, row in df_a.iterrows():
            st.info(f"📌 {row['fecha']} - {row['hora']} | {row['asunto']}")
            # VÍNCULO WHATSAPP
            msg = f"Recordatorio: {row['asunto']} el {row['fecha']} en {row['lugar']}"
            st.markdown(f"[📲 Enviar WhatsApp](https://wa.me/?text={msg.replace(' ', '%20')})")
            
            if st.button(f"🗑️ Borrar Cita {row['id']}", key=f"cita_{row['id']}"):
                with conectar_db() as conn:
                    conn.execute("DELETE FROM agenda WHERE id = ?", (row['id'],))
                st.rerun()
        
        if st.button("📄 GENERAR PDF AGENDA"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(200, 10, "AGENDA DE CITAS - NEXUS QUEVEDO", ln=True, align='C')
            pdf.set_font("Arial", "", 12)
            for i, row in df_a.iterrows():
                pdf.cell(200, 10, f"{row['fecha']} {row['hora']} - {row['asunto']} ({row['lugar']})", ln=True)
            pdf.output("agenda_quevedo.pdf")
            st.success("PDF de Agenda listo.")            

# --- PIE DE PÁGINA / FIRMA DE AUTORES ---
st.markdown("---") # Línea divisoria decorativa

col_firma1, col_firma2 = st.columns(2)

with col_firma1:
    st.markdown("""
    **SISTEMA QUEVEDO INTEGRAL**  
    *Versión 3.0 Pro - 2026*  
    Desarrollado por: **Sr. Quevedo**  
    República Dominicana 🇩🇴
    """)

with col_firma2:
    st.markdown("""
    **COLABORACIÓN TÉCNICA:**  
    *Diseño Luis Rafael y Lógica:* **Gemini AI**  
    *Arquitectura de Datos:* **Luis Rafael Quevedo**  
    *Estado:* **Operativo y Funcional** ✅
    """)

st.caption("© Todos los derechos reservados - Control de Gestión Personal")
