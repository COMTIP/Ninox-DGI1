import streamlit as st
import pandas as pd
import requests

# -----------------------------
# CONFIGURACIÓN DE INTERFAZ
# -----------------------------
st.set_page_config(page_title="Factura Electrónica", layout="centered")
st.title("Factura Electrónica")

# -----------------------------
# FUNCIÓN PARA CARGAR DATOS DESDE NINOX
# -----------------------------
# Si tienes la API Key de Ninox:
# Reemplaza estos valores:
API_KEY = "TU_API_KEY"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

def cargar_facturas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        # Convertir a DataFrame
        rows = []
        for record in data:
            fields = record["fields"]
            rows.append({
                "Factura No.": fields.get("Factura No."),
                "Fecha + Hora": fields.get("Fecha + Hora"),
                "Medio de Pago": fields.get("Medio de Pago"),
                "Total": fields.get("Total"),
                "Emitido por": fields.get("Emitido por"),
                "Estado": fields.get("Estado"),
            })
        df = pd.DataFrame(rows)
        return df
    else:
        st.error("Error al obtener datos de Ninox")
        return pd.DataFrame()

# -----------------------------
# CARGAR DATOS
# -----------------------------
df_facturas = cargar_facturas()

# Filtrar solo las facturas procesadas
df_procesadas = df_facturas[df_facturas["Estado"] == "Procesado"]

if df_procesadas.empty:
    st.warning("No hay facturas procesadas.")
else:
    # -----------------------------
    # SELECCIÓN DE CLIENTE
    # -----------------------------
    clientes = df_procesadas["Emitido por"].unique()
    cliente_sel = st.selectbox("Seleccione Cliente", clientes)

    # Filtrar facturas por cliente
    facturas_cliente = df_procesadas[df_procesadas["Emitido por"] == cliente_sel]

    # -----------------------------
    # MOSTRAR INFORMACIÓN DE FACTURA
    # -----------------------------
    factura = facturas_cliente.iloc[-1]  # Última factura procesada de ese cliente

    # Simular datos de cliente (esto podría venir de otra tabla "Clientes")
    ruc = "8-876-2342"
    telefono = "6863-3763"
    dv = "11"
    correo = "biomedical@iompanama.com"
    direccion = "Panamá"

    st.text_input("RUC", ruc, disabled=True)
    st.text_input("Teléfono", telefono, disabled=True)
    st.text_input("DV", dv, disabled=True)
    st.text_input("Correo", correo, disabled=True)
    st.text_area("Dirección", direccion, disabled=True)
    st.text_input("Factura No.", factura["Factura No."], disabled=True)
    st.text_input("Fecha Emisión", factura["Fecha + Hora"], disabled=True)
    st.text_input("Medio de Pago", factura["Medio de Pago"], disabled=True)
    st.text_input("Total", f"${factura['Total']}", disabled=True)




