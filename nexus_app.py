import streamlit as st
import pandas as pd
import datetime

# ==========================================
# 1. MOTOR DE PERSISTENCIA Y LÓGICA
# ==========================================
class MotorNEXUS:
    def __init__(self):
        # Bases de datos separadas (Independencia Total)
        if 'db_finanzas' not in st.session_state: st.session_state.db_finanzas = []
        if 'db_glucosa' not in st.session_state: st.session_state.db_glucosa = []
        if 'db_citas' not in st.session_state: st.session_state.db_citas = []
        if 'db_escaner' not in st.session_state: st.session_state.db_escaner = []

    def obtener_color_glucosa(self, valor):
        """Lógica de Semáforo solicitada por Sr. Quevedo"""
        if valor < 125: return "#28a745" # Verde
        elif 125 <= valor <= 160: return "#ffc107" # Amarillo
        else: return "#dc3545" # Rojo

# ==========================================
# 2. INTERFAZ DASHBOARD PRINCIPAL
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS SMART PRO", layout="wide")
    nexus = MotorNEXUS()

    st.title("🧬 NEXUS SMART: Gestión Institucional")
    st.write(f"Bienvenido, **Sr. Quevedo** | {datetime.datetime.now().strftime('%d/%m/%Y')}")

    # PESTAÑAS DE NAVEGACIÓN
    t_dash, t_clinica, t_citas, t_finanzas, t_escaner = st.tabs([
        "🏠 DASHBOARD", "🩺 CLÍNICA", "📅 CITAS", "💰 FINANZAS", "📸 ESCÁNER"
    ])

    # --- PESTAÑA: DASHBOARD ---
    with t_dash:
        st.subheader("Resumen de Estado")
        c1, c2 = st.columns(2)
        
        # Resumen Financiero
        total_ing = sum(f['Monto'] for f in st.session_state.db_finanzas if f['Tipo'] == 'Ingreso')
        total_gas = sum(f['Monto'] for f in st.session_state.db_finanzas if f['Tipo'] == 'Gasto')
        c1.metric("Balance Neto", f"RD$ {total_ing - total_gas:,.2f}")
        
        # Último Registro Glucosa con Semáforo
        if st.session_state.db_glucosa:
            ultimo = st.session_state.db_glucosa[-1]
            color = nexus.obtener_color_glucosa(ultimo['Valor'])
            c2.markdown(f"**Última Glucosa:** <span style='color:{color}; font-size:24px; font-weight:bold;'>{ultimo['Valor']} mg/dL</span>", unsafe_allow_html=True)
        else:
            c2.write("No hay registros de salud hoy.")

    # --- PESTAÑA: CLÍNICA (CON SEMÁFORO) ---
    with t_clinica:
        st.subheader("Control de Glucosa y Medicamentos")
        col_input, col_view = st.columns([1, 2])
        
        with col_input:
            val_g = st.number_input("Valor de Glucosa (mg/dL):", min_value=0)
            if st.button("Registrar Glucosa"):
                st.session_state.db_glucosa.append({"Fecha": datetime.datetime.now().strftime("%d/%m %H:%M"), "Valor": val_g})
        
        with col_view:
            if st.session_state.db_glucosa:
                for i, r in enumerate(reversed(st.session_state.db_glucosa)):
                    color = nexus.obtener_color_glucosa(r['Valor'])
                    st.markdown(f"● **{r['Fecha']}**: {r['Valor']} mg/dL <span style='color:{color};'>● Indicador</span>", unsafe_allow_html=True)

    # --- PESTAÑA: FINANZAS (YA NO ESTÁ VACÍA) ---
    with t_finanzas:
        st.subheader("Registro de Ingresos y Gastos")
        f_col1, f_col2 = st.columns([1, 2])
        
        with f_col1:
            tipo = st.radio("Tipo:", ["Ingreso", "Gasto"])
            monto = st.number_input("Monto RD$:", min_value=0.0)
            concepto = st.text_input("Concepto:")
            if st.button("Añadir Registro"):
                st.session_state.db_finanzas.append({"Fecha": datetime.datetime.now().strftime("%d/%m"), "Tipo": tipo, "Monto": monto, "Concepto": concepto})
        
        with f_col2:
            if st.session_state.db_finanzas:
                df_fin = pd.DataFrame(st.session_state.db_finanzas)
                st.table(df_fin)
                if st.button("Limpiar Finanzas"):
                    st.session_state.db_finanzas = []
                    st.rerun()

    # --- PESTAÑA: ESCÁNER (USO MANUAL) ---
    with t_escaner:
        st.subheader("Captura de Documentos")
        if st.button("📷 ABRIR CÁMARA"):
            img = st.camera_input("Enfoque el documento o receta")
            if img:
                st.session_state.db_escaner.append({"Fecha": datetime.datetime.now().strftime("%d/%m %H:%M"), "Imagen": img})
                st.success("Documento guardado en el archivo digital.")
        
        st.write("---")
        st.subheader("Archivo de Documentos Escaneados")
        if st.session_state.db_escaner:
            for doc in st.session_state.db_escaner:
                st.write(f"Documento del {doc['Fecha']}")
                st.image(doc['Imagen'], width=300)

if __name__ == "__main__":
    main()
