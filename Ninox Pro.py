import streamlit as st
import requests
from datetime import datetime

# --- Login obligatorio ---
USUARIOS = {
    "Mispanama": "Maxilo2000",
    "usuario1": "password123"
}

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("<h2 style='text-align:center; color:#1c6758'>Acceso a Facturación Electrónica</h2>", unsafe_allow_html=True)
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario in USUARIOS and password == USUARIOS[usuario]:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.stop()

if st.sidebar.button("Cerrar sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- Ninox API config ---
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

def obtener_clientes():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Clientes/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def obtener_facturas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def obtener_lineas_factura():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/LineasFactura/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

# --- MAIN STREAMLIT ---
st.set_page_config(page_title="Factura Electrónica Ninox + DGI", layout="centered")
st.title("Factura Electrónica")

if st.button("Actualizar datos de Ninox"):
    st.session_state.pop("clientes", None)
    st.session_state.pop("facturas", None)
    st.session_state.pop("lineas_factura", None)

if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_clientes()
if "facturas" not in st.session_state:
    st.session_state["facturas"] = obtener_facturas()
if "lineas_factura" not in st.session_state:
    st.session_state["lineas_factura"] = obtener_lineas_factura()

clientes = st.session_state["clientes"]
facturas = st.session_state["facturas"]
lineas_factura = st.session_state["lineas_factura"]

# --- Filtrar solo facturas Pendientes ---
facturas_pendientes = [f for f in facturas if f["fields"].get("Estado", "") == "Pendiente"]
facturas_opciones = [f["fields"].get("Factura No.", "") for f in facturas_pendientes]

if not facturas_opciones:
    st.warning("No hay facturas pendientes en Ninox")
    st.stop()

# --- Selección de Factura ---
factura_no = st.selectbox("Seleccione una Factura Pendiente", facturas_opciones)

# Buscar datos de la factura seleccionada
factura_data = next((f for f in facturas_pendientes if f["fields"].get("Factura No.", "") == factura_no), None)
cliente_nombre = factura_data["fields"].get("Cliente", "")

# Buscar cliente
cliente_data = next((c for c in clientes if c["fields"].get("Nombre", "") == cliente_nombre), None)
if not cliente_data:
    st.warning("Cliente no encontrado en la tabla Clientes")
    st.stop()
cliente = cliente_data["fields"]

# --- Mostrar datos del cliente (solo lectura) ---
col1, col2 = st.columns(2)
with col1:
    st.text_input("RUC", value=cliente.get('RUC', ''), disabled=True)
    st.text_input("DV", value=cliente.get('DV', ''), disabled=True)
    st.text_area("Dirección", value=cliente.get('Dirección', ''), disabled=True)
with col2:
    st.text_input("Teléfono", value=cliente.get('Teléfono', ''), disabled=True)
    st.text_input("Correo", value=cliente.get('Correo', ''), disabled=True)

st.text_input("Factura No.", value=factura_no, disabled=True)
fecha_emision = factura_data["fields"].get("Fecha + Hora", "")
if isinstance(fecha_emision, str):
    fecha_emision_dt = datetime.strptime(fecha_emision.split(" ")[0], "%m/%d/%Y")  # formato mm/dd/yyyy
else:
    fecha_emision_dt = datetime.today()
st.text_input("Fecha Emisión", value=fecha_emision_dt.strftime("%Y-%m-%d"), disabled=True)

# --- Buscar y mostrar productos asociados (lineas de factura) ---
items = []
for lf in lineas_factura:
    fno = lf["fields"].get("Factura No.", "")
    if fno == factura_no:
        items.append({
            "codigo": lf["fields"].get("Código", ""),
            "descripcion": lf["fields"].get("Descripción", ""),
            "cantidad": lf["fields"].get("Cantidad", 0),
            "precioUnitario": float(str(lf["fields"].get("Precio Unitario", 0)).replace("$", "")),
            "valorITBMS": float(lf["fields"].get("ITBMS", 0)),
        })

if not items:
    st.warning("No se encontraron productos en Lineas Factura para esta factura.")
else:
    st.write("#### Productos de la factura")
    st.table([{k: v for k, v in item.items()} for item in items])

total_neto = sum(i["cantidad"] * i["precioUnitario"] for i in items)
total_itbms = sum(i["valorITBMS"] for i in items)
total_factura = total_neto + total_itbms
st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_factura:.2f}")

