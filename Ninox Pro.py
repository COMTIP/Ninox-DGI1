import streamlit as st
import requests
from datetime import datetime

# ====== LOGIN OBLIGATORIO =======
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

# ========== NINOX API ===========
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

# ==================== UI ====================
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

if not clientes:
    st.warning("No hay clientes en Ninox")
    st.stop()

# ---------------- SELECCION DE CLIENTE ----------------
nombres_clientes = [c['fields']['Nombre'] for c in clientes]
cliente_idx = st.selectbox("Seleccione Cliente", range(len(nombres_clientes)), format_func=lambda x: nombres_clientes[x])
cliente = clientes[cliente_idx]["fields"]

col1, col2 = st.columns(2)
with col1:
    st.text_input("RUC", value=cliente.get('RUC', ''), disabled=True)
    st.text_input("DV", value=cliente.get('DV', ''), disabled=True)
    st.text_area("Dirección", value=cliente.get('Dirección', ''), disabled=True)
with col2:
    st.text_input("Teléfono", value=cliente.get('Teléfono', ''), disabled=True)
    st.text_input("Correo", value=cliente.get('Correo', ''), disabled=True)

# ------------- FILTRAR FACTURAS PENDIENTES DEL CLIENTE -----------------
# (Relacionando por "Nombre" en Cliente y en Factura, o cambia aquí si usas otro campo)
facturas_pendientes = [
    f for f in facturas
    if f["fields"].get("Estado", "") == "Pendiente"
    and f["fields"].get("Cliente", "") == cliente.get("Nombre", "")
]
if not facturas_pendientes:
    st.info("Este cliente no tiene facturas pendientes.")
    st.stop()

# Seleccionar factura pendiente
factura_labels = [
    f'{f["fields"].get("Factura No.", "")} - {f["fields"].get("Fecha + Hora", "")}'
    for f in facturas_pendientes
]
factura_idx = st.selectbox("Seleccione Factura Pendiente", range(len(facturas_pendientes)), format_func=lambda x: factura_labels[x])
factura = facturas_pendientes[factura_idx]["fields"]
factura_no = factura.get("Factura No.", "")

# -------------- AGREGAR PRODUCTOS DESDE LINEAS FACTURA AUTOMATICAMENTE -----------
# Todas las líneas asociadas a este número de factura
items = [
    {
        "codigo": lf["fields"].get("Código", ""),
        "descripcion": lf["fields"].get("Descripción", ""),
        "cantidad": float(lf["fields"].get("Cantidad", 1)),
        "precioUnitario": float(lf["fields"].get("Precio Unitario", 0)),
        "valorITBMS": float(lf["fields"].get("ITBMS", 0))
    }
    for lf in lineas_factura
    if str(lf["fields"].get("Factura No.", "")) == str(factura_no)
]

if not items:
    st.warning("La factura seleccionada no tiene productos asociados en la tabla de Líneas Factura.")
    st.stop()

st.markdown("### Ítems de la Factura")
for idx, i in enumerate(items):
    st.write(f"{idx+1}. {i['codigo']} | {i['descripcion']} | {i['cantidad']} | {i['precioUnitario']} | {i['valorITBMS']}")

# --- Totales ---
total_neto = sum(i["cantidad"] * i["precioUnitario"] for i in items)
total_itbms = sum(i["valorITBMS"] for i in items)
total_factura = total_neto + total_itbms

st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_factura:.2f}")

# --- Medio de pago ---
medio_pago = st.selectbox("Medio de Pago", ["Efectivo", "Débito", "Crédito"])

# --- Emisor ---
if "emisor" not in st.session_state:
    st.session_state["emisor"] = ""
st.session_state["emisor"] = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state["emisor"])

# --- Enviar a DGI ---
if st.button("Enviar Factura a DGI"):
    if not st.session_state["emisor"].strip():
        st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
    elif not items:
        st.error("La factura no tiene productos asociados.")
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
                    "fechaEmision": str(datetime.today().date()) + "T09:00:00-05:00",
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





