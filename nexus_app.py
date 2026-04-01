import streamlit as st
import pandas as pd
import datetime
import webbrowser
from fpdf import FPDF
import base64

# ==========================================
# 1. MOTOR DE LÓGICA INTEGRADA NEXUS (SIN CAMBIOS)
# ==========================================
class MotorNEXUS:
    def __init__(self):
        if 'presupuesto' not in st.session_state: st.session_state.presupuesto = 5000.0
        if 'gastos' not in st.session_state: st.session_state.gastos = []
        if 'glucosa_actual' not in st.session_state: st.session_state.glucosa_actual = 0.0
        self.ingresos = 8500.0

    def calcular_estado_ia(self):
        alertas = []
        total_gastos = sum(g['monto'] for g in st.session_state.gastos)
        
        # Lógica de Finanzas
        porc = (total_gastos / st.session_state.presupuesto) * 100 if st.session_state.presupuesto > 0 else 0
        if porc > 85: 
            alertas.append(f"⚠️ IA FINANZAS: Consumo del {porc:.1f}%. ¡Cuidado!")
        else:
            alertas.append(f"✅ IA FINANZAS: Presupuesto saludable ({porc:.1f}%)")
        
        # Lógica de Salud
        if st.session_state.glucosa_actual > 140:
            alertas.append(f"🚨 IA SALUD: Glucosa en {st.session_state.glucosa_actual} mg/dL. Nivel Crítico.")
        elif st.session_state.glucosa_actual > 0:
            alertas.append("✅ IA SALUD: Niveles de glucosa estables.")
            
        return alertas, total_gastos

# ==========================================
# 2. INTERFAZ WEB NEXUS (ADAPTADA)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO", layout="wide")
    nexus = MotorNEXUS()

    # --- ESTILO DARK MODE ---
    st.markdown("""
        <style>
        .main { background-color: #0d1117; color: white; }
        .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
        div[data-testid="stMetricValue"] { color: #58a6ff; }
        </style>
        """, unsafe_allow_html=True)

    # --- PANEL LATERAL ---
    with st.sidebar:
        st.title("NEXUS PRO 🧬")
        st.write("---")
        
        # WhatsApp Link
        msg = f"Reporte Nexus: Balance actual. Glucosa: {st.session_state.glucosa_actual}"
        wa_url = f"https://wa.me/?text={msg}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; background-color:#238636; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">📲 WHATSAPP ACTIVO</button></a>', unsafe_allow_html=True)
        
        st.write("")
        if st.button("📸 ACTIVAR ESCÁNER"):
            st.session_state.glucosa_actual = 155.0
            st.toast("Escáner: Se detectó Glucosa 155 mg/dL")

    # --- ÁREA CENTRAL ---
    st.title("SISTEMA INTEGRADO DE GESTIÓN")

    # SECCIÓN 1: CONFIGURACIÓN
    with st.expander("⚙️ CONFIGURACIÓN DE PRESUPUESTO", expanded=True):
        col_p1, col_p2 = st.columns([3, 1])
        nuevo_p = col_p1.number_input("DEFINA SU PRESUPUESTO (RD$):", value=st.session_state.presupuesto)
        if col_p2.button("FIJAR"):
            st.session_state.presupuesto = nuevo_p
            st.success(f"Presupuesto fijado en RD$ {nuevo_p}")

    # SECCIÓN 2: SALUD Y FINANZAS
    col_salud, col_fin = st.columns(2)

    with col_salud:
        st.subheader("🩺 CONTROL MÉDICO")
        glu_input = st.number_input("Glucosa (mg/dL):", value=float(st.session_state.glucosa_actual))
        med_input = st.text_input("Medicamento:")
        if st.button("REGISTRAR SALUD"):
            st.session_state.glucosa_actual = glu_input
            if med_input:
                st.session_state.gastos.append({'fecha': datetime.datetime.now().strftime('%d/%m %H:%M'), 'detalle': f"💊 {med_input}", 'monto': 0.0})
            st.session_state.gastos.append({'fecha': datetime.datetime.now().strftime('%d/%m %H:%M'), 'detalle': "🩸 Glucosa", 'monto': glu_input})

    with col_fin:
        st.subheader("📊 FINANZAS")
        alertas, total_g = nexus.calcular_estado_ia()
        balance = nexus.ingresos - total_g
        st.metric("Saldo Disponible", f"RD$ {balance:.2f}")
        
        gasto_val = st.number_input("Nuevo Gasto (RD$):", min_value=0.0)
        if st.button("AÑADIR GASTO"):
            fecha = datetime.datetime.now().strftime('%d/%m %H:%M')
            st.session_state.gastos.append({'fecha': fecha, 'detalle': "💸 Gasto", 'monto': gasto_val})
            st.rerun()

    # SECCIÓN 3: TABLA Y REPORTES
    st.write("---")
    if st.session_state.gastos:
        st.subheader("📝 HISTORIAL DE ACTIVIDAD")
        df = pd.DataFrame(st.session_state.gastos)
        st.table(df)
        
        # Botón para PDF (Versión Web)
        if st.button("📄 GENERAR REPORTE PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="REPORTE NEXUS PRO - SR. QUEVEDO", ln=True, align='C')
            pdf.output("reporte.pdf")
            with open("reporte.pdf", "rb") as f:
                st.download_button("⬇️ Descargar Reporte PDF", f, "Reporte_Nexus.pdf")

    # SECCIÓN 4: LOG DE IA
    st.subheader("🤖 REPORTE DE INTELIGENCIA NEXUS")
    for a in alertas:
        st.info(a)

if __name__ == "__main__":
    main()
