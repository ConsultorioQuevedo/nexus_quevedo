import streamlit as st
import pandas as pd
import sqlite3
import datetime
from io import BytesIO
import matplotlib.pyplot as plt
from fpdf import FPDF

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Nexus Pro", layout="wide")

DB = "nexus.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def run(q, p=()):
    with conn() as c:
        cur = c.cursor()
        cur.execute(q, p)
        c.commit()
        return cur.fetchall()

# -------------------------
# DB
# -------------------------
def init():
    run('''CREATE TABLE IF NOT EXISTS glucosa(id INTEGER PRIMARY KEY, fecha TEXT, valor REAL)''')
    run('''CREATE TABLE IF NOT EXISTS finanzas(id INTEGER PRIMARY KEY, fecha TEXT, tipo TEXT, monto REAL)''')

init()

# -------------------------
# FUNCIONES
# -------------------------
def guardar_glucosa(v):
    run("INSERT INTO glucosa VALUES(NULL,?,?)", (datetime.datetime.now(), v))

def listar_glucosa():
    return pd.DataFrame(run("SELECT * FROM glucosa"), columns=["id","fecha","valor"])

def color_glucosa(v):
    if v < 70: return "🔴 Bajo"
    elif v <= 140: return "🟢 Normal"
    return "🟡 Alto"

def prediccion():
    df = listar_glucosa()
    if len(df)>0:
        return df["valor"].mean()
    return 0

def guardar_finanza(t, m):
    run("INSERT INTO finanzas VALUES(NULL,?,?,?)", (datetime.datetime.now(), t, m))

def listar_finanzas():
    return pd.DataFrame(run("SELECT * FROM finanzas"), columns=["id","fecha","tipo","monto"])

def balance():
    df = listar_finanzas()
    if df.empty: return 0
    ing = df[df["tipo"]=="ingreso"]["monto"].sum()
    gas = df[df["tipo"]=="gasto"]["monto"].sum()
    return ing - gas

def pdf():
    p = FPDF()
    p.add_page()
    p.set_font("Arial", size=12)
    p.cell(200,10,"Reporte Nexus",ln=True)
    for _,r in listar_glucosa().iterrows():
        p.cell(200,10,f"{r['fecha']} {r['valor']}",ln=True)
    p.output("reporte.pdf")

# -------------------------
# UI
# -------------------------
st.title("Nexus Mejorado")

tabs = st.tabs(["Glucosa","Finanzas","Dashboard"])

# GLUCOSA
with tabs[0]:
    v = st.number_input("Valor")
    if st.button("Guardar"):
        guardar_glucosa(v)
        st.rerun()

    df = listar_glucosa()
    if not df.empty:
        df["estado"] = df["valor"].apply(color_glucosa)
        st.dataframe(df)

        st.line_chart(df["valor"])

# FINANZAS
with tabs[1]:
    t = st.selectbox("Tipo",["ingreso","gasto"])
    m = st.number_input("Monto")
    if st.button("Guardar finanza"):
        guardar_finanza(t,m)
        st.rerun()

    df = listar_finanzas()
    st.dataframe(df)

    st.metric("Balance", balance())

# DASHBOARD
with tabs[2]:
    st.metric("Promedio glucosa", prediccion())
    st.metric("Balance", balance())

    if prediccion() > 140:
        st.error("Glucosa alta")
    elif prediccion() < 70:
        st.warning("Glucosa baja")
    else:
        st.success("Normal")

# EXTRAS
st.markdown("[WhatsApp](https://wa.me/123456789)")
st.markdown("[Gmail](mailto:test@gmail.com)")

if st.button("Generar PDF"):
    pdf()
    st.success("PDF creado")
