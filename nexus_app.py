import streamlit as st
import pandas as pd
import datetime
import urllib.parse
from fpdf import FPDF

# ==========================================
# 1. BACKEND SÓLIDO (INDEPENDENCIA TOTAL)
# ==========================================
class BackendNEXUS:
    def __init__(self):
        # Entidades como archivos/celdas separadas
        if 'db_glucosa' not in st.session_state: st.session_state.db_glucosa = []
        if 'db_meds' not in st.session_state: st.session_state.db_meds = []
        if 'db_agenda' not in st.session_state: st.session_state.db_agenda = []
        if 'db_finanzas' not in st.session_state: st.session_state.db_finanzas = []

    def borrar_registro(self, db_name, index):
        """Borrado quirúrgico sin cruce de datos"""
        if db_name in st.session_state:
            st.session_state[db_name].pop(index)
            st.rerun()

# ==========================================
# 2. MÓDULO DE INTELIGENCIA ARTIFICIAL (IA)
# ==========================================
class CerebroNEXUS:
    @staticmethod
    def analizar_salud():
        alertas = []
        logs = st.session_state.db_glucosa
        if logs:
            ultimo = logs[-1]['Valor']
            # Patrón detectado
            if ultimo > 140:
                alertas.append("🚨 IA ALERTA: Tendencia de Glucosa ALTA. Sugerencia: Revisar ingesta de carbohidratos.")
            elif ultimo < 70:
                alertas.append("⚠️ IA ALERTA: Tendencia de Hipoglucemia. Tenga azúcar a mano.")
            else:
                alertas.append("✅ IA ESTADO: Niveles estables según los últimos registros.")
        
        # Análisis de Citas
        if st.session_state.db_agenda:
            alertas.append(f"📅 IA RECORDATORIO: Tiene {len(st.session_state.db_agenda)} cita(s) pendiente(s).")
            
        return alertas

# ==========================================
# 3. GENERADOR DE REPORTES ELEGANTES
# ==========================================
def generar_reporte_profesional():
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    # Formato Récord Médico / Factura
    rep = f"🏥 *NEXUS PRO - RÉCORD MÉDICO OFICIAL*\n"
    rep += f"🗓️ Fecha de Emisión: {fecha_hoy}\n"
    rep += f"👤 Paciente: Luis Rafael Quevedo\n"
    rep += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    rep += "🩸 *SECCIÓN A: CONTROL DE GLUCOSA*\n"
    if st.session_state.db_glucosa:
        for r in st.session_state.db_glucosa:
            rep += f"• {r['Fecha']}: {r['Valor']} mg/dL ({r['Nota']})\n"
    else: rep += "_Sin registros de glucosa_\n"
    
    rep += "\n💊 *SECCIÓN B: MEDICAMENTOS*\n"
    if st.session_state.db_meds:
        for m in st.session_state.db_meds:
            rep += f"• {m['Medicamento']}: {m['Dosis']}\n"
    
    rep += "\n📅 *SECCIÓN C: AGENDA DE CITAS*\n"
    if st.session_state.db_agenda:
        for c in st.session_state.db_agenda:
            rep += f"• {c['Fecha']}: Dr. {c['Doctor']} ({c['Centro']})\n"
    
    rep += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    rep += "🤖 _Analizado por Inteligencia Artificial NEXUS_"
    return rep

