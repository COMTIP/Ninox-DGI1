import streamlit as st
import requests
from datetime import datetime

# Config Ninox
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def obtener_tabla(tabla):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{tabla}/records"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.ok else []

# Carga de datos de Ninox solo si no están en cache
if st.button("Actualizar datos de Ninox"):
    st.session_state.pop("facturas", None)
    st.session_state.pop("clientes", None)

if "facturas" not in st.session_state:
    st.session_state["facturas"] = obtener_tabla("Facturas")
if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_tabla("Clientes")

facturas = st.session_state["facturas"]
clientes = st.session_state["clientes"]

if not facturas or not clientes:
    st.warning("No hay facturas o clientes en Ninox")
    st.stop()

# Mapeo rápido: cliente_id -> campos de cliente
clientes_dict = {c["id"]: c["fields"] for c in clientes}

# Selector de Factura (por número)
facturas_opciones = [
    f'{f["fields"].get("Factura No.", "")} - {f["fields"].get("Fecha + Hora", "")}'
    for f in facturas
]
factura_idx = st.selectbox("Seleccione Factura", range(len(facturas_opciones)), format_func=lambda x: facturas_opciones[x])
factura = facturas[factura_idx]["fields"]

# Relacionar cliente de la factura (si existe)
cliente_ids = factura.get("Clientes", [])
if cliente_ids:
    # Puede ser lista o string; Ninox API usualmente da lista de IDs
    cliente_id = cliente_ids[0] if isinstance(cliente_ids, list) else cliente_ids
    cliente = clientes_dict.get(cliente_id, {})
else:
    cliente = {}

col1, col2 = st.columns(2)
with col1:
    st.text_input("RUC", value=cliente.get('RUC', ''), disabled=True)
    st.text_input("DV", value=cliente.get('DV', ''), disabled=True)
    st.text_area("Dirección", value=cliente.get('Dirección', ''), disabled=True)
with col2:
    st.text_input("Teléfono", value=cliente.get('Teléfono', ''), disabled=True)
    st.text_input("Correo", value=cliente.get('Correo', ''), disabled=True)

st.text_input("Factura No.", value=factura.get("Factura No.", ""), disabled=True)
# Fecha Emisión de la factura o fecha actual si no hay
st.date_input("Fecha Emisión", value=factura.get("Fecha + Hora", datetime.today()))


