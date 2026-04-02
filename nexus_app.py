import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from fpdf import FPDF

# ==========================================
# 1. ARQUITECTURA DE DATOS (BACKEND SIMULADO)
# ==========================================
class BackendNEXUS:
    def __init__(self):
        # Bases de Datos Independientes según su diagrama
        if 'db_finanzas' not in st.session_state: st.session_state.db_finanzas = []
        if 'db_salud_clinica' not in st.session_state: st.session_state.db_salud_clinica = []
        if 'db_citas' not in st.session_state: st.session_state.db_citas = []
        if 'presupuesto' not in st.session_state: st.session_state.presupuesto = 5000.0

    def calcular_balance(self):
        ingresos = sum(f['Monto'] for f in st.session_state.db_finanzas if f['Tipo'] == 'Ingreso')
        gastos = sum(f['Monto'] for f in st.session_state.db_finanzas if f['Tipo'] == 'Gasto')
        return ingresos, gastos, ingresos - gastos

# ==========================================
# 2. MOTOR DE IA Y REPORTES
# ==========================================
def generar_texto_reporte():
    ahora = datetime.datetime.now().strftime("%d/%m/%Y")
    reporte = f"🧬 *REPORTE NEXUS PRO - {ahora}*\n\n"
    
    reporte += "🩺 *SALUD Y MEDICAMENTOS:*\n"
    if st.session_state.db_salud_clinica:
        for r in st.session_state.db_salud_clinica:
            reporte += f"- {r['Detalle']}: {r['Valor']}\n"
    else: reporte += "- Sin registros.\n"
    
    reporte += "\n📅 *CITAS PENDIENTES:*\n"
    for c in st.session_state.db_citas:
        reporte += f"- {c['Fecha']}: {c['Doctor']}\n"
        
    return reporte

# ==========================================
# 3. DASHBOARD PRINCIPAL (INTERFAZ)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO", layout="wide")
    backend = BackendNEXUS()
    
    # --- CABECERA ESTILO DASHBOARD ---
    ing, gas, bal = backend.calcular_balance()
    st.title("🚀 NEXUS SMART: Dashboard Principal")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance Total", f"RD$ {bal:,.2f}")
    c2.metric("Ingresos", f"RD$ {ing:,.2f}", delta_color="normal")
    c3.metric("Gastos", f"RD$ {gas:,.2f}", delta="-", delta_color="inverse")
    c4.metric("Presupuesto", f"RD$ {st.session_state.presupuesto:,.2f}")

    # --- NAVEGACIÓN POR MÓDULOS ---
    tab_fin, tab_salud, tab_citas, tab_export = st.tabs([
        "💰 FINANZAS (Ingresos/Gastos)", 
        "🩺 SALUD (Glucosa/Meds)", 
        "📅 CITAS MÉDICAS",
        "📤 REPORTES & ENVÍO"
    ])

    # --- MÓDULO FINANZAS ---
    with tab_fin:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Nuevo Registro")
            t_mov = st.radio("Tipo de Movimiento", ["Gasto", "Ingreso"])
            conc = st.text_input("Concepto:")
            mont = st.number_input("Monto RD$:", min_value=0.0)
            if st.button("Ejecutar Transacción"):
                st.session_state.db_finanzas.append({"Tipo": t_mov, "Concepto": conc, "Monto": mont, "Fecha": datetime.datetime.now().strftime("%d/%m %H:%M")})
                st.rerun()
        with col2:
            st.subheader("Historial de Caja")
            if st.session_state.db_finanzas:
                st.table(pd.DataFrame(st.session_state.db_finanzas))
                if st.button("🗑️ Borrar Todo Finanzas"):
                    st.session_state.db_finanzas = []
                    st.rerun()

    # --- MÓDULO SALUD ---
    with tab_salud:
        s_col1, s_col2 = st.columns([1, 2])
        with s_col1:
            st.subheader("Clínica")
            s_tipo = st.selectbox("Categoría", ["Glucosa", "Medicamento"])
            s_val = st.text_input("Valor/Nombre:")
            if st.button("Guardar en Salud"):
                st.session_state.db_salud_clinica.append({"Categoría": s_tipo, "Detalle": s_tipo, "Valor": s_val})
            
            st.write("---")
            if st.button("📷 ESCÁNER DE DOCUMENTOS"):
                st.info("Escaneando... Se detectó Glucosa: 115 mg/dL")
                st.session_state.db_salud_clinica.append({"Categoría": "Escáner", "Detalle": "Glucosa", "Valor": "115"})
        with s_col2:
            st.subheader("Registros Clínicos")
            if st.session_state.db_salud_clinica:
                st.table(pd.DataFrame(st.session_state.db_salud_clinica))
                if st.button("🗑️ Borrar Salud"):
                    st.session_state.db_salud_clinica = []
                    st.rerun()

    # --- MÓDULO CITAS ---
    with tab_citas:
        st.subheader("Agenda de Citas Médicas")
        ca1, ca2 = st.columns(2)
        with ca1:
            f_cita = st.date_input("Fecha")
            d_cita = st.text_input("Doctor/Especialidad")
            if st.button("Agendar Cita"):
                st.session_state.db_citas.append({"Fecha": str(f_cita), "Doctor": d_cita})
        with ca2:
            if st.session_state.db_citas:
                st.table(pd.DataFrame(st.session_state.db_citas))
                if st.button("🗑️ Vaciar Agenda"):
                    st.session_state.db_citas = []
                    st.rerun()

    # --- MÓDULO REPORTES & ENVÍO ---
    with tab_export:
        st.subheader("Generador de Salida")
        rep_txt = generar_texto_reporte()
        st.text_area("Previsualización:", rep_txt, height=200)
        
        c_wa, c_em = st.columns(2)
        with c_wa:
            wa_url = f"https://wa.me/?text={urllib.parse.quote(rep_txt)}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer;">📲 ENVIAR POR WHATSAPP</button></a>', unsafe_allow_html=True)
        with c_em:
            mail_url = f"mailto:?subject=Reporte Nexus&body={urllib.parse.quote(rep_txt)}"
            st.markdown(f'<a href="{mail_url}"><button style="width:100%; background-color:#EA4335; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer;">📧 ENVIAR POR CORREO</button></a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
