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
st.set_page_config(page_title="SISTEMA QUEVEDO PRO", layout="wide")

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
