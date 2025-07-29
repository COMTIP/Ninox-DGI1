import streamlit as st
import requests
import json

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

def generate_dgi_json(facturas, lineas, clientes):
    dgi_payload = []
    for factura in facturas:
        factura_id = factura.get("id")
        cliente_id = factura["fields"].get("Cliente")
        
        # Filtrar líneas de la factura
        factura_lineas = [l for l in lineas if l["fields"].get("Factura") == factura_id]
        if not factura_lineas:
            continue

        # Obtener datos del cliente
        cliente = next((c for c in clientes if c.get("id") == cliente_id), None)

        # Estructura para DGI
        dgi_payload.append({
            "FacturaID": factura_id,
            "Fecha": factura["fields"].get("FechaEmisión"),
            "Cliente": {
                "Nombre": cliente["fields"].get("Nombre") if cliente else "N/A",
                "CedulaRUC": cliente["fields"].get("Cédula/RUC") if cliente else "N/A",
                "Telefono": cliente["fields"].get("Teléfono") if cliente else "N/A"
            },
            "Lineas": [
                {
                    "Descripcion": l["fields"].get("Descripción"),
                    "Cantidad": l["fields"].get("Cantidad"),
                    "PrecioUnitario": l["fields"].get("Precio Unitario"),
                    "Subtotal": l["fields"].get("Subtotal Línea"),
                    "ITBMS": l["fields"].get("Valor ITBMS"),
                } for l in factura_lineas
            ]
        })
    return dgi_payload

def send_to_dgi(data):
    # Simulación de envío a DGI
    DGI_URL = "https://dgi.example.com/api/facturas"  # Reemplaza con la URL real de la DGI
    response = requests.post(DGI_URL, headers={"Content-Type": "application/json"}, data=json.dumps(data))
    return response.status_code, response.text

# ===== INTERFAZ STREAMLIT =====
st.sidebar.button("Cerrar sesión")

st.title("Integración Ninox → DGI")
if st.button("Actualizar datos de Ninox"):
    clientes = get_ninox_table("Clientes")
    facturas = get_ninox_table("Facturas")
    lineas = get_ninox_table("LineasFactura")

    if clientes and facturas and lineas:
        st.success("Datos cargados correctamente")
        
        dgi_json = generate_dgi_json(facturas, lineas, clientes)

        if dgi_json:
            st.json(dgi_json)
            enviar = st.button("Enviar a DGI")
            if enviar:
                status, respuesta = send_to_dgi(dgi_json)
                if status == 200:
                    st.success("Facturas enviadas correctamente a la DGI")
                else:
                    st.error(f"Error al enviar a DGI: {status} - {respuesta}")
        else:
            st.warning("No hay facturas con líneas asociadas")


