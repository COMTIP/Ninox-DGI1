import streamlit as st
import pandas as pd
import requests

# ========================
# CONFIGURACIÓN NINOX
# ========================
NINOX_API_KEY = "TU_API_KEY"  # Coloca tu API Key
NINOX_TEAM = "6dA5DFvfDTxCQxpDF"  # Team ID
NINOX_DATABASE = "yoq1qy9euurq"  # Database ID

TABLE_CLIENTES = "Clientes"   # Nombre exacto en Ninox
TABLE_FACTURAS = "Facturas"   # Nombre exacto en Ninox

# ========================
# FUNCIÓN PARA CARGAR DATOS
# ========================
def get_ninox_data(table_name):
    url = f"https://api.ninoxdb.de/v1/teams/{NINOX_TEAM}/databases/{NINOX_DATABASE}/tables/{table_name}/records"
    headers = {"Authorization": f"Bearer {NINOX_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        records = response.json()
        data = [rec.get("fields", {}) for rec in records]  # fields es dict
        return pd.DataFrame(data)
    else:
        st.error(f"Error {response.status_code} al conectar con Ninox para la tabla {table_name}")
        return pd.DataFrame()

# ========================
# APP STREAMLIT
# ========================
st.set_page_config(page_title="Gestión de Facturación DGI", layout="wide")
st.title("Gestión de Facturación DGI")

# ------------------------
# CARGAR CLIENTES
# ------------------------
st.subheader("Clientes")
clientes_df = get_ninox_data(TABLE_CLIENTES)
st.dataframe(clientes_df)

# ------------------------
# CARGAR FACTURAS
# ------------------------
st.subheader("Facturas (solo Procesadas)")
facturas_df = get_ninox_data(TABLE_FACTURAS)

if not facturas_df.empty:
    # Filtrar solo Estado = Procesado
    if "Estado" in facturas_df.columns:
        facturas_procesadas = facturas_df[facturas_df["Estado"] == "Procesado"]
        st.dataframe(facturas_procesadas)
    else:
        st.warning("No se encontró la columna 'Estado' en Facturas.")
else:
    st.warning("No se cargaron facturas desde Ninox.")



