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
