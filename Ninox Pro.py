import streamlit as st
import pandas as pd
import requests

# --- Configuración de tu API Ninox ---
NINOX_TEAM = "6dA5DFvfDTxCQxpDF"
NINOX_DATABASE = "yoq1qy9euurq"
NINOX_API_KEY = "d3c82d50-60d4-11f0-9dd2-0154422825e5"  
NINOX_TABLE_FACTURAS = "Facturas"  # Nombre exacto de la tabla

# --- Función para obtener datos de Ninox ---
def get_ninox_data(table_name):
    url = f"https://api.ninoxdb.de/v1/teams/{NINOX_TEAM}/databases/{NINOX_DATABASE}/tables/{table_name}/records"
    headers = {
        "Authorization": f"Bearer {NINOX_API_KEY}"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        records = response.json()
        # Convertir los registros a DataFrame
        data = []
        for rec in records:
            row = {field["name"]: field.get("value", "") for field in rec["fields"]}
            data.append(row)
        return pd.DataFrame(data)
    else:
        st.error(f"Error {response.status_code} al conectar con Ninox")
        return pd.DataFrame()

# --- Interfaz principal ---
st.title("Factura Electrónica")

# Botón para actualizar datos
if st.button("Actualizar datos de Ninox"):
    st.session_state["facturas"] = get_ninox_data(NINOX_TABLE_FACTURAS)

# Mostrar formulario del cliente (ejemplo de tu diseño)
st.selectbox("Seleccione Cliente", ["Roberto Sanchez", "Juan Sanchez", "Lionel Messi"])
col1, col2 = st.columns(2)
col1.text_input("RUC", "8-876-2342", disabled=True)
col2.text_input("Teléfono", "6863-3763", disabled=True)
col1.text_input("DV", "11", disabled=True)
col2.text_input("Correo", "biomedical@iompanama.com", disabled=True)
st.text_area("Dirección", "Panamá", disabled=True)
st.text_input("Factura No.", "00000072", disabled=True)
st.date_input("Fecha Emisión", pd.to_datetime("2025-07-29"))

# --- Mostrar Facturas Procesadas ---
st.subheader("Facturas Procesadas")

if "facturas" in st.session_state:
    df_facturas = st.session_state["facturas"]

    if not df_facturas.empty:
        # Filtrar solo las procesadas
        df_procesadas = df_facturas[df_facturas["Estado"] == "Procesado"]
        # Mostrar en tabla
        st.dataframe(df_procesadas, use_container_width=True)
    else:
        st.info("No hay facturas procesadas disponibles.")
else:
    st.info("Presiona 'Actualizar datos de Ninox' para cargar facturas.")




