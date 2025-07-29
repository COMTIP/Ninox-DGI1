import streamlit as st
import pandas as pd
import requests

# --- Configuración API Ninox ---
NINOX_TEAM = "6dA5DFvfDTxCQxpDF"
NINOX_DATABASE = "yoq1qy9euurq"
NINOX_API_KEY = "d3c82d50-60d4-11f0-9dd2-0154422825e5"

# ID de tablas (según Ninox)
TABLE_CLIENTES = "B"
TABLE_FACTURAS = "E"

# --- Función para obtener datos de Ninox ---
def get_ninox_data(table_id):
    url = f"https://api.ninoxdb.de/v1/teams/{NINOX_TEAM}/databases/{NINOX_DATABASE}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {NINOX_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        records = response.json()
        data = []
        for rec in records:
            row = {field["name"]: field.get("value", "") for field in rec["fields"]}
            data.append(row)
        return pd.DataFrame(data)
    else:
        st.error(f"Error {response.status_code} al conectar con Ninox")
        return pd.DataFrame()

# --- Título ---
st.title("Gestión de Facturación DGI")

# --- Cargar datos ---
clientes_df = get_ninox_data(TABLE_CLIENTES)
facturas_df = get_ninox_data(TABLE_FACTURAS)

# --- Selección de Cliente ---
if not clientes_df.empty:
    cliente_nombre = st.selectbox("Seleccione Cliente", clientes_df["Nombre"])
    cliente = clientes_df[clientes_df["Nombre"] == cliente_nombre].iloc[0]

    st.text_input("RUC", cliente.get("RUC", ""), disabled=True)
    st.text_input("Teléfono", cliente.get("Teléfono", ""), disabled=True)
    st.text_input("Correo", cliente.get("Correo", ""), disabled=True)
else:
    st.warning("No hay clientes en Ninox.")

# --- Mostrar Facturas Procesadas ---
st.subheader("Facturas Procesadas (Excluyendo 'Listo')")

if not facturas_df.empty:
    # Filtrar solo las facturas procesadas
    df_procesadas = facturas_df[
        (facturas_df["Estado"] == "Procesado")
    ]

    # Filtrar por cliente seleccionado
    if "Cliente" in df_procesadas.columns:
        df_procesadas = df_procesadas[df_procesadas["Cliente"] == cliente_nombre]

    st.dataframe(df_procesadas, use_container_width=True)

    # Botón para exportar a Excel
    if not df_procesadas.empty:
        excel_file = df_procesadas.to_excel(index=False)
        st.download_button(
            label="📥 Exportar a Excel para DGI",
            data=excel_file,
            file_name=f"Facturas_Procesadas_{cliente_nombre}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("No hay facturas en Ninox.")



