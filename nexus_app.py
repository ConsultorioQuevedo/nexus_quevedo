import streamlit as st
import pandas as pd
import datetime
import urllib.parse

# ==========================================
# 1. MOTOR DE LÓGICA Y REPORTES
# ==========================================
class MotorNEXUS:
    def __init__(self):
        # Bases de datos separadas por categoría
        if 'db_clinica' not in st.session_state: st.session_state.db_clinica = [] # Glucosa y Meds
        if 'db_citas' not in st.session_state: st.session_state.db_citas = []     # Agenda de Citas
        if 'gastos' not in st.session_state: st.session_state.gastos = []

    def generar_reporte_texto(self):
        ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        reporte = f"📋 *REPORTE MÉDICO NEXUS PRO*\nFecha: {ahora}\n\n"
        
        reporte += "🩸 *REGISTROS DE SALUD:*\n"
        if st.session_state.db_clinica:
            for r in st.session_state.db_clinica:
                reporte += f"- {r['Fecha']}: {r['Detalle']} ({r['Valor']})\n"
        else: reporte += "- Sin registros recientes.\n"
        
        reporte += "\n📅 *PRÓXIMAS CITAS:*\n"
        if st.session_state.db_citas:
            for c in st.session_state.db_citas:
                reporte += f"- {c['Fecha']}: {c['Doctor']} - {c['Motivo']}\n"
        else: reporte += "- No hay citas programadas.\n"
        
        return reporte

# ==========================================
# 2. INTERFAZ PROFESIONAL
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS SMART V2", layout="wide")
    nexus = MotorNEXUS()

    st.title("🧬 NEXUS SMART: Gestión de Salud y Citas")
    st.write("---")

    # SEPARACIÓN DE SECCIONES EN PESTAÑAS
    tab_clinica, tab_citas, tab_reportes = st.tabs(["🩺 CLÍNICA (Glucosa/Meds)", "📅 AGENDA DE CITAS", "📤 ENVIAR REPORTES"])

    # --- PESTAÑA 1: CLÍNICA ---
    with tab_clinica:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Nuevo Registro")
            tipo = st.selectbox("Tipo de registro", ["Glucosa (mg/dL)", "Medicamento"])
            valor = st.text_input("Valor o Nombre del Med:")
            if st.button("Guardar en Clínica"):
                fecha = datetime.datetime.now().strftime("%d/%m %H:%M")
                st.session_state.db_clinica.append({"Fecha": fecha, "Detalle": tipo, "Valor": valor})
                st.success("Registrado.")
        with col2:
            st.subheader("Historial Clínico")
            if st.session_state.db_clinica:
                st.table(pd.DataFrame(st.session_state.db_clinica))
                if st.button("🗑️ Limpiar Clínica"):
                    st.session_state.db_clinica = []
                    st.rerun()

    # --- PESTAÑA 2: CITAS MÉDICAS ---
    with tab_citas:
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            st.subheader("Programar Cita")
            fecha_cita = st.date_input("Fecha de la cita")
            hora_cita = st.time_input("Hora")
            doctor = st.text_input("Especialista / Centro")
            motivo = st.text_area("Motivo de consulta")
            if st.button("Añadir a la Agenda"):
                st.session_state.db_citas.append({
                    "Fecha": f"{fecha_cita} {hora_cita}",
                    "Doctor": doctor,
                    "Motivo": motivo
                })
                st.balloons()
        with col_c2:
            st.subheader("Citas Programadas")
            if st.session_state.db_citas:
                st.table(pd.DataFrame(st.session_state.db_citas))
                if st.button("🗑️ Limpiar Agenda"):
                    st.session_state.db_citas = []
                    st.rerun()

    # --- PESTAÑA 3: REPORTES Y ENVÍO ---
    with tab_reportes:
        st.subheader("Generar y Exportar Datos")
        texto_reporte = nexus.generar_reporte_texto()
        st.text_area("Vista previa del reporte:", texto_reporte, height=250)

        c1, c2 = st.columns(2)
        with c1:
            # WHATSAPP
            wa_encoded = urllib.parse.quote(texto_reporte)
            st.markdown(f'''
                <a href="https://wa.me/?text={wa_encoded}" target="_blank">
                    <button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; font-weight:bold;">
                        📲 ENVIAR POR WHATSAPP
                    </button>
                </a>
            ''', unsafe_allow_html=True)

        with c2:
            # EMAIL
            asunto = "Reporte Nexus Pro Salud"
            mail_url = f"mailto:?subject={asunto}&body={wa_encoded}"
            st.markdown(f'''
                <a href="{mail_url}">
                    <button style="width:100%; background-color:#EA4335; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; font-weight:bold;">
                        📧 ENVIAR POR CORREO
                    </button>
                </a>
            ''', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
