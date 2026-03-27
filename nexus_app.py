import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import pytz
import plotly.express as px
import io
import urllib.parse
import os
from fpdf import FPDF

# --- CLASE ESPECIAL PARA EL PDF (REPORTES PROFESIONALES) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'NEXUS - CONTROL PERSONAL QUEVEDO', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, f'Reporte Generado el: {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Propiedad Privada - Sistema Nexus Pro v3', 0, 0, 'C')

    def dibujar_semaforo(self, x, y, color_tipo):
        if color_tipo == "VERDE": self.set_fill_color(27, 94, 32) 
        elif color_tipo == "AMARILLO": self.set_fill_color(251, 192, 45) 
        elif color_tipo == "ROJO": self.set_fill_color(183, 28, 28) 
        else: self.set_fill_color(200, 200, 200) 
        self.ellipse(x, y, 4, 4, 'F')

# --- 1. CONFIGURACIÓN VISUAL Y ESTILOS ---
st.set_page_config(page_title="NEXUS QUEVEDO", layout="wide", page_icon="🌐")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #161b22; min-width: 300px; }
    .stForm { background-color: #161b22; border-radius: 15px; border: 1px solid #30363d; padding: 20px; }
    h1, h2, h3 { font-weight: 800; color: white; }
    .balance-box { background-color: #1f2937; padding: 25px; border-radius: 15px; text-align: center; border: 1px solid #30363d; margin: 20px 0; }
    .alerta-card { padding: 20px; border-radius: 12px; background-color: #1c2128; border: 1px solid #30363d; border-left: 6px solid #30363d; margin-bottom: 10px; }
    .insight-card { padding: 15px; border-radius: 10px; background: linear-gradient(90deg, #1e3a8a33, #1e3a8a11); border: 1px solid #3b82f644; margin-bottom: 20px; }
    
    div.stButton > button { 
        background-color: #1f2937; color: white; border: 1px solid #30363d; 
        border-radius: 8px; width: 100%; font-weight: bold; height: 50px; transition: 0.3s;
    }
    div.stButton > button:hover { border-color: #3b82f6; background-color: #232d3b; }
    
    .btn-borrar-rojo > div > button { background-color: #441111 !important; color: #ff9999 !important; border: 1px solid #662222 !important; height: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE TIEMPO Y BASE DE DATOS ---
def obtener_tiempo_rd():
    zona = pytz.timezone('America/Santo_Domingo')
    ahora = datetime.now(zona)
    return ahora.strftime("%d/%m/%Y"), ahora.strftime("%I:%M %p"), ahora.strftime("%m-%Y"), ahora.date(), ahora

def iniciar_db():
    # CONECTA EXACTAMENTE AL ARCHIVO DE TU FOTO
    conn = sqlite3.connect("nexus_quevedo_core.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS glucosa (id INTEGER PRIMARY KEY, fecha TEXT, hora TEXT, momento TEXT, valor INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS medicamentos (id INTEGER PRIMARY KEY, nombre TEXT, dosis TEXT, horario TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS citas (id INTEGER PRIMARY KEY, doctor TEXT, fecha TEXT, motivo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS finanzas (id INTEGER PRIMARY KEY, fecha TEXT, mes TEXT, tipo TEXT, categoria TEXT, detalle TEXT, monto REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS config (param TEXT PRIMARY KEY, valor REAL)')
    conn.commit()
    return conn

def interpretar_salud(valor, momento):
    if momento == "Ayunas":
        if 70 <= valor <= 100: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 101 <= valor <= 125: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"
    elif "Post" in momento:
        if valor < 140: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 140 <= valor <= 199: return "AMARILLO", "PRE-DIABETES", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "ALTO", "background-color: #b71c1c; color: white;"
    elif momento == "Antes de dormir":
        if 100 <= valor <= 140: return "VERDE", "NORMAL", "background-color: #1b5e20; color: white;"
        elif 141 <= valor <= 160: return "AMARILLO", "MEDIO", "background-color: #fbc02d; color: black;"
        else: return "ROJO", "REVISAR", "background-color: #b71c1c; color: white;"
    return "GRIS", "N/A", ""

# --- 3. SEGURIDAD ---
if "password_correct" not in st.session_state:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>🌐 NEXUS CONTROL</h1>", unsafe_allow_html=True)
    _, col_b, _ = st.columns([1,2,1])
    with col_b:
        with st.form("login"):
            pwd = st.text_input("Contraseña de Acceso:", type="password")
            if st.form_submit_button("INGRESAR"):
                if pwd == "admin123":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Acceso Denegado")
    st.stop()

# --- 4. INICIALIZACIÓN DE DATOS ---
db = iniciar_db()
f_str, h_str, mes_str, f_obj, ahora_full = obtener_tiempo_rd()
res_conf = db.execute("SELECT valor FROM config WHERE param='presupuesto'").fetchone()
presupuesto_mensual = res_conf[0] if res_conf else 0.0

# --- 5. INTERFAZ Y NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f"<h2 style='text-align: center;'>SR. QUEVEDO</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #8b949e;'>{f_str} | {h_str}</p>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("MÓDULOS ACTIVOS", ["🏠 PANEL DE CONTROL", "💰 CONTROL FINANCIERO", "🩺 SALUD Y GLUCOSA", "📝 BITÁCORA PERSONAL", "⚙️ CONFIGURACIÓN"])
    st.markdown("---")
    if st.button("SALIR DEL SISTEMA"):
        del st.session_state["password_correct"]
        st.rerun()

# --- MÓDULO 1: PANEL DE CONTROL (INICIO) ---
if menu == "🏠 PANEL DE CONTROL":
    st.title("Panel de Control General")
    st.markdown("### 🔔 Estatus Actual")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a: # Resumen Citas
        citas = db.execute("SELECT doctor, fecha FROM citas ORDER BY fecha ASC").fetchall()
        prox_cita = "Sin citas"
        for c in citas:
            try:
                if datetime.strptime(c[1], '%Y-%m-%d').date() >= f_obj:
                    prox_cita = f"{c[0]} ({c[1]})"
                    break
            except: pass
        st.markdown(f"<div class='alerta-card' style='border-left-color: #3b82f6;'><strong>📅 PRÓXIMA CITA</strong><br>{prox_cita}</div>", unsafe_allow_html=True)

    with col_b: # Resumen Glucosa
        ult_g = db.execute("SELECT valor, momento FROM glucosa ORDER BY id DESC LIMIT 1").fetchone()
        if ult_g:
            slug, txt, _ = interpretar_salud(ult_g[0], ult_g[1])
            color = "#27ae60" if slug == "VERDE" else "#e74c3c"
            st.markdown(f"<div class='alerta-card' style='border-left-color: {color};'><strong>🩸 ÚLTIMA GLUCOSA</strong><br>{ult_g[0]} mg/dL ({txt})</div>", unsafe_allow_html=True)
        else: st.markdown("<div class='alerta-card'><strong>🩸 SALUD</strong><br>Sin registros</div>", unsafe_allow_html=True)

    with col_c: # Resumen Gastos
        gastos_tot = abs(db.execute("SELECT SUM(monto) FROM finanzas WHERE tipo='GASTO' AND mes=?", (mes_str,)).fetchone()[0] or 0)
        st.markdown(f"<div class='alerta-card' style='border-left-color: #f1c40f;'><strong>💰 GASTOS {mes_str}</strong><br>RD$ {gastos_tot:,.2f}</div>", unsafe_allow_html=True)

# --- MÓDULO 2: FINANZAS ---
elif menu == "💰 CONTROL FINANCIERO":
    st.title("Gestión de Ingresos y Gastos")
    df_f = pd.read_sql_query("SELECT * FROM finanzas ORDER BY id DESC", db)
    
    # Análisis de Presupuesto
    gastos_mes = abs(df_f[(df_f['tipo'] == 'GASTO') & (df_f['mes'] == mes_str)]['monto'].sum()) if not df_f.empty else 0
    if presupuesto_mensual > 0:
        dias_mes = 31 - f_obj.day + 1
        gasto_permitido = (presupuesto_mensual - gastos_mes) / dias_mes
        st.markdown(f'<div class="insight-card">💡 <b>GUÍA DE GASTO:</b> Para no excederte, puedes gastar <b>RD$ {max(0, gasto_permitido):,.2f} diarios</b> por el resto del mes.</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='balance-box'><h3>Balance Total</h3><h1 style='color:#2ecc71;'>RD$ {df_f['monto'].sum() if not df_f.empty else 0:,.2f}</h1></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='balance-box'><h3>Gastos del Mes</h3><h1 style='color:#e74c3c;'>RD$ {gastos_mes:,.2f}</h1></div>", unsafe_allow_html=True)

    with st.form("registro_fin"):
        col1, col2, col3 = st.columns([1,1,2])
        tipo = col1.selectbox("Tipo", ["GASTO", "INGRESO"])
        monto = col2.number_input("Monto RD$", min_value=0.0)
        cat = col3.text_input("Categoría (Ej: Supermercado, Farmacia)").upper()
        det = st.text_input("Detalle del movimiento").upper()
        if st.form_submit_button("REGISTRAR MOVIMIENTO"):
            m_final = -abs(monto) if tipo == "GASTO" else abs(monto)
            db.execute("INSERT INTO finanzas (fecha, mes, tipo, categoria, detalle, monto) VALUES (?,?,?,?,?,?)", (f_str, mes_str, tipo, cat, det, m_final))
            db.commit(); st.rerun()

    if not df_f.empty:
        st.dataframe(df_f[['fecha', 'tipo', 'categoria', 'detalle', 'monto']], use_container_width=True)
        st.markdown('<div class="btn-borrar-rojo">', unsafe_allow_html=True)
        if st.button("🗑️ Eliminar último registro"):
            db.execute("DELETE FROM finanzas WHERE id = (SELECT MAX(id) FROM finanzas)"); db.commit(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- MÓDULO 3: SALUD ---
elif menu == "🩺 SALUD Y GLUCOSA":
    st.title("Seguimiento Médico")
    df_g = pd.read_sql_query("SELECT * FROM glucosa ORDER BY id DESC", db)
    
    if not df_g.empty:
        promedio = df_g['valor'].head(15).mean()
        a1c = (46.7 + promedio) / 28.7
        st.markdown(f'<div class="insight-card">🩺 <b>ESTADO DE SALUD:</b> Promedio: <b>{promedio:.1f} mg/dL</b> | Hemoglobina Glicosilada Est. (A1C): <b>{a1c:.1f}%</b></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🩸 Glucosa", "💊 Medicamentos", "📅 Citas Médicas"])
    
    with tab1:
        with st.form("reg_glucosa", clear_on_submit=True):
            col_v, col_m = st.columns(2)
            val = col_v.number_input("Valor de Glucosa (mg/dL)", min_value=1)
            mom = col_m.selectbox("Momento", ["Ayunas", "Post-Desayuno", "Post-Almuerzo", "Post-Cena", "Antes de dormir"])
            if st.form_submit_button("GUARDAR LECTURA"):
                db.execute("INSERT INTO glucosa (fecha, hora, momento, valor) VALUES (?,?,?,?)", (f_str, h_str, mom, val))
                db.commit(); st.rerun()
        
        if not df_g.empty:
            st.plotly_chart(px.line(df_g.iloc[::-1], x='hora', y='valor', markers=True, title="Historial del Día", template="plotly_dark"), use_container_width=True)
            def highlight(row): return [interpretar_salud(row['valor'], row['momento'])[2]] * len(row)
            st.dataframe(df_g[['fecha', 'hora', 'momento', 'valor']].style.apply(highlight, axis=1), use_container_width=True)

    with tab2:
        df_m = pd.read_sql_query("SELECT * FROM medicamentos", db)
        for _, m in df_m.iterrows():
            st.info(f"💊 **{m['nombre']}** | {m['dosis']} | {m['horario']}")
        with st.form("reg_med"):
            n_m = st.text_input("Medicina"); d_m = st.text_input("Dosis"); h_m = st.text_input("Horario")
            if st.form_submit_button("Agregar"):
                db.execute("INSERT INTO medicamentos (nombre, dosis, horario) VALUES (?,?,?)", (n_m, d_m, h_m))
                db.commit(); st.rerun()

    with tab3:
        df_c = pd.read_sql_query("SELECT * FROM citas", db)
        if not df_c.empty: st.table(df_c[['doctor', 'fecha', 'motivo']])
        with st.form("reg_cita"):
            d_c = st.text_input("Doctor"); f_c = st.date_input("Fecha"); m_c = st.text_input("Motivo")
            if st.form_submit_button("Agendar"):
                db.execute("INSERT INTO citas (doctor, fecha, motivo) VALUES (?,?,?)", (d_c, str(f_c), m_c))
                db.commit(); st.rerun()

# --- MÓDULO 4: BITÁCORA ---
elif menu == "📝 BITÁCORA PERSONAL":
    st.title("Notas y Bitácora")
    path_notas = "nexus_notas.txt"
    if st.button("🗑️ Borrar Historial de Notas"):
        if os.path.exists(path_notas): os.remove(path_notas); st.rerun()
    
    nota_nueva = st.text_area("Escribir nueva nota:", height=100)
    if st.button("💾 Guardar Nota"):
        if nota_nueva:
            with open(path_notas, "a", encoding="utf-8") as f:
                f.write(f"[{f_str} {h_str}]: {nota_nueva}\n\n")
            st.success("Nota guardada"); st.rerun()
    
    if os.path.exists(path_notas):
        with open(path_notas, "r", encoding="utf-8") as f:
            st.text_area("Notas Guardadas:", f.read(), height=400)

# --- MÓDULO 5: CONFIGURACIÓN ---
elif menu == "⚙️ CONFIGURACIÓN":
    st.title("Ajustes del Sistema")
    nuevo_p = st.number_input("Presupuesto Mensual (RD$)", value=float(presupuesto_mensual))
    if st.button("Actualizar Presupuesto"):
        db.execute("INSERT OR REPLACE INTO config (param, valor) VALUES ('presupuesto', ?)", (nuevo_p,))
        db.commit(); st.success("Presupuesto actualizado")
