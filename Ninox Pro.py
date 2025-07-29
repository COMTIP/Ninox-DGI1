import streamlit as st
import requests
import pandas as pd

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
st.title("Clientes de Ninox")

clientes = get_ninox_table("Clientes")

if clientes:
    # Convertir a DataFrame
    data = []
    for c in clientes:
        fields = c.get("fields", {})
        data.append({
            "Nombre": fields.get("Nombre", ""),
            "RUC": fields.get("RUC", ""),
            "DV": fields.get("DV", ""),
            "Dirección": fields.get("Dirección", ""),
            "Teléfono": fields.get("Teléfono", ""),
            "Correo": fields.get("Correo", "")
        })

    df = pd.DataFrame(data)
    st.dataframe(df)
else:
    st.warning("No se encontraron clientes.")



