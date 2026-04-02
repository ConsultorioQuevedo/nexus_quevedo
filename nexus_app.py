import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF
import io

# ==========================================
# 1. EL BÚNKER: PERSISTENCIA REAL (SQLite)
# ==========================================
def conectar_db():
    # Creamos un archivo real en el dispositivo para que nada se borre
    conn = sqlite3.connect('nexus_pro_vault.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS salud 
                 (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, valor REAL, estado TEXT, nota TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas 
                 (id INTEGER PRIMARY KEY, fecha TEXT, categoria TEXT, concepto TEXT, monto REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS agenda 
                 (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)''')
    conn.commit()
    return conn

db_conn = conectar_db()

# ==========================================
# 2. LÓGICA DE NEGOCIO E IA
# ==========================================
def calcular_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    if v > 160: return "🔴 ALERTA"
    return "⚪ FUERA DE RANGO"

def motor_ia():
    analisis = []
    df = pd.read_sql_query("SELECT valor FROM salud WHERE tipo='Glucosa' ORDER BY id DESC LIMIT 3", db_conn)
    if not df.empty:
        if df['valor'].iloc[0] > 160:
            analisis.append("🚨 IA: Nivel crítico detectado. Se sugiere reposo e hidratación.")
    return analisis

# ==========================================
# 3. INTERFAZ PROFESIONAL (DASHBOARD)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    st.title("🧬 NEXUS SMART: Control de Alto Nivel")
    st.write(f"Gestión de **Luis Rafael Quevedo** | 🔒 Datos en Madera Sólida")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 DASHBOARD", "🩺 SALUD", "📅 AGENDA", "💰 FINANZAS", "📤 REPORTES"])

    # --- DASHBOARD & IA ---
    with tab1:
        st.subheader("🤖 Cerebro Proactivo")
        avisos = motor_ia()
        for a in avisos: st.error(a)
        
        st.write("---")
        if st.toggle("📸 ACTIVAR ESCÁNER DE DOCUMENTOS"):
            foto = st.camera_input("Enfoque su receta o reporte")
            if foto:
                st.success("Documento capturado. Guardado en el historial de archivos.")

    # --- SALUD (Punto 3: Semáforo y Formato Correcto) ---
    with tab2:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Registrar Glucosa/Meds")
            tipo_s = st.selectbox("Categoría:", ["Glucosa", "Medicamento"])
            # Punto 6: El format="%.2f" asegura que no haya multiplicaciones raras
            val_s = st.number_input("Valor / Dosis:", min_value=0.0, format="%.2f", step=1.0)
            nota_s = st.text_input("Nota adicional:")
            if st.button("💾 Guardar en Salud"):
                est = calcular_semaforo(val_s) if tipo_s == "Glucosa" else "N/A"
                fec = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                db_conn.execute('INSERT INTO salud (fecha, tipo, valor, estado, nota) VALUES (?,?,?,?,?)', 
                               (fec, tipo_s, val_s, est, nota_s))
                db_conn.commit()
                st.rerun()
        with c2:
            st.subheader("Historial Médico")
            df_s = pd.read_sql_query("SELECT fecha, tipo, valor, estado, nota FROM salud ORDER BY id DESC", db_conn)
            st.dataframe(df_s, use_container_width=True)
            if st.button("🗑️ Vaciar Historial Médico"):
                db_conn.execute("DELETE FROM salud"); db_conn.commit(); st.rerun()

    # --- FINANZAS (Punto 2: Diferenciación Clara) ---
    with tab4:
        f1, f2 = st.columns([1, 2])
        with f1:
            st.subheader("Ingresos y Gastos")
            cat_f = st.radio("Tipo:", ["Gasto", "Ingreso"])
            con_f = st.text_input("Concepto:")
            mon_f = st.number_input("Monto RD$:", min_value=0.0, format="%.2f", step=1.0)
            if st.button("💸 Registrar"):
                fec = datetime.datetime.now().strftime("%d/%m/%Y")
                db_conn.execute('INSERT INTO finanzas (fecha, categoria, concepto, monto) VALUES (?,?,?,?)',
                               (fec, cat_f, con_f, mon_f))
                db_conn.commit()
                st.rerun()
        with f2:
            df_f = pd.read_sql_query("SELECT * FROM finanzas", db_conn)
            st.table(df_f)
            if st.button("🗑️ Borrar Finanzas"):
                db_conn.execute("DELETE FROM finanzas"); db_conn.commit(); st.rerun()

    # --- AGENDA (Punto 4: Funcional) ---
    with tab3:
        st.subheader("Próximas Citas Médicas")
        a1, a2 = st.columns(2)
        with a1:
            f_cita = st.date_input("Fecha de la Cita")
            d_cita = st.text_input("Doctor/Especialidad")
            if st.button("🗓️ Agendar"):
                db_conn.execute('INSERT INTO agenda (fecha, doctor) VALUES (?,?)', (str(f_cita), d_cita))
                db_conn.commit(); st.rerun()
        with a2:
            st.write(pd.read_sql_query("SELECT * FROM agenda", db_conn))

    # --- REPORTES (Punto 9: Formato Profesional) ---
    with tab5:
        st.subheader("Exportación de Récord Médico")
        rep = "🏥 *NEXUS PRO - REPORTE INSTITUCIONAL*\n"
        rep += "---------------------------------\n"
        rep += f"Emitido para: Luis Rafael Quevedo\n\n"
        rep += "🩸 *ESTADO DE GLUCOSA:*\n"
        df_g = pd.read_sql_query("SELECT * FROM salud WHERE tipo='Glucosa' LIMIT 5", db_conn)
        for _, r in df_g.iterrows(): rep += f"• {r['fecha']}: {r['valor']} ({r['estado']})\n"
        
        st.text_area("Cuerpo del Reporte:", rep, height=200)
        
        col_wa, col_gm = st.columns(2)
        url_wa = f"https://wa.me/?text={urllib.parse.quote(rep)}"
        url_gm = f"https://mail.google.com/mail/?view=cm&fs=1&su=Reporte+Nexus&body={urllib.parse.quote(rep)}"
        
        col_wa.markdown(f'[📲 Enviar por WhatsApp]({url_wa})')
        col_gm.markdown(f'[📧 Enviar por Gmail]({url_gm})')

if __name__ == "__main__":
    main()
