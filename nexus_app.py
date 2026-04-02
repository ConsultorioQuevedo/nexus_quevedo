import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from fpdf import FPDF

# ==========================================
# 1. EL "CHASIS" (CONEXIÓN SEGURA)
# ==========================================
def conectar_db():
    conn = sqlite3.connect('nexus_pro_vault.db', check_same_thread=False)
    cursor = conn.cursor()
    # Creamos las tablas de inmediato para que el sistema nunca las encuentre "vacías"
    tablas = [
        'glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)',
        'meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)',
        'citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT, motivo TEXT)',
        'finanzas (id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, concepto TEXT, monto REAL)',
        'escaneos (id INTEGER PRIMARY KEY, fecha TEXT, imagen BLOB, nota TEXT)'
    ]
    for t in tablas:
        cursor.execute(f'CREATE TABLE IF NOT EXISTS {t}')
    conn.commit()
    return conn, cursor

conn, cursor = conectar_db()

# ==========================================
# 2. MOTOR DE INTELIGENCIA (IA SILENCIOSA)
# ==========================================
def motor_ia_proactivo():
    alertas = []
    try:
        # Solo analiza si hay datos, si no, se queda en silencio (sin errores)
        df_g = pd.read_sql_query("SELECT valor FROM glucosa ORDER BY id DESC LIMIT 5", conn)
        if not df_g.empty:
            avg = df_g['valor'].mean()
            if avg > 160: alertas.append("🚨 IA: Tendencia de glucosa ALTA detectada.")
    except: pass 
    return alertas

# ==========================================
# 3. INTERFAZ (SIN CAMBIOS DE DISEÑO)
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO", layout="wide")
    st.title("🧬 NEXUS SMART: Control Institucional")
    st.caption(f"Usuario: {st.session_state.get('user', 'Luis Rafael Quevedo')} | Modo: Estabilidad Total")

    tabs = st.tabs(["🏠 DASHBOARD", "🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS", "💰 FINANZAS", "📸 ESCÁNER", "📤 EXPORTAR"])

    # --- DASHBOARD ---
    with tabs[0]:
        st.subheader("🤖 Análisis de IA")
        for a in motor_ia_proactivo(): st.warning(a)
        st.write("---")
        st.info("Sistema listo. Sus datos están protegidos en el disco local.")

    # --- GLUCOSA (Precisión de número corregida internamente) ---
    with tabs[1]:
        c1, c2 = st.columns([1, 2])
        with c1:
            # Forzamos el tipo de dato a FLOAT para evitar multiplicaciones erróneas
            val_g = st.number_input("Valor Glucosa:", min_value=0.0, step=1.0, format="%.0f")
            if st.button("Guardar Glucosa"):
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                est = "Normal" if val_g <= 125 else "Alerta"
                cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, float(val_g), est))
                conn.commit()
                st.rerun()
        with c2:
            df_g = pd.read_sql_query("SELECT fecha, valor, estado FROM glucosa ORDER BY id DESC", conn)
            st.table(df_g)

    # --- FINANZAS (Diferenciación Ingreso/Gasto) ---
    with tabs[4]:
        f1, f2 = st.columns([1, 2])
        with f1:
            tipo = st.radio("Operación:", ["Gasto", "Ingreso"])
            monto = st.number_input("Monto RD$:", min_value=0.0, format="%.2f")
            if st.button("Registrar"):
                fec = datetime.datetime.now().strftime("%d/%m/%Y")
                cursor.execute('INSERT INTO finanzas (fecha, tipo, monto) VALUES (?,?,?)', (fec, tipo, float(monto)))
                conn.commit()
                st.rerun()
        with f2:
            st.write(pd.read_sql_query("SELECT * FROM finanzas", conn))

if __name__ == "__main__":
    main()
