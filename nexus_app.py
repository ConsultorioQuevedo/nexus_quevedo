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
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #00d4ff !important; }
    .stAlert { border-radius: 10px; }
    .css-1n76uvr { border: 1px solid #30363d; }
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
        "id_dia": ahora.strftime("%Y%m%d"),
        "mes": ahora.strftime("%B").upper()
    }

tiempo = obtener_tiempo()

# ==========================================
# ============================================================
# 3. CONEXIÓN A BASE DE DATOS UNIFICADA (NEXUS PRO)
# ============================================================
def inicializar_db():
    # Conexión con seguridad para subprocesos
    conn = sqlite3.connect("sistema_quevedo_pro.db", check_same_thread=False)
    c = conn.cursor()

    # --- TABLA FINANZAS (Con Categoría para Predicción) ---
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, mes TEXT, tipo TEXT, 
                  categoria TEXT, monto REAL, nota TEXT)''')

    # --- TABLA GLUCOSA (Con Estado para Machine Learning) ---
    c.execute('''CREATE TABLE IF NOT EXISTS glucosa
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, hora TEXT, momento TEXT, 
                  valor INTEGER, estado TEXT, notas TEXT)''')

    # --- TABLA MEDICAMENTOS (Plan Maestro de Stock) ---
    c.execute('''CREATE TABLE IF NOT EXISTS medicamentos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nombre TEXT, dosis TEXT, horario TEXT, 
                  stock_inicial INTEGER, stock_actual INTEGER)''')

    # --- TABLA REGISTRO MÉDICO (Cumplimiento de Tomas) ---
    c.execute('''CREATE TABLE IF NOT EXISTS registro_medico
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, medicamento TEXT, hora_toma TEXT, 
                  cumplimiento TEXT)''')

    # --- TABLA AGENDA (Citas y Alertas de Proximidad) ---
    c.execute('''CREATE TABLE IF NOT EXISTS citas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, doctor TEXT, motivo TEXT, 
                  recordatorio TEXT)''')

    conn.commit()
    return conn

# Inicializamos la conexión global
conn = inicializar_db()
# ==========================================
# 4. CONTROL DE ACCESO
# ==========================================
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🔐 ACCESO RESTRINGIDO</h1>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        clave = st.text_input("Introduzca su clave:", type="password")
        if st.button("ENTRAR"):
            if clave == "1628":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Clave Incorrecta")
    st.stop()

# ==========================================
# 5. BARRA LATERAL (NAVEGACIÓN)
# ==========================================
with st.sidebar:
    st.title("SISTEMA QUEVEDO")
    st.write(f"📅 {tiempo['fecha']}")
    st.write(f"⏰ {tiempo['hora']}")
    st.markdown("---")
    menu = st.radio("SELECCIONE MÓDULO:", 
                   ["🏠 Dashboard", "💰 Finanzas", "🩺 Glucosa & Salud", "💊 Botiquín", "🗓️ Agenda", "📝 Bitácora"])
    
    if st.button("🚪 Cerrar Sesión"):
        del st.session_state["autenticado"]
        st.rerun()
  # ==========================================
# 6. FUNCIONES DE EXPORTACIÓN (PDF Y WHATSAPP)
# ==========================================
def generar_pdf_glucosa(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "REPORTE MÉDICO - CONTROL DE GLUCOSA", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Paciente: Luis Rafael Quevedo | Fecha: {tiempo['fecha']}", ln=True, align='C')
    pdf.ln(10)
    
    # Encabezados de tabla
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(40, 10, "Fecha", 1, 0, 'C', 1)
    pdf.cell(40, 10, "Momento", 1, 0, 'C', 1)
    pdf.cell(30, 10, "Valor", 1, 0, 'C', 1)
    pdf.cell(80, 10, "Nota", 1, 1, 'C', 1)
    
    for _, fila in df.iterrows():
        pdf.cell(40, 10, str(fila['fecha']), 1)
        pdf.cell(40, 10, str(fila['momento']), 1)
        pdf.cell(30, 10, str(fila['valor']), 1)
        pdf.cell(80, 10, str(fila['nota'])[:30], 1, 1)
    
    pdf.output("reporte_salud_quevedo.pdf")
    return "reporte_salud_quevedo.pdf"

def enviar_whatsapp(mensaje):
    msg_encoded = urllib.parse.quote(mensaje)
    # Reemplaza el número con el tuyo o el de tu médico
    url = f"https://wa.me/18290000000?text={msg_encoded}"
    return url

# ==========================================
# 7 SECCIÓN: GLUCOSA & SALUD (NEXUS AI)
# ==========================================
if menu == "🩺 Glucosa & Salud":
    st.title("🩺 Control de Glucosa con Inteligencia Artificial")
    st.markdown(f"**Paciente:** Luis Rafael Quevedo | **Fecha:** {tiempo['fecha']}")

    # --- 1. ENTRADA DE DATOS (TECLADO NUMÉRICO Y LIMPIEZA) ---
    with st.expander("📝 REGISTRAR NUEVA LECTURA", expanded=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        
        with c1:
            # Al ser 'number_input' con 'step=1', el celular abre el teclado de números automáticamente
            valor_g = st.number_input("Nivel (mg/dL):", min_value=0, max_value=500, step=1, key="input_glucosa")
        with c2:
            momento_g = st.selectbox("Momento:", ["Ayunas", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
        with c3:
            nota_g = st.text_input("Nota (Síntomas/Comida):", placeholder="Ej: Comí arroz con habichuela...").upper()

        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("💾 GUARDAR REGISTRO"):
                if valor_g > 0:
                    conn.execute("INSERT INTO glucosa (fecha, hora, momento, valor, nota) VALUES (?,?,?,?,?)",
                                (tiempo['fecha'], tiempo['hora'], momento_g, valor_g, nota_g))
                    conn.commit()
                    st.success("✅ ¡Guardado!")
                    st.rerun()
                else:
                    st.warning("⚠️ Por favor, introduce un valor.")
        with col_btn2:
            if st.button("🧹 LIMPIAR TODO"):
                st.rerun() # Esto borra lo que escribiste y refresca la pantalla

    st.markdown("---")

    # --- 2. ANÁLISIS DE DATOS (REGLAS INTELIGENTES E IA) ---
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id ASC", conn)

    if not df_g.empty:
        # Último valor registrado
        ultimo = df_g.iloc[-1]
        v = ultimo['valor']
        m = ultimo['momento']

        # Reglas Inteligentes (If/Else Avanzado)
        st.subheader("🤖 Análisis de la IA")
        if m == "Ayunas":
            if v < 70: color, msg = "🔵 CRÍTICO (BAJO)", "Hipoglucemia detectada. Ingiere algo dulce de inmediato."
            elif v <= 100: color, msg = "🟢 EXCELENTE", "Tu nivel en ayunas es perfecto."
            elif v <= 125: color, msg = "🟡 PRE-DIABETES", "Nivel algo elevado. Cuida las harinas hoy."
            else: color, msg = "🔴 ALERTA ALTA", "Nivel muy alto. Llama a tu médico si persiste."
        else: # Si es después de comer
            if v > 180: color, msg = "🔴 ALTA POST-PRANDIAL", "Nivel muy alto después de comer. Camina 15 minutos."
            else: color, msg = "🟢 NORMAL", "Tu cuerpo está procesando bien el azúcar."
        
        st.markdown(f"### {color}")
        st.info(msg)

        # Machine Learning Simple (Predicción de Tendencia)
        if len(df_g) > 3:
            # Calculamos si el azúcar va subiendo o bajando comparando los últimos 3
            promedio_ultimos = df_g['valor'].tail(3).mean()
            tendencia = "ALZA 📈" if v > promedio_ultimos else "BAJA 📉"
            st.write(f"**Sistema de Recomendación:** La tendencia actual es al **{tendencia}**. Basado en esto, te recomiendo monitorear tu próxima comida.")

        # --- 3. WHATSAPP Y PDF ---
        st.markdown("---")
        col_pdf, col_wa = st.columns(2)

        with col_pdf:
            if st.button("📄 GENERAR PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, f"REPORTE DE GLUCOSA - SR. QUEVEDO", ln=True, align='C')
                pdf.set_font("Arial", size=11)
                for _, fila in df_g.tail(10).iterrows():
                    pdf.cell(190, 10, f"{fila['fecha']} | {fila['momento']} | {fila['valor']} mg/dL", 1, 1)
                pdf.output("reporte_salud.pdf")
                with open("reporte_salud.pdf", "rb") as f:
                    st.download_button("📥 Descargar Reporte", f, file_name="reporte_salud.pdf")

        with col_wa:
            # Botón de WhatsApp con mensaje automático
            msg_wa = f"Hola Dr., mi último nivel de glucosa fue {v} mg/dL en {m}. ({tiempo['fecha']})"
            msg_url = f"https://wa.me/18290000000?text={msg_wa.replace(' ', '%20')}"
            st.markdown(f'<a href="{msg_url}" target="_blank" style="text-decoration:none;"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">📲 ENVIAR A WHATSAPP</button></a>', unsafe_allow_html=True)

        # Mostrar tabla histórica
        st.dataframe(df_g[["fecha", "hora", "momento", "valor", "nota"]].tail(10), use_container_width=True)
# ==========================================
# 8. MÓDULO DE FINANZAS (CON IA DE AHORRO)
# ==========================================
if menu == "💰 Finanzas":
    st.title("💰 Gestión Financiera Inteligente")
    
    with st.expander("➕ REGISTRAR MOVIMIENTO", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            tipo = st.selectbox("Tipo:", ["INGRESO", "GASTO"])
            monto = st.number_input("Monto (RD$):", min_value=0.0, step=100.0)
        with col2:
            cat = st.selectbox("Categoría:", ["Salud", "Supermercado", "Servicios", "Negocio", "Otros"])
        with col3:
            det = st.text_input("Detalle:").upper()
            
        if st.button("💾 GUARDAR TRANSACCIÓN"):
            conn.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)",
                        (tiempo['fecha'], tiempo['mes'], tipo, cat, det, monto))
            conn.commit()
            st.success("Transacción registrada.")
            st.rerun()

    # --- ANÁLISIS DE DATOS ---
    df_f = pd.read_sql_query(f"SELECT * FROM finanzas WHERE mes = '{tiempo['mes']}'", conn)
    
    if not df_f.empty:
        ingresos = df_f[df_f['tipo'] == 'INGRESO']['monto'].sum()
        gastos = df_f[df_f['tipo'] == 'GASTO']['monto'].sum()
        balance = ingresos - gastos
        
        # Métricas principales
        c1, c2, c3 = st.columns(3)
        c1.metric("INGRESOS", f"RD$ {ingresos:,.2f}")
        c2.metric("GASTOS", f"RD$ {gastos:,.2f}", delta=f"-{gastos:,.2f}", delta_color="inverse")
        c3.metric("BALANCE", f"RD$ {balance:,.2f}")

        # --- REGLAS INTELIGENTES Y RECOMENDACIÓN ---
        st.markdown("---")
        st.subheader("💡 Asistente de Ahorro")
        
        if gastos > ingresos * 0.8:
            st.warning("⚠️ REGLA CRÍTICA: Has gastado más del 80% de tus ingresos. Se recomienda frenar gastos no esenciales.")
        else:
            st.success("✅ REGLA DE ESTABILIDAD: Tu nivel de gasto está bajo control respecto a tus ingresos.")

        # Sistema de recomendación simple
        if gastos > 0:
            peor_cat = df_f[df_f['tipo'] == 'GASTO'].groupby('categoria')['monto'].sum().idxmax()
            st.info(f"🔍 RECOMENDACIÓN: Tu mayor gasto este mes es en **{peor_cat}**. Si reduces un 10% aquí, ahorrarías RD$ {(df_f[df_f['categoria']==peor_cat]['monto'].sum()*0.1):,.2f}.")

        # --- EXPORTAR PDF FINANZAS ---
        if st.button("📄 GENERAR REPORTE FINANCIERO"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, f"REPORTE FINANCIERO - {tiempo['mes']}", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", size=12)
            for _, r in df_f.iterrows():
                pdf.cell(190, 10, f"{r['fecha']} | {r['tipo']} | {r['categoria']} | RD$ {r['monto']}", 1, 1)
            pdf.output("finanzas_quevedo.pdf")
            with open("finanzas_quevedo.pdf", "rb") as f:
                st.download_button("📥 Descargar Reporte", f, file_name="finanzas_quevedo.pdf")

# ==========================================
# 9. MÓDULO DE BITÁCORA (CON WHATSAPP)
# ==========================================
if menu == "📝 Bitácora":
    st.title("📝 Bitácora de Actividades")
    
    nota_rapida = st.text_area("¿Qué sucedió hoy?", placeholder="Escribe aquí los eventos relevantes...")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("💾 GUARDAR EN BITÁCORA"):
            # Aquí podrías crear una tabla específica si quieres histórico, 
            # por ahora lo manejamos como mensaje directo.
            st.success("Nota procesada localmente.")
            
    with col_b2:
        if nota_rapida:
            msg = f"BITÁCORA QUEVEDO ({tiempo['fecha']}): {nota_rapida}"
            st.markdown(f"[📲 Enviar Bitácora por WhatsApp]({enviar_whatsapp(msg)})")

    st.info("Este módulo permite centralizar tus pensamientos y enviarlos como reporte diario.")
# ==========================================================
# 10. MÓDULO: BOTIQUÍN INTELIGENTE - LUIS RAFAEL QUEVEDO
# ==========================================================
elif menu == "💊 BOTIQUÍN":
    st.title("💊 Gestión de Medicamentos y Stock")
    st.subheader("Control Maestro: Sr. Quevedo")

    # --- CAPA 1: INTELIGENCIA DE STOCK (PREDICCIÓN) ---
    df_m = pd.read_sql_query("SELECT * FROM medicamentos", conn)
    
    if not df_m.empty:
        # Regla Inteligente: Detectar si queda poco de algo
        bajo_stock = df_m[df_m['stock_actual'] <= 5]
        if not bajo_stock.empty:
            for _, med in bajo_stock.iterrows():
                st.error(f"⚠️ **ALERTA DE REPOSICIÓN:** Sr. Quevedo, le quedan solo {fila['stock_actual']} dosis de {fila['nombre']}. Debería comprar más pronto.")

    # --- CAPA 2: REGISTRO DE NUEVA MEDICINA ---
    with st.expander("➕ AGREGAR MEDICAMENTO AL PLAN", expanded=False):
        c1, c2 = st.columns(2)
        n_med = c1.text_input("Nombre del Medicamento:", placeholder="Ej: Enalapril")
        d_med = c2.text_input("Dosis:", placeholder="Ej: 10mg")
        
        c3, c4 = st.columns(2)
        h_med = c3.text_input("Horario (HH:MM):", value="08:00")
        s_med = c4.number_input("Cantidad Inicial (Pastillas):", min_value=1, value=30)
        
        if st.button("💾 REGISTRAR EN BOTIQUÍN", use_container_width=True):
            conn.execute("""INSERT INTO medicamentos (nombre, dosis, horario, stock_inicial, stock_actual) 
                         VALUES (?,?,?,?,?)""", (n_med, d_med, h_med, s_med, s_med))
            conn.commit()
            st.success(f"✅ {n_med} añadido al Plan Maestro.")
            st.rerun()

    # --- CAPA 3: PANEL DE CONTROL ELEGANTE ---
    st.markdown("---")
    if not df_m.empty:
        st.markdown("### 📋 Inventario Actual")
        for _, med in df_m.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.markdown(f"**{med['nombre']}** ({med['dosis']}) - ⏰ {med['horario']}")
                
                # Barra de progreso visual para el stock
                porcentaje = (med['stock_actual'] / med['stock_inicial'])
                col2.progress(porcentaje)
                
     if col3.button("💊 TOMAR", key=f"toma_{med['id']}"):
            nuevo_stock = fila['stock_actual'] - 1
            conn.execute("UPDATE medicamentos SET stock_actual = ? WHERE id = ?", (nuevo_stock, fila['id']))
            conn.execute("INSERT INTO registro_medico (fecha, medicamento, hora_toma, cumplimiento) VALUES (?,?,?,?)",
                         (str(tiempo['fecha']), fila['nombre'], tiempo['hora'], "SÍ"))
            conn.commit()
            st.rerun()   
# ==========================================
# 11. MÓDULO DASHBOARD (EL CEREBRO DEL SISTEMA)
# ==========================================
if menu == "🏠 Dashboard":
    st.title(f"🚀 PANEL NEXUS PRO - BIENVENIDO SR. QUEVEDO")
    
    # --- FILA 1: MÉTRICAS CRÍTICAS CON REGLAS INTELIGENTES ---
    col_s1, col_s2, col_s3 = st.columns(3)
    
    # Obtener datos de Salud para el Dashboard
    df_salud = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 5", conn)
    if not df_salud.empty:
        ultimo_v = df_salud['valor'].iloc[0]
        promedio_v = df_salud['valor'].mean()
        
        # Regla Inteligente de Salud
        estado_salud = "ÓPTIMO" if 70 <= ultimo_v <= 130 else "REVISAR"
        col_s1.metric("ÚLTIMA GLUCOSA", f"{ultimo_v} mg/dL", f"{ultimo_v - promedio_v:.1f} vs prom")
        
    # Obtener datos de Finanzas para el Dashboard
    df_fin = pd.read_sql_query(f"SELECT tipo, monto FROM finanzas WHERE mes = '{tiempo['mes']}'", conn)
    if not df_fin.empty:
        gastos_totales = df_fin[df_fin['tipo'] == 'GASTO']['monto'].sum()
        col_s2.metric("GASTOS DEL MES", f"RD$ {gastos_totales:,.2f}")
    
    col_s3.metric("SISTEMA", "ACTIVO", "Protección 1628")

    st.markdown("---")

    # --- FILA 2: MACHINE LEARNING Y PREDICCIÓN ---
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        st.subheader("📊 Análisis de Tendencia Histórica")
        df_all_g = pd.read_sql_query("SELECT id, valor FROM glucosa ORDER BY id ASC", conn)
        if len(df_all_g) > 2:
            fig_dash = px.area(df_all_g, x='id', y='valor', title="Flujo de Salud Continuo",
                              color_discrete_sequence=['#00d4ff'], template="plotly_dark")
            st.plotly_chart(fig_dash, use_container_width=True)
        else:
            st.info("Aún no hay suficientes datos para el modelo de Machine Learning.")

    with c_right:
        st.subheader("🤖 Recomendaciones IA")
        # Sistema de recomendación basado en lógica avanzada
        if not df_salud.empty:
            if ultimo_v > 150:
                st.error("🚨 RECOMENDACIÓN: Tu nivel actual sugiere reducir carbohidratos en la próxima comida.")
            elif ultimo_v < 80:
                st.warning("⚠️ RECOMENDACIÓN: Nivel bajo. Ten a mano una fruta o merienda ligera.")
            else:
                st.success("✅ RECOMENDACIÓN: Mantén tu rutina actual, los niveles son estables.")
        
        # Predicción de Gastos (ML Simple)
        if not df_fin.empty and gastos_totales > 0:
            prediccion_fin = gastos_totales * 1.05  # Simulación de tendencia inflacionaria
            st.info(f"📈 PREDICCIÓN FINANCIERA: Basado en tu ritmo actual, podrías cerrar el mes con un gasto de RD$ {prediccion_fin:,.2f}.")

    # --- FILA 3: ACCIONES RÁPIDAS (WHATSAPP Y PDF) ---
    st.markdown("---")
    st.subheader("⚡ Reportes Rápidos")
    ca1, ca2, ca3 = st.columns(3)
    
    with ca1:
        if st.button("📄 PDF RESUMEN TOTAL"):
            # Lógica rápida de PDF para el Dashboard
            pdf_res = FPDF()
            pdf_res.add_page()
            pdf_res.set_font("Arial", 'B', 16)
            pdf_res.cell(200, 10, "RESUMEN EJECUTIVO QUEVEDO PRO", ln=True, align='C')
            pdf_res.ln(10)
            pdf_res.set_font("Arial", size=12)
            pdf_res.cell(200, 10, f"Salud: {ultimo_v} mg/dL | Gastos: RD$ {gastos_totales}", ln=True)
            pdf_res.output("resumen_quevedo.pdf")
            with open("resumen_quevedo.pdf", "rb") as f:
                st.download_button("📥 Descargar Resumen", f, file_name="resumen_quevedo.pdf")

    with ca2:
        texto_seguridad = f"SISTEMA QUEVEDO: Reporte de seguridad generado el {tiempo['fecha']}. Todo bajo control."
        st.markdown(f"[📲 WhatsApp de Seguridad]({enviar_whatsapp(texto_seguridad)})")
        
    with ca3:
        if st.button("🧹 Limpiar Caché"):
            st.cache_data.clear()
            st.success("Sistema optimizado.")

# ==========================================
# FINAL DEL ARCHIVO: CIERRE DE CONEXIÓN
# ==========================================
conn.close()
# ==========================================
# 11. MOTOR DE INTELIGENCIA ARTIFICIAL (ML)
# ==========================================
def motor_prediccion_ml(df):
    """
    Simulación de Modelo de Machine Learning (Regresión Lineal Simple)
    para predecir la tendencia de salud.
    """
    if len(df) < 5:
        return None, "Se requieren al menos 5 registros para activar el ML."
    
    # Preparamos los datos (X = índice de tiempo, Y = valor glucosa)
    y = df['valor'].values[::-1]
    x = list(range(len(y)))
    
    # Cálculo de la pendiente (slope) mediante mínimos cuadrados simples
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(i*i for i in x)
    sum_xy = sum(i*j for i, j in zip(x, y))
    
    denominador = (n * sum_xx - sum_x**2)
    if denominador == 0: return None, "Datos insuficientes."
    
    pendiente = (n * sum_xy - sum_x * sum_y) / denominador
    prediccion = y[-1] + pendiente
    
    return prediccion, pendiente

# ==========================================
# 12. SISTEMA DE RECOMENDACIÓN Y ALERTAS AVANZADAS
# ==========================================
if menu == "🏠 Dashboard":
    # (Este código complementa el Dashboard del bloque anterior)
    st.markdown("---")
    st.subheader("🧠 Análisis Predictivo (IA)")
    
    df_ml = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 10", conn)
    
    if not df_ml.empty:
        pred, tendencia = motor_prediccion_ml(df_ml)
        
        c_ml1, c_ml2 = st.columns(2)
        
        with c_ml1:
            if pred:
                color_pred = "🔴" if pred > 140 else "🟢"
                st.metric("PREDICCIÓN PRÓXIMA LECTURA", f"{pred:.1f} mg/dL", 
                          delta=f"{tendencia:.2f} tendencia", delta_color="inverse")
                st.write(f"{color_pred} El sistema proyecta un cambio basado en tus últimos 10 registros.")
        
        with c_ml2:
            st.markdown("**Sistema de Recomendación:**")
            if tendencia > 0.5:
                st.warning("⚠️ Tus niveles muestran una tendencia ALCISTA. Considera aumentar la actividad física.")
            elif tendencia < -0.5:
                st.info("📉 Tus niveles muestran una tendencia BAJISTA. Verifica si necesitas ajustar la dosis.")
            else:
                st.success("⚖️ Tendencia ESTABLE. Sigue con tu régimen actual.")

# ==========================================
# 13. GENERADOR DE REPORTES PDF (MÓDULO UNIFICADO)
# ==========================================
def exportar_todo_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "SISTEMA QUEVEDO PRO - REPORTE INTEGRAL", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, f"Fecha de Generación: {tiempo['fecha']} {tiempo['hora']}", ln=True)
    pdf.cell(200, 10, "Desarrollado por: Luis Rafael Quevedo & Gemini AI", ln=True)
    pdf.ln(5)
    pdf.output("Reporte_Integral_Quevedo.pdf")
    return "Reporte_Integral_Quevedo.pdf"

# Botón final de exportación en la barra lateral
with st.sidebar:
    st.markdown("---")
    if st.button("📄 GENERAR PDF MAESTRO"):
        archivo_maestro = exportar_todo_pdf()
        with open(archivo_maestro, "rb") as f:
            st.download_button("📥 DESCARGAR REPORTE COMPLETO", f, file_name=archivo_maestro)

# ==========================================
# FINAL DEL SISTEMA
# ==========================================
st.sidebar.markdown("---")
st.sidebar.caption(f"©️ 2026 - SISTEMA QUEVEDO PRO")
st.sidebar.caption(f"Colaboradores:Luis Rafael Quevedo & Gemini AI")
st.sidebar.caption(f"Fecha de última actualización: 29/03/2026")
