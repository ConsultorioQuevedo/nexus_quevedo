import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px

st.set_page_config(page_title="Nexus AI", layout="wide")

DB="nexus_ai.db"

def db():
    return sqlite3.connect(DB, check_same_thread=False)

def run(q,p=()):
    with db() as c:
        cur=c.cursor()
        cur.execute(q,p)
        c.commit()
        return cur.fetchall()

# DB
run("CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)")
run("CREATE TABLE IF NOT EXISTS finanzas(id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL)")

# FUNCIONES
def add_g(v):
    run("INSERT INTO glucosa VALUES(NULL,?,?)",(datetime.datetime.now(),v))

def get_g():
    return pd.DataFrame(run("SELECT * FROM glucosa"),columns=["id","fecha","valor"])

def add_f(t,m):
    run("INSERT INTO finanzas VALUES(NULL,?,?,?)",(datetime.datetime.now(),t,m))

def get_f():
    return pd.DataFrame(run("SELECT * FROM finanzas"),columns=["id","fecha","tipo","monto"])

def bal():
    df=get_f()
    if df.empty: return 0
    return df[df.tipo=="ingreso"].monto.sum()-df[df.tipo=="gasto"].monto.sum()

def pred():
    df=get_g()
    if len(df)>2:
        return df.valor.mean()
    return 0

# UI
st.title("🧠 Nexus Inteligente")

col1,col2,col3=st.columns(3)
col1.metric("💰 Balance",bal())
col2.metric("🩺 Glucosa Prom",pred())
col3.metric("📊 Registros",len(get_g()))

st.divider()

# INPUTS
c1,c2=st.columns(2)

with c1:
    st.subheader("Glucosa")
    v=st.number_input("Valor")
    if st.button("Guardar Glucosa"):
        add_g(v)
        st.rerun()

with c2:
    st.subheader("Finanzas")
    t=st.selectbox("Tipo",["ingreso","gasto"])
    m=st.number_input("Monto")
    if st.button("Guardar Movimiento"):
        add_f(t,m)
        st.rerun()

st.divider()

# GRÁFICAS
dfg=get_g()
if not dfg.empty:
    fig=px.line(dfg,x="fecha",y="valor",title="Glucosa")
    st.plotly_chart(fig,use_container_width=True)

dff=get_f()
if not dff.empty:
    fig2=px.pie(dff,names="tipo",values="monto",title="Finanzas")
    st.plotly_chart(fig2,use_container_width=True)

# ALERTAS
p=pred()
if p>140:
    st.error("⚠ Glucosa alta")
elif p<70 and p!=0:
    st.warning("⚠ Glucosa baja")
elif p!=0:
    st.success("✅ Todo bien")

# LINKS
st.markdown("### Compartir")
st.markdown("[📲 WhatsApp](https://wa.me/123456789)")
st.markdown("[✉ Gmail](mailto:test@gmail.com)")
