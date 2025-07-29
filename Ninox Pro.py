import streamlit as st
import pandas as pd
import requests

# --- Configuración de la API Ninox ---
NINOX_TEAM = "6dA5DFvfDTxCQxpDF"         # ID de tu Team
NINOX_DATABASE = "yoq1qy9euurq"          # ID de tu Database
NINOX_API_KEY = "d3c82d50-60d4-11f0-9dd2-0154422825e5"            # Coloca tu API Key de Ninox aquí
TABLE_CLIENTES = "Clientes"              # Nombre de la tabla de clientes en Ninox
TABLE_FACTURAS = "Facturas"              # Nombre de la tabla de facturas en Ninox

# --- Función para obtener datos de una tabla de Ninox ---
def get_ninox_data(table_name):
    url = f"https://api.ninoxdb.de/v1/teams/{NINOX_TEAM}/databases/{NINOX_DATABASE}/tables/{table_name}/records"
    headers = {"Authorization": f"Bearer {NINOX_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        records = response.json()
        # Transformar a DataFrame
        data = []
        for rec in records:
            row = {field["name"]: field.get("value", "") for field in rec["fields"]}
            data.append(row)
        return pd.DataFrame(data)
    else:
        st.error(f"Error {response.status_code} al conectar con Ninox")
        return pd.DataFrame()

# --- Cargar datos de Ninox ---
st.title("Factura Electrónica")

if "clientes" not in st.session_state:
    st.session_state["clientes"] = get_ninox_data(TABLE_CLIENTES)
if "facturas" not in st.session_state:
    st.session_state["facturas"] = get_ninox_data(TABLE_FACTURAS)

clientes_df = st.session_state["clientes"]
facturas_df = st.session_state["facturas"]

# --- Selección dinámica de cliente ---
if not clientes_df.empty:
    cliente_nombre = st.selectbox("Seleccione Cliente", clientes_df["Nombre"])
    cliente = clientes_df[clientes_df["Nombre"] == cliente_nombre].iloc[0]

    col1, col2 = st.columns(2)
    col1.text_input("RUC", cliente.get("RUC", ""), disabled=True)
    col2.text_input("Teléfono", cliente.get("Teléfono", ""), disabled=True)
    col1.text_input("DV", cliente.get("DV", ""), disabled=True)
    col2.text_input("Correo", cliente.get("Correo", ""), disabled=True)
    st.text_area("Dirección", cliente.get("Dirección", ""), disabled=True)
else:
    st.warning("No hay clientes en Ninox.")

# --- Mostrar facturas filtradas dinámicamente ---
st.subheader("Facturas Procesadas (excluyendo 'Listo')")

if not facturas_df.empty:
    df_procesadas = facturas_df[(facturas_df["Estado"] == "Procesado")]
    st.dataframe(df_procesadas, use_container_width=True)
else:
    st.info("No hay facturas disponibles en Ninox.")

# --- Botón para actualizar ---
if st.button("Actualizar datos de Ninox"):
    st.session_state["clientes"] = get_ninox_data(TABLE_CLIENTES)
    st.session_state["facturas"] = get_ninox_data(TABLE_FACTURAS)
    st.experimental_rerun()




