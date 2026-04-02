import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF

# ==========================================
# 1. MOTOR DE LÓGICA (BACKEND SIMULADO)
# ==========================================
class MotorNEXUS:
    def __init__(self):
        # Bases de Datos Independientes (como en su diagrama)
        if 'db_finanzas' not in st.session_state: st.session_state.db_finanzas = []
        if 'db_salud' not in st.session_state: st.session_state.db_salud = []
        if 'presupuesto' not in st.session_state: st.session_state.presupuesto = 5000.0
        self.ingresos = 8500.0

    def obtener_alertas_ia(self):
        total_g = sum(g['Monto'] for g in st.session_state.db_finanzas)
        alertas = []
        # Predicción Financiera
        if total_g > st.session_state.presupuesto * 0.8:
            alertas.append("⚠️ IA FINANZAS: Predicción de agotamiento de presupuesto próximamente.")
        # Análisis de Salud
        if any(s['Glucosa'] > 140 for s in st.session_state.db_salud):
            alertas.append("🚨 IA SALUD: Se detectaron picos de glucosa en el historial.")
        return alertas, total_g

# ==========================================
# 2. DASHBOARD PRINCIPAL (FRONTEND)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO - Arquitectura", layout="wide")
    nexus = MotorNEXUS()

    # --- ENCABEZADO ESTILO DASHBOARD ---
    st.title("🚀 NEXUS SMART: Dashboard Principal")
    alertas_ia, total_gastado = nexus.obtener_alertas_ia()
    
    # Métricas rápidas arriba
    c1, c2, c3 = st.columns(3)
    c1.metric("Balance Disponible", f"RD$ {nexus.ingresos - total_gastado}")
    c2.metric("Presupuesto Fijo", f"RD$ {st.session_state.presupuesto}")
    c3.metric("Estado General", "Estable" if not alertas_ia else "Atención")

    # --- SEPARACIÓN POR PESTAÑAS (Arquitectura de su diagrama) ---
    tab_fin, tab_salud, tab_ia = st.tabs(["💰 ÁREA FINANZAS", "🩺 ÁREA SALUD", "🤖 MOTOR IA & REPORTES"])

    # --- PESTAÑA FINANZAS ---
    with tab_fin:
        st.subheader("Gestión de Ingresos & Gastos")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            desc = st.text_input("Concepto:")
            monto = st.number_input("Monto (RD$):", min_value=0.0, key="f_monto")
            if st.button("AÑADIR GASTO"):
                st.session_state.db_finanzas.append({
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Concepto": desc,
                    "Monto": monto
                })
        with col_f2:
            st.write("Historial Financiero")
            if st.session_state.db_finanzas:
                st.table(pd.DataFrame(st.session_state.db_finanzas))
                if st.button("Limpiar Finanzas"):
                    st.session_state.db_finanzas = []
                    st.rerun()

    # --- PESTAÑA SALUD ---
    with tab_salud:
        st.subheader("Control Médico & Medicamentos")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            glu = st.number_input("Registro de Glucosa:", min_value=0)
            med = st.text_input("Medicamento / Cita:")
            if st.button("REGISTRAR EN SALUD"):
                st.session_state.db_salud.append({
                    "Fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Glucosa": glu,
                    "Detalle": med
                })
        with col_s2:
            st.write("Historial Médico")
            if st.session_state.db_salud:
                st.table(pd.DataFrame(st.session_state.db_salud))
                if st.button("Limpiar Salud"):
                    st.session_state.db_salud = []
                    st.rerun()

    # --- PESTAÑA IA & REPORTES ---
    with tab_ia:
        st.subheader("Modelos Predictivos & Generador PDF")
        for alerta in alertas_ia:
            st.warning(alerta)
        
        st.write("---")
        if st.button("📄 GENERAR REPORTE GLOBAL (PDF)"):
            st.info("Generando reporte basado en la base de datos central...")
            # Aquí iría la lógica del PDF que ya tenemos

    # --- SIDEBAR (CONEXIONES EXTERNAS) ---
    with st.sidebar:
        st.header("Conexiones")
        st.button("📲 API WHATSAPP")
        st.button("📷 ESCÁNER DOCUMENTOS")

if __name__ == "__main__":
    main()
