import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import base64
from io import BytesIO
import matplotlib.pyplot as plt

# -------------------------
# Configuración y estilo
# -------------------------
st.set_page_config(page_title="NEXUS QUEVEDO PRO", layout="wide")
st.markdown(
    """<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; background-color: #0E1117; color: #E6EEF3; }
    .stButton>button { background-color:#2563EB; color: white; width: 100%; border-radius: 5px; height: 3em; }
    </style>""",
    unsafe_allow_html=True,
)

DBPATH = "nexuspro_data.db"

# -------------------------
# Utilidades de base de datos
# -------------------------
def get_conn():
    return sqlite3.connect(DBPATH, check_same_thread=False)

def init_tables():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                user TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS glucosa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                fecha TEXT,
                valor REAL
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS finanzas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                monto REAL,
                tipo TEXT,
                fecha TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS meds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                nombre TEXT,
                dosis TEXT,
                hora TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS citas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                fecha TEXT,
                doctor TEXT
            )
        ''')
        conn.commit()

def ejecutar_consulta(sql: str, params: tuple = (), fetch: str = "all"):
    if not sql:
        return None
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(sql, params)
        if fetch == "one":
            return c.fetchone()
        if fetch == "all":
            return c.fetchall()
        conn.commit()
    return None

# -------------------------
# Seguridad mínima (hash)
# -------------------------
def encriptar(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def registrar_usuario(user: str, password: str):
    if not user or not password:
        return False, "Usuario y contraseña son obligatorios."
    user = user.strip()
    try:
        ejecutar_consulta('INSERT INTO usuarios (user, password) VALUES (?,?)', (user, encriptar(password)), fetch="none")
        return True, "Cuenta creada correctamente."
    except sqlite3.IntegrityError:
        return False, "El usuario ya existe."
    except Exception as e:
        return False, f"Error: {e}"

def verificar_usuario(user: str, password: str) -> bool:
    if not user or not password:
        return False
    row = ejecutar_consulta('SELECT password FROM usuarios WHERE user = ?', (user.strip(),), fetch="one")
    if not row:
        return False
    return row[0] == encriptar(password)

# -------------------------
# Funciones de negocio
# -------------------------
def guardar_glucosa(user: str, valor: float):
    if valor is None:
        return False, "Valor inválido."
    fecha = datetime.datetime.now().isoformat(timespec="seconds")
    ejecutar_consulta('INSERT INTO glucosa (user, fecha, valor) VALUES (?,?,?)', (user, fecha, float(valor)), fetch="none")
    return True, fecha

def obtener_glucosa(user: str) -> pd.DataFrame:
    rows = ejecutar_consulta('SELECT id, fecha, valor FROM glucosa WHERE user=? ORDER BY fecha DESC', (user,), fetch="all")
    df = pd.DataFrame(rows, columns=["id", "fecha", "valor"]) if rows else pd.DataFrame(columns=["id", "fecha", "valor"])
    return df

def borrar_glucosa(rowid: int, user: str):
    ejecutar_consulta('DELETE FROM glucosa WHERE id=? AND user=?', (rowid, user), fetch="none")

def registrar_finanza(user: str, monto: float, tipo: str):
    if monto is None or monto < 0:
        return False, "Monto inválido."
    fecha = datetime.datetime.now().date().isoformat()
    ejecutar_consulta('INSERT INTO finanzas (user, monto, tipo, fecha) VALUES (?,?,?,?)', (user, float(monto), tipo, fecha), fetch="none")
    return True, fecha

def obtener_finanzas(user: str) -> pd.DataFrame:
    rows = ejecutar_consulta('SELECT id, monto, tipo, fecha FROM finanzas WHERE user=? ORDER BY fecha DESC', (user,), fetch="all")
    df = pd.DataFrame(rows, columns=["id", "monto", "tipo", "fecha"]) if rows else pd.DataFrame(columns=["id", "monto", "tipo", "fecha"])
    return df

def borrar_finanza(rowid: int, user: str):
    ejecutar_consulta('DELETE FROM finanzas WHERE id=? AND user=?', (rowid, user), fetch="none")

def generar_backup_excel_bytes(user: str) -> BytesIO:
    df_gluc = obtener_glucosa(user)
    df_fin = obtener_finanzas(user)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_gluc.to_excel(writer, sheet_name="Glucosa", index=False)
        df_fin.to_excel(writer, sheet_name="Finanzas", index=False)
    output.seek(0)
    return output

# -------------------------
# Inicialización
# -------------------------
init_tables()

# -------------------------
# Estado de sesión y UI de acceso
# -------------------------
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = ""

if not st.session_state.login:
    st.title("🛡️ NEXUS PRO - Acceso Soberano")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Entrar")
        u = st.text_input("Usuario", key="ulogin")
        p = st.text_input("Clave", type="password", key="plogin")
        if st.button("Iniciar Sesión"):
            if verificar_usuario(u, p):
                st.session_state.login = True
                st.session_state.user = u.strip()
                st.success("Bienvenido.")
                st.rerun()
            else:
                st.error("Credenciales incorrectas o usuario inexistente.")

    with col2:
        st.subheader("Registro")
        nu = st.text_input("Nuevo Usuario", key="nureg")
        np = st.text_input("Nueva Clave", type="password", key="npreg")
        if st.button("Crear Cuenta"):
            ok, msg = registrar_usuario(nu, np)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown("---")
    st.info("Si necesita ayuda para crear la cuenta, pida a un familiar que le asista.")
    st.stop()

# -------------------------
# Dashboard principal
# -------------------------
st.sidebar.title(f"Soberano: {st.session_state.user}")
menu = st.sidebar.radio("Navegación", ["💰 Finanzas", "🏥 Salud e IA", "📸 Visor PDF", "🔒 Cerrar Sesión"])

if menu == "💰 Finanzas":
    st.header("Presupuesto e Inteligencia Financiera")
    col_a, col_b = st.columns([2, 1])
    df_f = obtener_finanzas(st.session_state.user)
    
    with col_a:
        m = st.number_input("Monto RD$:", min_value=0.0, format="%.2f", step=1.0)
        t = st.selectbox("Operación:", ["Ingreso", "Gasto"])
        if st.button("Registrar Transacción"):
            ok, msg = registrar_finanza(st.session_state.user, m, t)
            if ok:
                st.success("Transacción registrada.")
                st.rerun()
            else:
                st.error(msg)

        st.subheader("Movimientos recientes")
        if not df_f.empty:
            st.dataframe(df_f, use_container_width=True)
            st.write("Borrar movimiento (últimos 10):")
            for _, row in df_f.head(10).iterrows():
                cols = st.columns([6,1])
                cols[0].write(f"ID {int(row['id'])} — {row['fecha']} — {row['tipo']} RD$ {row['monto']:,.2f}")
                if cols[1].button("Borrar", key=f"delfin{int(row['id'])}"):
                    borrar_finanza(int(row['id']), st.session_state.user)
                    st.rerun()
        else:
            st.info("No hay movimientos registrados.")

    with col_b:
        ingresos = df_f[df_f['tipo']=='Ingreso']['monto'].sum() if not df_f.empty else 0.0
        gastos = df_f[df_f['tipo']=='Gasto']['monto'].sum() if not df_f.empty else 0.0
        bal = ingresos - gastos
        st.metric("Presupuesto Disponible", f"RD$ {bal:,.2f}", delta=f"RD$ {ingresos:,.2f} ingresos / RD$ {gastos:,.2f} gastos")
        
        if st.button("Generar Backup (Excel)"):
            bio = generar_backup_excel_bytes(st.session_state.user)
            st.download_button(
                label="📥 Descargar Backup Excel",
                data=bio,
                file_name="backup_nexus.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif menu == "🏥 Salud e IA":
    st.header("Módulo de Salud Inteligente")
    col1, col2 = st.columns([2,1])
    df_g = obtener_glucosa(st.session_state.user)
    
    with col1:
        gluc = st.number_input("Valor Glucosa (mg/dL):", min_value=0.0, format="%.1f")
        if st.button("Guardar Glucosa"):
            ok, fecha = guardar_glucosa(st.session_state.user, gluc)
            if ok:
                if 70 <= gluc <= 125:
                    st.success("🟢 NORMAL")
                elif 126 <= gluc <= 160:
                    st.warning("🟡 PRECAUCIÓN")
                else:
                    st.error("🔴 ALERTA CRÍTICA")
                st.rerun()
            else:
                st.error("No se pudo guardar el registro.")

        st.subheader("Registros de Glucosa")
        if not df_g.empty:
            st.dataframe(df_g, use_container_width=True)
            st.write("Borrar registro (últimos 10):")
            for _, row in df_g.head(10).iterrows():
                cols = st.columns([6,1])
                cols[0].write(f"ID {int(row['id'])} — {row['fecha']} — {row['valor']}")
                if cols[1].button("Borrar", key=f"delgluc{int(row['id'])}"):
                    borrar_glucosa(int(row['id']), st.session_state.user)
                    st.rerun()

            try:
                dfplot = df_g.copy()
                dfplot['fechadt'] = pd.to_datetime(dfplot['fecha'])
                dfplot_sorted = dfplot.sort_values('fechadt')
                fig, ax = plt.subplots(figsize=(8,3))
                ax.plot(df_plot_sorted['fechadt'], df_plot_sorted['valor'], marker='o', color='#60A5FA')
                ax.set_title("Tendencia de Glucosa")
                ax.set_ylabel("mg/dL")
                plt.xticks(rotation=25)
                plt.tight_layout()
                st.pyplot(fig)
            except Exception:
                st.info("No se pudo generar el gráfico de tendencia.")
        else:
            st.info("Aún no hay registros de glucosa.")

    with col2:
        st.subheader("Medicamentos")
        nombre_m = st.text_input("Nombre del Medicamento")
        dosis_m = st.text_input("Dosis")
        hora_m = st.time_input("Hora de toma")
        if st.button("Registrar Medicamento"):
            ejecutar_consulta('INSERT INTO meds (user, nombre, dosis, hora) VALUES (?,?,?,?)', (st.session_state.user, nombre_m, dosis_m, str(hora_m)), fetch="none")
            st.success("Medicamento registrado.")

        st.write("---")
        st.subheader("Agendar Cita")
        fecha_c = st.date_input("Fecha de cita")
        doctor_c = st.text_input("Doctor / Especialidad", key="doctorinput")
        if st.button("Agendar Cita"):
            ejecutar_consulta('INSERT INTO citas (user, fecha, doctor) VALUES (?,?,?)', (st.session_state.user, fecha_c.isoformat(), doctor_c), fetch="none")
            st.success("Cita agendada.")

elif menu == "📸 Visor PDF":
    st.header("Visor de PDF")
    up = st.file_uploader("Subir Análisis (PDF)", type=['pdf'])
    if up:
        try:
            b64 = base64.b64encode(up.read()).decode('utf-8')
            st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf">', unsafe_allow_html=True)
        except Exception:
            st.error("No se pudo mostrar el PDF.")

elif menu == "🔒 Cerrar Sesión":
    st.session_state.login = False
    st.session_state.user = ""
    st.rerun()