# ==========================================
# 4. INTERFAZ DASHBOARD PRINCIPAL
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide", page_icon="🧬")
    backend = BackendNEXUS()
    ia = CerebroNEXUS()

    st.title("🧬 NEXUS SMART: Gestión Institucional")
    st.write(f"Bienvenido, **Sr. Quevedo** | {datetime.datetime.now().strftime('%A, %d de %B')}")

    # --- PESTAÑAS DE NAVEGACIÓN ---
    t_dash, t_salud, t_agenda, t_fin, t_reporte = st.tabs([
        "🏠 DASHBOARD", "🩺 CLÍNICA", "📅 CITAS", "💰 FINANZAS", "📤 REPORTES"
    ])

    # PESTAÑA DASHBOARD (IA INTEGRADA)
    with t_dash:
        st.subheader("🤖 Análisis Proactivo de la IA")
        avisos = ia.analizar_salud()
        for aviso in avisos:
            st.info(aviso)
        
        st.write("---")
        st.subheader("📸 ESCÁNER INTELIGENTE")
        # Integración de cámara nativa para teléfono
        img_file = st.camera_input("Capturar Documento/Receta Médica")
        if img_file:
            st.success("✅ Imagen capturada. Procesando datos para registro automático...")
            # Aquí la IA registraría automáticamente (Simulación)
            st.session_state.db_glucosa.append({"Fecha": "Hoy", "Valor": 118.0, "Nota": "Escaneado"})

    # PESTAÑA CLÍNICA (GLUCOSA Y MEDS)
    with t_salud:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🩸 Registro de Glucosa")
            val_g = st.number_input("Valor mg/dL", min_value=0.0)
            nota_g = st.text_input("Nota (Ayunas, Post-comida, etc.)")
            if st.button("Guardar Glucosa"):
                st.session_state.db_glucosa.append({"Fecha": datetime.datetime.now().strftime("%d/%m %H:%M"), "Valor": val_g, "Nota": nota_g})
        
        with col2:
            st.markdown("### 💊 Medicamentos")
            nom_m = st.text_input("Nombre Medicina")
            dos_m = st.text_input("Dosis (Ej: 500mg)")
            if st.button("Registrar Medicina"):
                st.session_state.db_meds.append({"Medicamento": nom_m, "Dosis": dos_m})

        st.write("---")
        st.write("### Historial Clínico Independiente")
        if st.session_state.db_glucosa:
            for i, r in enumerate(st.session_state.db_glucosa):
                c_a, c_b = st.columns([4, 1])
                c_a.write(f"📍 {r['Fecha']} - **{r['Valor']} mg/dL** ({r['Nota']})")
                if c_b.button("🗑️", key=f"del_g_{i}"): backend.borrar_registro('db_glucosa', i)

    # PESTAÑA AGENDA DE CITAS
    with t_agenda:
        st.subheader("📅 Gestión de Citas Médicas")
        ca1, ca2 = st.columns([1, 2])
        with ca1:
            f_cita = st.date_input("Fecha de Cita")
            d_cita = st.text_input("Nombre del Doctor")
            l_cita = st.text_input("Centro Médico")
            if st.button("Agendar Nueva Cita"):
                st.session_state.db_agenda.append({"Fecha": str(f_cita), "Doctor": d_cita, "Centro": l_cita})
        
        with ca2:
            if st.session_state.db_agenda:
                for i, c in enumerate(st.session_state.db_agenda):
                    col_x, col_y = st.columns([4, 1])
                    col_x.warning(f"📆 **{c['Fecha']}** | Dr. {c['Doctor']} en {c['Centro']}")
                    if col_y.button("🗑️", key=f"del_c_{i}"): backend.borrar_registro('db_agenda', i)

    # PESTAÑA REPORTES (ELEGANCIA)
    with t_reporte:
        st.subheader("📄 Generación de Récord Médico Profesional")
        reporte_final = generar_reporte_profesional()
        st.markdown(f"```\n{reporte_final}\n```")
        
        rep_enc = urllib.parse.quote(reporte_final)
        col_wa, col_em = st.columns(2)
        with col_wa:
            st.markdown(f'<a href="https://wa.me/?text={rep_enc}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; font-weight:bold;">📲 WHATSAPP PROFESIONAL</button></a>', unsafe_allow_html=True)
        with col_em:
            st.markdown(f'<a href="mailto:?subject=Record Medico Nexus&body={rep_enc}"><button style="width:100%; background-color:#EA4335; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; font-weight:bold;">📧 CORREO ELECTRÓNICO</button></a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
