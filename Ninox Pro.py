import streamlit as st
import requests
from datetime import datetime

API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DB_ID = "yoq1qy9euurq"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def obtener_tabla(tabla):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DB_ID}/tables/{tabla}/records"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.ok else []

# Cargar datos
if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_tabla("Clientes")

clientes = st.session_state["clientes"]

st.subheader("Vista cruda de la tabla Clientes (primeros 5 registros)")
st.write(clientes[:5])

# Convertir a diccionario ID -> campos
clientes_dict = {c["id"]: c["fields"] for c in clientes}

# Si no existen registros, detener
if not clientes:
    st.warning("No se encontraron registros en la tabla Clientes.")
    st.stop()

# Seleccionar cliente manualmente para probar
clientes_list = list(clientes_dict.values())
nombres = [c.get("Nombre", "<sin nombre>") for c in clientes_list]
idx = st.selectbox("Selecciona un cliente (prueba)", range(len(nombres)), format_func=lambda x: nombres[x])
cliente = clientes_list[idx]

st.write("### Campos del cliente seleccionado (en vivo):")
st.json(cliente)

# Mostrar los campos específicos
col1, col2 = st.columns(2)
with col1:
    st.text_input("Nombre", value=cliente.get("Nombre", ""), disabled=True)
    st.text_input("RUC", value=cliente.get("RUC", ""), disabled=True)
    st.text_input("DV", value=cliente.get("DV", ""), disabled=True)
with col2:
    st.text_input("Teléfono", value=cliente.get("Teléfono", ""), disabled=True)
    st.text_input("Correo", value=cliente.get("Correo", ""), disabled=True)
    st.text_area("Dirección", value=cliente.get("Dirección", ""), disabled=True)


