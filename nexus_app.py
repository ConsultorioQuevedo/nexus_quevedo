import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import pytz
import plotly.express as px
import urllib.parse
import os
from fpdf import FPDF

# =========================================================
# 1. MOTOR DE PDF PROFESIONAL (CLASE NEXUS COMPLETA)
# =========================================================
class NEXUS_PDF(FPDF):
    def header(self):
        # Encabezado con diseño oscuro
        self.set_fill_color(13, 17, 23)
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 24)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, 'NEXUS - SISTEMA DE CONTROL MAESTRO', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'REPORTE OFICIAL - LUIS RAFAEL QUEVEDO', 0, 1, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150)
        self.cell(0, 10, f'Documento generado por Nexus AI el {datetime.now().strftime("%d/%m/%Y")} | Página {self.page_no()}', 0, 0, 'C')

    def draw_health_circle(self, x, y, color_type):
        if color_type == "VERDE": self.set_fill_color(34, 139, 34)
        elif color_type == "AMARILLO": self.set_fill_color(218, 165, 32)
        elif color_type == "ROJO": self.set_fill_color(178, 34, 34)
        else: self.set_fill_color(100, 100, 100)
        self.ellipse(x, y, 4, 4, 'F')

# =========================================================
# 2. CONFIGURACIÓN DE INTERFAZ Y ESTILOS CSS PRO
# =========================================================
st.set_page_config(page_title="NEXUS QUEVEDO ULTIMATE v4.0", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    /* Fondo General */
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; }
    
    /* Botones Estilo Nexus */
    .stButton>button { 
        width: 100%; border-radius: 8px; font-weight: bold; height: 50px; 
        background: linear-gradient(180deg, #21262d 0%, #0d1117 100%);
        border: 1px solid #30363d; color: #58a6ff; transition: 0.3s;
    }
    .stButton>button:hover { border-color: #58a6ff; color: white; box-shadow: 0 0 10px #58a6ff44; }
    
    /* Botón Borrar (Rojo) */
    .btn-borrar > div > button { 
        background: #442326 !important; color: #ff7b72 !important; border: 1px solid #6e3636 !important; height: 35px !important; 
    }
    
    /* Botón WhatsApp (Verde) */
    .btn-whatsapp {
        background-color: #238636 !important; color: white !important; 
        text-decoration: none; padding: 12px; border-radius: 8px;
        display: block; text-align: center; font-weight: bold; margin-bottom: 15px;
    }
    
    /* Tarjetas */
    .nexus-card { background: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-bottom: 15px; }
    .status-badge { padding: 4px 10px; border-radius: 20px; font-size: 0.8em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 3. FUNCIONES DE TIEMPO Y BASE DE DATOS
# =========================================================
def obtener_fecha_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date()

def conectar_db():
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def analizardor_salud(valor, momento):
    if momento == "Ayunas":
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "#238636"
        if 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "#d29922"
        return "ROJO", "ALTO", "#da3633"
    else:
        if valor < 140: return "VERDE", "NORMAL", "#238636"
        if 140 <= valor <= 199: return "AMARILLO", "PRE-DIABETES", "#d29922"
        return "ROJO", "ALTO", "#da3633"

# =========================================================
# 4. SEGURIDAD DE ACCESO
# =========================================================
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 100px;'>🌐 SISTEMA NEXUS</h1>", unsafe_allow_html=True)
    _, col_log, _ = st.columns([1,1,1])
    with col_log:
        with st.form("login_nexus"):
            clave = st.text_input("Contraseña de Seguridad", type="password")
            if st.form_submit_button("INICIAR SESIÓN"):
                if clave == "admin123":
                    st.session_state.autenticado = True
                    st.rerun()
                else: st.error("Acceso denegado")
    st.stop()

# Inicializar Variables
db = conectar_db()
fecha_hoy, hora_hoy, mes_actual, fecha_obj = obtener_fecha_rd()

# =========================================================
# 5. BARRA LATERAL (MENÚ PRINCIPAL)
# =========================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>NEXUS PRO</h2>", unsafe_allow_html=True)
    st.markdown("---")
    st.write(f"📅 **Fecha:** {fecha_hoy}")
    st.write(f"🕒 **Hora:** {hora_hoy}")
    st.markdown("---")
    menu = st.radio("MÓDULOS ACTIVOS", ["🏠 PANEL DE INICIO", "💰 CONTROL FINANCIERO", "🩺 GESTIÓN DE SALUD", "📝 BITÁCORA Y NOTAS", "⚙️ CONFIGURACIÓN"])
    st.markdown("---")
    if st.button("CERRAR SESIÓN"):
        del st.session_state.autenticado
        st.rerun()

# =========================================================
# MÓDULO 1: PANEL DE INICIO
# =========================================================
if menu == "🏠 PANEL DE INICIO":
    st.title("Panel de Control General")
    st.write(f"Bienvenido de nuevo, Sr. Quevedo. Aquí está el resumen de sus datos.")

    c1, c2, c3 = st.columns(3)
    
    # KPI Salud
    ult_glu = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
    with c1:
        if ult_glu:
            _, texto, color_h = analizardor_salud(ult_glu[0], ult_glu[1])
            st.metric("Última Glucosa", f"{ult_glu[0]} mg/dL", delta=texto, delta_color="normal")
        else: st.metric("Glucosa", "Sin datos")

    # KPI Finanzas
    balance = db.execute("SELECT SUM(monto) FROM finanzas").fetchone()[0] or 0.0
    with c2:
        st.metric("Balance Total", f"RD$ {balance:,.2f}")

    # KPI Citas
    proxima = db.execute("SELECT doctor, fecha FROM citas WHERE fecha >= ? ORDER BY fecha LIMIT 1", (str(fecha_obj),)).fetchone()
    with c3:
        if proxima: st.metric("Próxima Cita", proxima[0], delta=proxima[1], delta_color="off")
        else: st.metric("Citas", "Sin citas")

    st.markdown("---")
    st.subheader("📈 Tendencia de Salud (Gráfica)")
    df_graf = pd.read_sql_query("SELECT fecha, valor FROM glucosa ORDER BY id DESC LIMIT 15", db)
    if not df_graf.empty:
        fig = px.line(df_graf.iloc[::-1], x='fecha', y='valor', markers=True, template="plotly_dark")
        fig.update_traces(line_color='#58a6ff')
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# MÓDULO 2: CONTROL FINANCIERO
# =========================================================
elif menu == "💰 CONTROL FINANCIERO":
    st.title("Gestión de Ingresos y Gastos")
    
    # Formulario de Registro
    with st.form("finanzas_form", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns([1,1,2])
        tipo_f = col_f1.selectbox("Tipo", ["GASTO", "INGRESO"])
        monto_f = col_f2.number_input("Monto en RD$", min_value=0.0, step=100.0)
        cat_f = col_f3.selectbox("Categoría", ["Salud", "Supermercado", "Servicios", "Transporte", "Hogar", "Otros"])
        det_f = st.text_input("Detalle del movimiento").upper()
        if st.form_submit_button("REGISTRAR EN BASE DE DATOS"):
            monto_final = -monto_f if tipo_f == "GASTO" else monto_f
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", 
                       (fecha_hoy, mes_actual, tipo_f, cat_f, det_f, monto_final))
            db.commit(); st.rerun()

    st.markdown("---")
    st.subheader("Historial de Movimientos")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    
    if not df_f.empty:
        # Aquí agregamos los BORRADORES individuales por ID
        for _, fila in df_f.iterrows():
            col_d1, col_d2 = st.columns([6, 1])
            color_monto = "#f87171" if fila['monto'] < 0 else "#4ade80"
            col_d1.markdown(f"""
                <div class='nexus-card'>
                <b>{fila['fecha']}</b> | {fila['tipo']} | {fila['categoria']} | {fila['detalle']} | 
                <span style='color:{color_monto}'>RD$ {abs(fila['monto']):,.2f}</span>
                </div>
            """, unsafe_allow_html=True)
            if col_d2.button("🗑️", key=f"fin_{fila['id']}"):
                db.execute("DELETE FROM finanzas WHERE id=?", (fila['id'],)); db.commit(); st.rerun()

# =========================================================
# MÓDULO 3: GESTIÓN DE SALUD (COMPLETO CON BORRADORES Y PDF)
# =========================================================
elif menu == "🩺 GESTIÓN DE SALUD":
    st.title("Control Médico y Glucosa")
    
    tab_glu, tab_med, tab_cit = st.tabs(["🩸 REGISTRO GLUCOSA", "💊 MEDICAMENTOS", "📅 AGENDA DE CITAS"])

    # --- SUB-TAB: GLUCOSA ---
    with tab_glu:
        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            with st.form("glu_form", clear_on_submit=True):
                val_g = st.number_input("Nivel (mg/dL)", 100)
                mom_g = st.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
                if st.form_submit_button("GUARDAR LECTURA"):
                    db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (fecha_hoy, hora_hoy, mom_g, val_g))
                    db.commit(); st.rerun()
        
        with col_g2:
            df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
            if not df_g.empty:
                # 1. BOTÓN WHATSAPP SALUD
                ult = df_g.iloc[0]
                msg_w = f"*REPORTE NEXUS SALUD*\nPaciente: Luis Rafael Quevedo\nValor: {ult['valor']} mg/dL\nMomento: {ult['momento']}\nFecha: {fecha_hoy}"
                st.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg_w)}" target="_blank" class="btn-whatsapp">📲 ENVIAR ÚLTIMO A WHATSAPP</a>', unsafe_allow_html=True)
                
                # 2. BOTÓN PDF SALUD
                pdf_s = NEXUS_PDF()
                pdf_s.add_page()
                pdf_s.set_font("Arial", 'B', 14)
                pdf_s.cell(0, 10, "HISTORIAL DE GLUCOSA", 0, 1, 'L')
                pdf_s.ln(5)
                for _, rs in df_g.head(20).iterrows():
                    slug_s, txt_s, _ = analizardor_salud(rs['valor'], rs['momento'])
                    pdf_s.set_font("Arial", '', 10)
                    pdf_s.cell(30, 10, rs['fecha'], 1)
                    pdf_s.cell(40, 10, rs['momento'], 1)
                    pdf_s.cell(20, 10, str(rs['valor']), 1)
                    pdf_s.cell(30, 10, txt_s, 1, 1)
                
                st.download_button("📥 DESCARGAR REPORTE PDF SALUD", pdf_s.output(dest='S').encode('latin-1'), "Salud_Quevedo.pdf")

                # 3. LISTA CON BORRADORES
                st.markdown("### Últimos Registros")
                for _, rg in df_g.head(10).iterrows():
                    _, t_g, c_g = analizardor_salud(rg['valor'], rg['momento'])
                    cg1, cg2 = st.columns([6, 1])
                    cg1.markdown(f"<div class='nexus-card' style='border-left: 5px solid {c_g}'><b>{rg['valor']} mg/dL</b> - {rg['momento']} ({rg['fecha']} {rg['hora']}) -> {t_g}</div>", unsafe_allow_html=True)
                    if cg2.button("🗑️", key=f"glu_{rg['id']}"):
                        db.execute("DELETE FROM glucosa WHERE id=?", (rg['id'],)); db.commit(); st.rerun()

    # --- SUB-TAB: MEDICAMENTOS ---
    with tab_med:
        with st.form("med_form"):
            cm1, cm2, cm3 = st.columns(3)
            m_n = cm1.text_input("Nombre de la Medicina")
            m_d = cm2.text_input("Dosis (Ej: 1 tableta)")
            m_h = cm3.text_input("Horario (Ej: 8:00 AM)")
            if st.form_submit_button("REGISTRAR MEDICAMENTO"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (m_n.upper(), m_d.upper(), m_h.upper()))
                db.commit(); st.rerun()
        
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, rm in df_m.iterrows():
            cm1, cm2 = st.columns([6, 1])
            cm1.info(f"💊 **{rm['nombre']}** | Dosis: {rm['dosis']} | Horario: {rm['horario']}")
            if cm2.button("🗑️", key=f"med_{rm['id']}"):
                db.execute("DELETE FROM medicamentos WHERE id=?", (rm['id'],)); db.commit(); st.rerun()

    # --- SUB-TAB: CITAS ---
    with tab_cit:
        with st.form("cita_form"):
            cc1, cc2 = st.columns(2)
            c_doc = cc1.text_input("Doctor / Especialidad")
            c_fec = cc2.date_input("Fecha de la Cita")
            c_mot = st.text_input("Motivo de la consulta")
            if st.form_submit_button("AGENDAR CITA MÉDICA"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (c_doc.upper(), str(c_fec), c_mot.upper()))
                db.commit(); st.rerun()
        
        df_c = pd.read_sql_query("SELECT * FROM citas ORDER BY fecha ASC", db)
        for _, rc in df_c.iterrows():
            cc1, cc2 = st.columns([6, 1])
            cc1.warning(f"📅 **{rc['fecha']}** | Doctor: {rc['doctor']} | Motivo: {rc['motivo']}")
            if cc2.button("🗑️", key=f"cit_{rc['id']}"):
                db.execute("DELETE FROM citas WHERE id=?", (rc['id'],)); db.commit(); st.rerun()

