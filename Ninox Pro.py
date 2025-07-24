import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# ======= CONFIGURACIÓN NINOX =======
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

def obtener_tabla(tabla):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{tabla}/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

def indexar_por_id(lista):
    return {x['id']: x for x in lista}

def calcular_siguiente_factura_no(facturas):
    max_factura = 0
    for f in facturas:
        valor = f["fields"].get("Factura No.", "")
        try:
            n = int(valor)
            if n > max_factura:
                max_factura = n
        except Exception:
            continue
    return f"{max_factura + 1:08d}"

def factura_no_ya_existe(facturas, factura_no):
    for f in facturas:
        if str(f["fields"].get("Factura No.", "")).zfill(8) == factura_no.zfill(8):
            return True
    return False

# ======= LOGIN =======
USUARIOS = {"Mispanama": "Maxilo2000", "usuario1": "password123"}
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

# ======= DATOS NINOX =======
if st.button("Actualizar datos de Ninox"):
    st.session_state.pop("clientes", None)
    st.session_state.pop("facturas", None)
    st.session_state.pop("lineas_factura", None)

if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_tabla("Clientes")
if "facturas" not in st.session_state:
    st.session_state["facturas"] = obtener_tabla("Facturas")
if "lineas_factura" not in st.session_state:
    st.session_state["lineas_factura"] = obtener_tabla("Líneas Factura")

clientes = st.session_state["clientes"]
facturas = st.session_state["facturas"]
lineas_factura = st.session_state["lineas_factura"]

clientes_idx = indexar_por_id(clientes)

# ======= SELECCIÓN DE FACTURA =======
if not clientes or not facturas or not lineas_factura:
    st.warning("Debe haber clientes, facturas y líneas de factura en la base de datos Ninox.")
    st.stop()

facturas_con_lineas = [f for f in facturas if any(lf["fields"].get("Facturas") == f["id"] for lf in lineas_factura)]
nombres_facturas = [
    f'{f["fields"].get("Factura No.", "")} | {f["fields"].get("Fecha + Hora", "")} | {f["fields"].get("Emitido por", "")}'
    for f in facturas_con_lineas
]
factura_idx = st.selectbox(
    "Seleccione Factura",
    range(len(nombres_facturas)),
    format_func=lambda x: nombres_facturas[x],
)
factura = facturas_con_lineas[factura_idx]
factura_fields = factura["fields"]
factura_id = factura["id"]

# Cliente asociado
cliente_id = factura_fields.get("Clientes")
if isinstance(cliente_id, list):
    cliente_id = cliente_id[0] if cliente_id else None
cliente = clientes_idx.get(cliente_id)["fields"] if cliente_id and clientes_idx.get(cliente_id) else {}

# ======= DATOS DE CLIENTE =======
col1, col2 = st.columns(2)
with col1:
    st.text_input("RUC", value=cliente.get('RUC', ''), disabled=True)
    st.text_input("DV", value=cliente.get('DV', ''), disabled=True)
    st.text_area("Dirección", value=cliente.get('Dirección', ''), disabled=True)
with col2:
    st.text_input("Teléfono", value=cliente.get('Teléfono', ''), disabled=True)
    st.text_input("Correo", value=cliente.get('Correo', ''), disabled=True)

# ======= FACTURA NO. EDITABLE =======
factura_no_usuario = st.text_input("Factura No. (puede editarlo, 8 dígitos)", value=factura_fields.get("Factura No.", ""))
if not factura_no_usuario:
    factura_no_usuario = calcular_siguiente_factura_no(facturas)

# ======= FECHA =======
fecha_emision = st.date_input("Fecha Emisión", value=datetime.today())

# ======= ÍTEMS DESDE LÍNEAS FACTURA =======
items_factura = [
    {
        "codigo": lf["fields"].get('Código', ''),
        "descripcion": lf["fields"].get('Descripción', ''),
        "cantidad": float(lf["fields"].get('Cantidad', 0)),
        "precioUnitario": float(lf["fields"].get('Precio Unitario', 0)),
        "valorITBMS": float(lf["fields"].get('ITBMS', 0))
    }
    for lf in lineas_factura
    if lf["fields"].get("Facturas") == factura_id
]

# ======= MOSTRAR ÍTEMS =======
if items_factura:
    st.write("#### Ítems de la factura")
    for idx, i in enumerate(items_factura):
        st.write(f"{idx+1}. {i['codigo']} | {i['descripcion']} | {i['cantidad']} | {i['precioUnitario']} | {i['valorITBMS']}")
else:
    st.warning("No hay ítems para esta factura.")
    st.stop()

total_neto = sum(i["cantidad"] * i["precioUnitario"] for i in items_factura)
total_itbms = sum(i["valorITBMS"] for i in items_factura)
total_factura = total_neto + total_itbms

st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_factura:.2f}")

medio_pago = st.selectbox(
    "Medio de Pago",
    ["Efectivo", "Débito", "Crédito"],
    index={"Efectivo": 0, "Débito": 1, "Crédito": 2}.get(factura_fields.get("Medio de Pago", "Efectivo"), 0)
)

if "emisor" not in st.session_state:
    st.session_state["emisor"] = factura_fields.get("Emitido por", "")
st.session_state["emisor"] = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state["emisor"])

# ======= ENVIAR A DGI =======
def obtener_facturas_actualizadas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

if st.button("Enviar Factura a DGI"):
    if not st.session_state["emisor"].strip():
        st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
    elif not items_factura:
        st.error("Esta factura no tiene productos.")
    elif factura_no_ya_existe(facturas, factura_no_usuario):
        st.error(f"El número de factura {factura_no_usuario} ya existe. Por favor, elija otro.")
    else:
        facturas_actualizadas = obtener_facturas_actualizadas()
        if factura_no_ya_existe(facturas_actualizadas, factura_no_usuario):
            st.error(f"El número de factura {factura_no_usuario} ya existe. Por favor, elija otro.")
            st.stop()
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
                    "numeroDocumentoFiscal": factura_no_usuario,
                    "puntoFacturacionFiscal": "001",
                    "naturalezaOperacion": "01",
                    "tipoOperacion": 1,
                    "destinoOperacion": 1,
                    "formatoCAFE": 1,
                    "entregaCAFE": 1,
                    "envioContenedor": 1,
                    "procesoGeneracion": 1,
                    "tipoVenta": 1,
                    "fechaEmision": str(fecha_emision) + "T09:00:00-05:00",
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
                        } for i in items_factura
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
                    "nroItems": str(len(items_factura)),
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
            # Actualiza historial en sesión (opcional)
            if "historial" not in st.session_state:
                st.session_state["historial"] = []
            st.session_state["historial"].append({
                "Factura No.": factura_no_usuario,
                "Cliente": cliente.get("Nombre", ""),
                "Fecha": str(fecha_emision),
                "Total Neto": f"{total_neto:.2f}",
                "Medio de Pago": medio_pago,
                "Emitido por": st.session_state["emisor"]
            })
            st.session_state["facturas"] = obtener_tabla("Facturas")
        except Exception as e:
            st.error(f"Error: {str(e)}")

