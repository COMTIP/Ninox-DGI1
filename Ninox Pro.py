import streamlit as st
import requests
import pandas as pd

# ==================== CONFIGURACIÓN NINOX ====================
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"  # Cambia por tu token
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

# ==================== FUNCIONES AUXILIARES ====================

def obtener_notas_credito():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Nota%20de%20Credito/records"
    r = requests.get(url, headers=HEADERS)
    if r.ok:
        return r.json()
    return []

def obtener_clientes():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Clientes/records"
    r = requests.get(url, headers=HEADERS)
    if r.ok:
        return {c['id']: c['fields'] for c in r.json()}
    return {}

def obtener_facturas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    r = requests.get(url, headers=HEADERS)
    if r.ok:
        return {f['id']: f['fields'] for f in r.json()}
    return {}

# ==================== STREAMLIT INTERFAZ ====================

st.set_page_config(page_title="Notas de Crédito - Ninox", layout="centered")
st.title("Notas de Crédito (Ninox ➔ Streamlit)")

notas_credito = obtener_notas_credito()
clientes = obtener_clientes()
facturas = obtener_facturas()

if not notas_credito:
    st.warning("No hay notas de crédito registradas.")
    st.stop()

# Procesar las notas para DataFrame amigable
datos = []
for n in notas_credito:
    f = n["fields"]
    cliente = ""
    factura = ""
    # Si tienes relación, Ninox guarda los IDs
    if "Clientes" in f and f["Clientes"]:
        cliente_id = f["Clientes"][0] if isinstance(f["Clientes"], list) else f["Clientes"]
        cliente = clientes.get(cliente_id, {}).get("Nombre", "")
    if "Facturas" in f and f["Facturas"]:
        factura_id = f["Facturas"][0] if isinstance(f["Facturas"], list) else f["Facturas"]
        factura = facturas.get(factura_id, {}).get("Factura No.", "")
    datos.append({
        "Credit No": f.get("Credit No", ""),
        "Fecha": f.get("Fecha", ""),
        "Monto": f.get("Monto", ""),
        "Estado": f.get("Estado", ""),
        "Cliente": cliente,
        "Factura Relacionada": factura
    })

df = pd.DataFrame(datos)
st.subheader("Listado de Notas de Crédito")
st.dataframe(df, use_container_width=True)

# Seleccionar una Nota de Crédito
creditos_disponibles = df["Credit No"].tolist()
credito_seleccionado = st.selectbox("Selecciona una Nota de Crédito", creditos_disponibles)
detalle = df[df["Credit No"] == credito_seleccionado].iloc[0]

st.markdown("### Detalle de la Nota de Crédito Seleccionada")
st.write(f"**Número:** {detalle['Credit No']}")
st.write(f"**Fecha:** {detalle['Fecha']}")
st.write(f"**Monto:** ${detalle['Monto']}")
st.write(f"**Estado:** {detalle['Estado']}")
st.write(f"**Cliente:** {detalle['Cliente']}")
st.write(f"**Factura Relacionada:** {detalle['Factura Relacionada']}")

# ---- Opcional: JSON para enviar a DGI ----
st.markdown("#### JSON preparado para integración DGI")
json_dgi = {
    "tipoDocumento": "NOTA_CREDITO",
    "numero": detalle["Credit No"],
    "fecha": str(detalle["Fecha"]),
    "monto": detalle["Monto"],
    "cliente": detalle["Cliente"],
    "factura_relacionada": detalle["Factura Relacionada"]
}
st.json(json_dgi)