# =========================================================
# MÓDULO 4: BITÁCORA Y NOTAS (CON PDF Y WHATSAPP)
# =========================================================
elif menu == "📝 BITÁCORA Y NOTAS":
    st.title("Bitácora de Notas Personales")
    path_bitacora = "nexus_bitacora.txt"
    
    # Campo de texto para nueva nota
    nueva_nota = st.text_area("¿Qué desea anotar hoy, Quevedo?", height=150)
    col_n1, col_n2, col_n3 = st.columns(3)
    
    if col_n1.button("💾 GUARDAR NOTA"):
        if nueva_nota:
            with open(path_bitacora, "a", encoding="utf-8") as f:
                f.write(f"--- FECHA: {fecha_hoy} {hora_hoy} ---\n{nueva_nota}\n\n")
            st.success("Nota guardada"); st.rerun()

    if os.path.exists(path_bitacora):
        with open(path_bitacora, "r", encoding="utf-8") as f:
            contenido_completo = f.read()
        
        # 1. WHATSAPP BITÁCORA
        if contenido_completo:
            msg_bit = f"*BITÁCORA NEXUS*\n{contenido_completo[-500:]}" # Últimos 500 caracteres
            col_n2.markdown(f'<a href="https://wa.me/?text={urllib.parse.quote(msg_bit)}" target="_blank" class="btn-whatsapp">📲 ENVIAR A WHATSAPP</a>', unsafe_allow_html=True)
        
        # 2. PDF BITÁCORA
        pdf_b = NEXUS_PDF()
        pdf_b.add_page()
        pdf_b.set_font("Arial", '', 11)
        pdf_b.multi_cell(0, 10, contenido_completo.encode('latin-1', 'replace').decode('latin-1'))
        col_nb3 = col_n3.download_button("📥 DESCARGAR PDF NOTAS", pdf_b.output(dest='S').encode('latin-1'), "Bitacora_Quevedo.pdf")

        st.markdown("---")
        st.markdown("### Historial de Notas")
        st.text_area("Vista de Historial", contenido_completo, height=400)
        
        if st.button("🗑️ BORRAR TODA LA BITÁCORA", type="primary"):
            if os.path.exists(path_bitacora):
                os.remove(path_bitacora)
                st.rerun()

# =========================================================
# MÓDULO 5: CONFIGURACIÓN
# =========================================================
elif menu == "⚙️ CONFIGURACIÓN":
    st.title("Ajustes del Sistema")
    st.write("Configuración técnica de Nexus Core.")
    
    if st.button("BORRAR TODA LA BASE DE DATOS (PELIGRO)"):
        db.execute("DELETE FROM glucosa")
        db.execute("DELETE FROM finanzas")
        db.execute("DELETE FROM medicamentos")
        db.execute("DELETE FROM citas")
        db.commit()
        st.warning("Todos los datos han sido borrados.")

# Cierre de conexión
db.close()