# --- Medio de pago ---
medio_pago = factura_data["fields"].get("Medio de Pago", "Efectivo")
medio_pago = st.selectbox("Medio de Pago", ["Efectivo", "Débito", "Crédito"], index=["Efectivo", "Débito", "Crédito"].index(medio_pago))

# --- Nombre de quien emite la factura
emisor = st.text_input("Nombre de quien emite la factura (obligatorio)", value=factura_data["fields"].get("Emitido por", ""))

# --- Enviar a la DGI ---
if st.button("Enviar Factura a DGI"):
    if not emisor.strip():
        st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
    elif not items:
        st.error("No hay productos para enviar en esta factura.")
    else:
        forma_pago = {
            "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Crédito": "03"}[medio_pago],
            "valorCuotaPagada": f"{total_factura:.2f}"
        }
        payload = {
            "documento": {
                "codigoSucursalEmisor": "0000",
                "tipoSucursal": "1",
                "datosTransaccion": {
                    "tipoEmision": "01",
                    "tipoDocumento": "01",
                    "numeroDocumentoFiscal": factura_no,
                    "puntoFacturacionFiscal": "001",
                    "naturalezaOperacion": "01",
                    "tipoOperacion": 1,
                    "destinoOperacion": 1,
                    "formatoCAFE": 1,
                    "entregaCAFE": 1,
                    "envioContenedor": 1,
                    "procesoGeneracion": 1,
                    "tipoVenta": 1,
                    "fechaEmision": fecha_emision_dt.strftime("%Y-%m-%dT09:00:00-05:00"),
                    "cliente": {
                        "tipoClienteFE": "02",
                        "tipoContribuyente": 1,
                        "numeroRUC": cliente.get('RUC', '').replace("-", ""),
                        "digitoVerificadorRUC": cliente.get('DV', ''),
                        "razonSocial": cliente.get('Nombre', ''),
                        "direccion": cliente.get('Dirección', ''),
                        "telefono1": cliente.get('Teléfono', ''),
                        "correoElectronico1": cliente.get('Correo', ''),
                        "pais": "PA"
                    }
                },
                "listaItems": {
                    "item": [
                        {
                            "codigo": i["codigo"],
                            "descripcion": i["descripcion"],
                            "codigoGTIN": "0",
                            "cantidad": f"{i['cantidad']:.2f}",
                            "precioUnitario": f"{i['precioUnitario']:.2f}",
                            "precioUnitarioDescuento": "0.00",
                            "precioItem": f"{i['cantidad'] * i['precioUnitario']:.2f}",
                            "valorTotal": f"{i['cantidad'] * i['precioUnitario'] + i['valorITBMS']:.2f}",
                            "cantGTINCom": f"{i['cantidad']:.2f}",
                            "codigoGTINInv": "0",
                            "tasaITBMS": "01" if i["valorITBMS"] > 0 else "00",
                            "valorITBMS": f"{i['valorITBMS']:.2f}",
                            "cantGTINComInv": f"{i['cantidad']:.2f}"
                        } for i in items
                    ]
                },
                "totalesSubTotales": {
                    "totalPrecioNeto": f"{total_neto:.2f}",
                    "totalITBMS": f"{total_itbms:.2f}",
                    "totalMontoGravado": f"{total_itbms:.2f}",
                    "totalDescuento": "0.00",
                    "totalAcarreoCobrado": "0.00",
                    "valorSeguroCobrado": "0.00",
                    "totalFactura": f"{total_factura:.2f}",
                    "totalValorRecibido": f"{total_factura:.2f}",
                    "vuelto": "0.00",
                    "tiempoPago": "1",
                    "nroItems": str(len(items)),
                    "totalTodosItems": f"{total_factura:.2f}",
                    "listaFormaPago": {
                        "formaPago": [forma_pago]
                    }
                }
            }
        }
        st.write("JSON enviado:")
        st.json(payload)
        url = "https://ninox-factory-server.onrender.com/enviar-factura"
        try:
            response = requests.post(url, json=payload)
            st.success(f"Respuesta: {response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")








