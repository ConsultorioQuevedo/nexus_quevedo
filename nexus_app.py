import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF
import io

# ==========================================
# 1. MOTOR DE INTELIGENCIA Y PERSISTENCIA
# ==========================================
class MotorNEXUS:
    def __init__(self):
        # Inicialización de Bases de Datos en Memoria (Session State)
        if 'db_finanzas' not in st.session_state: st.session_state.db_finanzas = []
        if 'db_salud' not in st.session_state: st.session_state.db_salud = []
        if 'presupuesto' not in st.session_state: st.session_state.presupuesto = 10000.0
        if 'ingresos_totales' not in st.session_state: st.session_state.ingresos_totales = 0.0

    def calcular_metricas(self):
        gastos = sum(item['Monto'] for item in st.session_state.db_finanzas if item['Tipo'] == 'Gasto')
        ingresos = sum(item['Monto'] for item in st.session_state.db_finanzas if item['Tipo'] == 'Ingreso')
        balance = ingresos - gastos
        return balance, gastos, ingresos

    def ia_predictiva(self):
        alertas = []
        balance, gastos, _ = self.calcular_metricas()
        
        # Predicción Financiera
        if gastos > st.session_state.presupuesto * 0.9:
            alertas.append("⚠️ IA ALERTA: Has superado el 90% de tu presupuesto establecido.")
        elif gastos > st.session_state.presupuesto * 0.7:
            alertas.append("💡 IA SUGERENCIA: El ritmo de gasto indica que agotarás el presupuesto en 4 días.")
            
        # Predicción de Salud (Basado en Glucosa)
        registros_glu = [r['Valor'] for r in st.session_state.db_salud if r['Categoría'] == 'Glucosa']
        if registros_glu and registros_glu[-1] > 140:
            alertas.append("🚨 IA SALUD: Nivel de glucosa elevado. Se recomienda revisión médica inmediata.")
        
        return alertas

# ==========================================
# 2. INTERFAZ MODERNA (DASHBOARD)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO - Dashboard", layout="wide", page_icon="🧬")
    nexus = MotorNEXUS()

    # Estilo CSS para Elegancia Moderna
    st.markdown("""
        <style>
        .stApp { background-color: #0d1117; color: #c9d1d9; }
        .stButton>button { width: 100%; border-radius: 8px; border: 1px solid #30363d; background-color: #21262d; }
        .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🧬 NEXUS SMART: Dashboard Integral")
    
    # --- MÉTRICAS SUPERIORES ---
    balance, total_gastos, total_ingresos = nexus.calcular_metricas()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Balance Neto", f"RD$ {balance:,.2f}")
    m2.metric("Total Gastos", f"RD$ {total_gastos:,.2f}", delta_color="inverse")
    m3.metric("Presupuesto", f"RD$ {st.session_state.presupuesto:,.2f}")
    m4.metric("Salud Glucosa", f"{st.session_state.db_salud[-1]['Valor'] if st.session_state.db_salud else 'N/A'} mg/dL")

    # --- PESTAÑAS PRINCIPALES ---
    tab_fin, tab_salud, tab_ia = st.tabs(["💰 GESTIÓN FINANCIERA", "🩺 CONTROL DE SALUD", "🤖 IA & REPORTES"])

    # 1. SECCIÓN FINANZAS
    with tab_fin:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Registrar Movimiento")
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            concepto = st.text_input("Concepto (Ej: Supermercado)")
            monto = st.number_input("Monto RD$", min_value=0.0)
            if st.button("Añadir a Finanzas"):
                st.session_state.db_finanzas.append({
                    "ID": len(st.session_state.db_finanzas),
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y"),
                    "Tipo": tipo,
                    "Concepto": concepto,
                    "Monto": monto
                })
                st.rerun()
            
            st.write("---")
            st.session_state.presupuesto = st.number_input("Ajustar Presupuesto Mensual", value=st.session_state.presupuesto)

        with col2:
            st.subheader("Historial Financiero")
            if st.session_state.db_finanzas:
                df_fin = pd.DataFrame(st.session_state.db_finanzas)
                st.dataframe(df_fin[["Fecha", "Tipo", "Concepto", "Monto"]], use_container_width=True)
                if st.button("🗑️ Borrar Historial de Finanzas"):
                    st.session_state.db_finanzas = []
                    st.rerun()

    # 2. SECCIÓN SALUD
    with tab_salud:
        s_col1, s_col2 = st.columns([1, 2])
        with s_col1:
            st.subheader("Ingreso de Datos Médicos")
            cat_salud = st.selectbox("Categoría", ["Glucosa", "Medicamento", "Cita Médica"])
            detalle_salud = st.text_input("Detalle (Nombre de Medicina / Doctor)")
            valor_salud = st.number_input("Valor (Si es glucosa)", min_value=0.0)
            
            if st.button("Guardar en Salud"):
                st.session_state.db_salud.append({
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Categoría": cat_salud,
                    "Detalle": detalle_salud,
                    "Valor": valor_salud
                })
                st.rerun()
            
            st.write("---")
            if st.button("📷 SIMULAR ESCÁNER (OCR)"):
                # Simulación de guardado de escáner
                st.session_state.db_salud.append({
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y"),
                    "Categoría": "Escáner",
                    "Detalle": "Documento Analizado: Glucosa 125 mg/dL",
                    "Valor": 125.0
                })
                st.success("Documento escaneado y guardado en Salud.")

        with s_col2:
            st.subheader("Historial Médico")
            if st.session_state.db_salud:
                st.table(pd.DataFrame(st.session_state.db_salud))
                if st.button("🗑️ Borrar Historial de Salud"):
                    st.session_state.db_salud = []
                    st.rerun()

    # 3. SECCIÓN IA Y EXPORTACIÓN
    with tab_ia:
        st.subheader("Análisis Predictivo Nexus")
        alertas = nexus.ia_predictiva()
        for a in alertas:
            st.info(a) if "Sugerencia" in a else st.warning(a) if "Presupuesto" in a else st.error(a)

        st.write("---")
        st.subheader("Generación de Documentos")
        c_pdf, c_wa = st.columns(2)
        
        with c_pdf:
            if st.button("📄 GENERAR REPORTE PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt="REPORTE OFICIAL NEXUS PRO", ln=True, align='C')
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt=f"Balance Actual: RD$ {balance}", ln=True)
                # (Lógica simplificada de PDF)
                st.download_button("Descargar PDF", data=pdf.output(dest='S'), file_name="Reporte_Nexus.pdf")

        with c_wa:
            wa_msg = f"Reporte NEXUS: Balance RD$ {balance}. Glucosa: {st.session_state.db_salud[-1]['Valor'] if st.session_state.db_salud else 'N/A'}"
            wa_url = f"https://wa.me/?text={wa_msg.replace(' ', '%20')}"
            st.markdown(f'[📲 Enviar a WhatsApp]({wa_url})')

if __name__ == "__main__":
    main()
