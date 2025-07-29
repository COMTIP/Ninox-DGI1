import streamlit as st
import requests
import datetime

# ===== CONFIGURACIÓN =====
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# ===== FUNCIONES =====
def get_ninox_table(table_name):
    url = f"https://api.ninoxdb.de/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{table_name}/records"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al cargar '{table_name}': {response.status_code} - {response.reason}")
        return []

# ===== INTERFAZ STREAMLIT =====
st.title("Factura Electrónica")

if st.button("Actualizar datos de Ninox"):
    st.session_state["clientes"] = get_ninox_table("Clientes")

# Cargar clientes en la sesión si no existe
if "clientes" not in st.session_state:
    st.session_state["clientes"] = get_ninox_table("Clientes")

clientes = st.session_state["clientes"]

if clientes:
    # Lista de nombres para el selectbox
    nombres_clientes = [c.get("fields", {}).get("Nombre", "Sin Nombre") for c in clientes]
    cliente_seleccionado = st.selectbox("Seleccione Cliente", nombres_clientes)

    # Buscar los datos del cliente seleccionado
    cliente_data = next(
        (c for c in clientes if c.get("fields", {}).get("Nombre") == cliente_seleccionado), None
    )

    if cliente_data:
        fields = cliente_data.get("fields", {})

        # Campos de la factura
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("RUC", fields.get("RUC", ""), disabled=True)
            st.text_input("DV", fields.get("DV", ""), disabled=True)
            st.text_area("Dirección", fields.get("Dirección", ""), disabled=True)
        with col2:
            st.text_input("Teléfono", fields.get("Teléfono", ""), disabled=True)
            st.text_input("Correo", fields.get("Correo", ""), disabled=True)

        st.text_input("Factura No.", "00000072", disabled=True)
        st.text_input("Fecha Emisión", datetime.date.today().strftime("%Y/%m/%d"), disabled=True)
else:
    st.warning("No se encontraron clientes en Ninox.")



