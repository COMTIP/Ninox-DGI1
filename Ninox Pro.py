import streamlit as st
import requests
from datetime import datetime

# ========== CONFIGURACIÓN ==========
API_TOKEN = "TU_API_TOKEN"
TEAM_ID = "TU_TEAM_ID"
DATABASE_ID = "TU_DATABASE_ID"

# ========== FUNCIONES ==========
def obtener_tabla(tabla):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{tabla}/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def indexar_por_id(lista):
    return {x['id']: x for x in lista}

def normaliza_fact_no(val):
    val = str(val).strip()
    return val.zfill(8) if val.isdigit() else val

# ========== LOGIN ==========
USUARIOS = {"admin": "1234", "Mispanama": "Maxilo2000"}
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("Acceso al Sistema de Facturación")
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

# ========== ACTUALIZAR DATOS ==========
if st.button("Actualizar datos de Ninox"):
    for k in ["clientes", "facturas", "lineas_factura"]:
        st.session_state.pop(k, None)

clientes = st.session_state.setdefault("clientes", obtener_tabla("Clientes"))
facturas = st.session_state.setdefault("facturas", obtener_tabla("Facturas"))
lineas_factura = st.session_state.setdefault("lineas_factura", obtener_tabla("Líneas Factura"))
clientes_idx = indexar_por_id(clientes)

# ========== DEBUG: MOSTRAR VALORES ==========
st.write("Facturas cargadas:", [f["fields"].get("Factura No.", "") for f in facturas])
st.write("Líneas cargadas:", [lf["fields"].get("Factura No.", "") for lf in lineas_factura])

# ========== FILTRAR FACTURAS CON LÍNEAS ==========
fact_no_lineas = {normaliza_fact_no(lf["fields"].get("Factura No.", "")) for lf in lineas_factura}
facturas_con_lineas = [
    f for f in facturas
    if normaliza_fact_no(f["fields"].get("Factura No.", "")) in fact_no_lineas
]

if not facturas_con_lineas:
    st.warning("No hay facturas con líneas asociadas.")
    st.stop()

# ========== SELECCIÓN DE FACTURA ==========
opciones = [
    f'{f["fields"].get("Factura No.", "")} | {f["fields"].get("Fecha + Hora", "")} | {f["fields"].get("Emitido por", "")}'
    for f in facturas_con_lineas
]
seleccion = st.selectbox("Seleccione una factura", opciones)
factura = facturas_con_lineas[opciones.index(seleccion)]
factura_no = normaliza_fact_no(factura["fields"].get("Factura No.", ""))
cliente_id = factura["fields"].get("Clientes")
if isinstance(cliente_id, list):
    cliente_id = cliente_id[0]
cliente = clientes_idx.get(cliente_id, {}).get("fields", {})

# ========== CLIENTE ==========
st.subheader("🧾 Cliente")
col1, col2 = st.columns(2)
with col1:
    st.text_input("Nombre", value=cliente.get("Nombre", ""), disabled=True)
    st.text_input("RUC", value=cliente.get("RUC", ""), disabled=True)
    st.text_input("DV", value=cliente.get("DV", ""), disabled=True)
with col2:
    st.text_input("Teléfono", value=cliente.get("Teléfono", ""), disabled=True)
    st.text_input("Correo", value=cliente.get("Correo", ""), disabled=True)
st.text_area("Dirección", value=cliente.get("Dirección", ""), disabled=True)

# ========== ÍTEMS ==========
items_factura = [
    {
        "codigo": lf["fields"].get("Código", ""),
        "descripcion": lf["fields"].get("Descripción", ""),
        "cantidad": float(lf["fields"].get("Cantidad", 0)),
        "precioUnitario": float(lf["fields"].get("Precio Unitario", 0)),
        "valorITBMS": float(lf["fields"].get("ITBMS", 0))
    }
    for lf in lineas_factura
    if normaliza_fact_no(lf["fields"].get("Factura No.", "")) == factura_no
]

st.subheader("📋 Ítems")
if items_factura:
    st.write(items_factura)
    total_neto = sum(i["cantidad"] * i["precioUnitario"] for i in items_factura)
    total_itbms = sum(i["valorITBMS"] for i in items_factura)
    total = total_neto + total_itbms
    st.success(f"Total Neto: ${total_neto:.2f} | ITBMS: ${total_itbms:.2f} | Total: ${total:.2f}")
else:
    st.warning("No hay ítems.")
    st.stop()

# ========== FORMULARIO DE ENVÍO ==========
medio_pago = st.selectbox("Medio de pago", ["Efectivo", "Débito", "Crédito"])
fecha_emision = st.date_input("Fecha de emisión", value=datetime.today())

if "emisor" not in st.session_state:
    st.session_state["emisor"] = factura["fields"].get("Emitido por", "")
st.session_state["emisor"] = st.text_input("Emitido por", value=st.session_state["emisor"])

# ========== ENVÍO ==========
if st.button("Enviar factura a DGI"):
    if not st.session_state["emisor"].strip():
        st.error("Debe ingresar el nombre del emisor.")
        st.stop()

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
                "totalFactura": f"{total:.2f}",
                "totalValorRecibido": f"{total:.2f}",
                "vuelto": "0.00",
                "tiempoPago": "1",
                "nroItems": str(len(items_factura)),
                "totalTodosItems": f"{total:.2f}",
                "listaFormaPago": {
                    "formaPago": [{
                        "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Crédito": "03"}[medio_pago],
                        "valorCuotaPagada": f"{total:.2f}"
                    }]
                }
            }
        }
    }

    st.write("Payload enviado:")
    st.json(payload)

    try:
        url = "https://ninox-factory-server.onrender.com/enviar-factura"
        response = requests.post(url, json=payload)
        st.success(f"Factura enviada correctamente. Respuesta: {response.text}")
    except Exception as e:
        st.error(f"Error al enviar: {e}")

