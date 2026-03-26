import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import os
from fpdf import FPDF

# --- 1. CLASE PARA REPORTES PDF ---
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 10)
        self.set_text_color(120)
        # Nombre del autor en el pie de página
        self.cell(0, 10, 'Luis Rafael Quevedo', 0, 0, 'C')

# --- 2. CONFIGURACIÓN DE PÁGINA Y ESTILO PROFESIONAL ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0d1117; }
    div[data-testid="stForm"], .balance-box { 
        background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; 
        padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .neon-verde { color: #40E0D0; font-weight: 800; font-size: 2rem; }
    .neon-rojo { color: #FF7F50; font-weight: 800; font-size: 2rem; }
    .stButton > button { border-radius: 10px; font-weight: 700; height: 45px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE SISTEMA ---
def obtener_tiempo():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y")

def iniciar_base_datos():
    conn = sqlite3.connect("nexus_final_v11.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS salud (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, tipo TEXT, valor TEXT)')
    conn.commit()
    return conn

db = iniciar_base_datos()
f_s, h_s, mes_s = obtener_tiempo()

# --- 4. CONTROL DE ACCESO (CORRECCIÓN DEL ERROR DE LA FOTO) ---
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align:center; color:white;'>🌐 NEXUS QUEVEDO</h1>", unsafe_allow_html=True)
    
    # El formulario DEBE contener el botón de envío para funcionar
    with st.form("bloque_seguridad"):
        clave = st.text_input("Clave de Acceso:", type="password")
        boton_entrar = st.form_submit_button("ACCEDER AL SISTEMA")
        
        if boton_entrar:
            if clave == "admin123":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta. Intente de nuevo.")
    st.stop()

# --- 5. INTERFAZ DE NAVEGACIÓN ---
with st.sidebar:
    st.title("🌐 NEXUS PRO")
    opcion = st.radio("MENÚ PRINCIPAL", ["💰 FINANZAS", "🩺 SALUD", "📝 BITÁCORA"])
    st.markdown("---")
    if st.button("SALIR"):
        del st.session_state["autenticado"]
        st.rerun()

# --- 6. MÓDULO DE FINANZAS ---
if opcion == "💰 FINANZAS":
    st.title("💰 Gestión de Finanzas")
    
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    total = df_f['monto'].sum() if not df_f.empty else 0.0
    gastos = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_s)]['monto'].sum()) if not df_f.empty else 0.0

    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='balance-box'><h3>Capital Total</h3><div class='neon-verde'>RD$ {total:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='balance-box'><h3>Gastos de {mes_s}</h3><div class='neon-rojo'>RD$ {gastos:,.2f}</div></div>", unsafe_allow_html=True)

    with st.form("nuevo_movimiento"):
        st.subheader("Registrar Ingreso/Gasto")
        col_a, col_b, col_c = st.columns(3)
        t = col_a.selectbox("Tipo", ["GASTO", "INGRESO"])
        d = col_b.text_input("Detalle").upper()
        m = col_c.number_input("Monto RD$", min_value=0.0)
        if st.form_submit_button("GUARDAR EN BASE DE DATOS"):
            monto_final = -m if t == "GASTO" else m
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, detalle, monto) VALUES (?,?,?,?,?)", (f_s, mes_s, t, d, monto_final))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.subheader("Historial")
        st.dataframe(df_f[["fecha", "tipo", "detalle", "monto"]], use_container_width=True)

# --- 7. MÓDULO DE SALUD ---
elif opcion == "🩺 SALUD":
    st.title("🩺 Control de Salud")
    
    with st.form("toma_salud"):
        col1, col2 = st.columns(2)
        tipo_s = col1.selectbox("Tipo de Medida", ["GLUCOSA", "PRESIÓN", "PESO"])
        valor_s = col2.text_input("Valor (ej: 110, 120/80)")
        if st.form_submit_button("REGISTRAR MEDIDA"):
            db.execute("INSERT INTO salud (fecha, hora, tipo, valor) VALUES (?,?,?,?)", (f_s, h_s, tipo_s, valor_s))
            db.commit(); st.rerun()

    df_s = pd.read_sql_query("SELECT * FROM salud ORDER BY id DESC", db)
    if not df_s.empty:
        st.table(df_s[["fecha", "hora", "tipo", "valor"]].head(10))

# --- 8. MÓDULO DE BITÁCORA (PDF Y BORRADO) ---
elif opcion == "📝 BITÁCORA":
    st.title("📝 Bitácora de Notas")
    
    nota = st.text_area("¿Qué tienes en mente hoy?", height=150)
    if st.button("💾 GUARDAR NOTA"):
        if nota.strip():
            with open("notas_quevedo.txt", "a", encoding="utf-8") as f:
                f.write(f"[{f_s} {h_s}]: {nota.strip()}\n\n")
            st.success("Nota guardada."); st.rerun()

    st.markdown("---")
    
    if os.path.exists("notas_quevedo.txt"):
        with open("notas_quevedo.txt", "r", encoding="utf-8") as f:
            contenido = f.read()
    else:
        contenido = ""

    if contenido:
        col_p, col_b, _ = st.columns([1, 1, 2])
        
        with col_p:
            reporte = PDF()
            reporte.add_page()
            reporte.set_font("Arial", 'B', 16); reporte.cell(190, 10, "BITÁCORA NEXUS", ln=True, align='C'); reporte.ln(10)
            reporte.set_font("Arial", '', 12); reporte.multi_cell(190, 8, contenido)
            st.download_button("📄 EXPORTAR PDF", reporte.output(dest='S').encode('latin-1', errors='replace'), "Bitacora.pdf")

        with col_b:
            if st.button("🗑️ BORRAR TODO"):
                if os.path.exists("notas_quevedo.txt"): os.remove("notas_quevedo.txt")
                st.rerun()

        st.text_area("Contenido actual:", contenido, height=300)
    else:
        st.info("No hay notas registradas.")
