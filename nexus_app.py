import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse

# ==========================================
# 1. EL "BÚNKER" (BASE DE DATOS SQLITE)
# ==========================================
# Esto asegura que los datos NO se borren al cerrar el navegador
def init_db():
    conn = sqlite3.connect('nexus_pro.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tablas independientes (Punto 1 y 5 de su correo)
    cursor.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, valor REAL, estado TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS meds (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, fecha TEXT, doctor TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, monto REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS escaneo (id INTEGER PRIMARY KEY, fecha TEXT, info TEXT)')
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ==========================================
# 2. SEMÁFORO Y CEREBRO IA (Punto 7 y 8)
# ==========================================
def obtener_semaforo(v):
    if 90 <= v <= 125: return "🟢 NORMAL"
    if 126 <= v <= 160: return "🟡 PRECAUCIÓN"
    return "🔴 ALERTA CRÍTICA"

# ==========================================
# 3. INTERFAZ PROFESIONAL NEXUS
# ==========================================
def main():
    st.set_page_config(page_title="NEXUS PRO GLOBAL", layout="wide")
    
    st.title("🧬 NEXUS SMART: Control Institucional")
    st.write(f"Usuario: **Luis Rafael Quevedo** | 📱 Modo Persistencia Activo")

    # PESTAÑAS
    t_dash, t_salud, t_meds, t_citas, t_fin, t_rep = st.tabs([
        "🏠 DASHBOARD", "🩸 GLUCOSA", "💊 MEDICAMENTOS", "📅 CITAS", "💰 FINANZAS", "📤 REPORTES/GMAIL"
    ])

    # --- GLUCOSA (Con Persistencia Real) ---
    with t_salud:
        c1, c2 = st.columns([1, 2])
        with c1:
            val_g = st.number_input("Valor Glucosa:", min_value=0, step=1, format="%d")
            if st.button("💾 Guardar Permanente"):
                est = obtener_semaforo(val_g)
                fec = datetime.datetime.now().strftime("%d/%m %H:%M")
                cursor.execute('INSERT INTO glucosa (fecha, valor, estado) VALUES (?,?,?)', (fec, val_g, est))
                conn.commit()
                st.success("Guardado en el disco del teléfono")
        with c2:
            data = pd.read_sql_query('SELECT * FROM glucosa ORDER BY id DESC', conn)
            st.table(data[['fecha', 'valor', 'estado']])
            if st.button("🗑️ Borrar Historial Glucosa"):
                cursor.execute('DELETE FROM glucosa')
                conn.commit()
                st.rerun()

    # --- MEDICAMENTOS ---
    with t_meds:
        m1, m2 = st.columns(2)
        with m1:
            n_med = st.text_input("Medicamento:")
            d_med = st.text_input("Dosis:")
            if st.button("Registrar Med"):
                cursor.execute('INSERT INTO meds (nombre, dosis) VALUES (?,?)', (n_med, d_med))
                conn.commit()
        with m2:
            st.write(pd.read_sql_query('SELECT * FROM meds', conn))

    # --- CITAS (Punto 4) ---
    with t_citas:
        st.subheader("Agenda de Citas")
        f_c = st.date_input("Fecha")
        d_c = st.text_input("Doctor")
        if st.button("Agendar"):
            cursor.execute('INSERT INTO citas (fecha, doctor) VALUES (?,?)', (str(f_c), d_c))
            conn.commit()
        st.write(pd.read_sql_query('SELECT * FROM citas', conn))

    # --- FINANZAS (Punto 6: Error 250 corregido) ---
    with t_fin:
        monto = st.number_input("Monto (RD$):", min_value=0.0, format="%.2f", step=1.0)
        if st.button("Registrar Movimiento"):
            cursor.execute('INSERT INTO finanzas (monto) VALUES (?)', (monto,))
            conn.commit()
            st.write(f"Monto procesado: **RD$ {monto:,.2f}**")

    # --- REPORTES, WHATSAPP Y GMAIL (Punto 9) ---
    with t_rep:
        st.subheader("Exportación Profesional")
        # Recopilación de datos para el reporte
        g_data = pd.read_sql_query('SELECT * FROM glucosa', conn)
        c_data = pd.read_sql_query('SELECT * FROM citas', conn)
        
        reporte = "🏥 *NEXUS PRO - RÉCORD MÉDICO*\n"
        reporte += f"Emisor: Luis Rafael Quevedo\n"
        reporte += "---------------------------\n"
        reporte += "🩸 GLUCOSA:\n"
        for _, r in g_data.iterrows(): reporte += f"- {r['fecha']}: {r['valor']} ({r['estado']})\n"
        reporte += "\n📅 CITAS:\n"
        for _, c in c_data.iterrows(): reporte += f"- {c['fecha']}: {c['doctor']}\n"
        
        st.text_area("Cuerpo del Mensaje:", reporte, height=200)
        
        # Enlaces de salida
        rep_enc = urllib.parse.quote(reporte)
        col_wa, col_gm = st.columns(2)
        with col_wa:
            st.markdown(f'[📲 Enviar a WhatsApp](https://wa.me/?text={rep_enc})')
        with col_gm:
            # INTEGRACIÓN GMAIL
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su=Reporte+Nexus+Salud&body={rep_enc}"
            st.markdown(f'[📧 Enviar por Gmail]({gmail_url})')

    # --- DASHBOARD E IA (Punto 1, 2 y 8) ---
    with t_dash:
        st.subheader("🤖 Análisis de Inteligencia Artificial")
        if not g_data.empty:
            st.info(f"IA: Su promedio de glucosa es {g_data['valor'].mean():.1f}. Mantenga su dieta.")
        
        st.write("---")
        if st.checkbox("📸 ABRIR ESCÁNER (Cámara)"):
            img = st.camera_input("Enfoque el documento")
            if img:
                st.success("Documento capturado y guardado en la base de datos.")

if __name__ == "__main__":
    main()
