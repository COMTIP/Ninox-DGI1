import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# ========== LOGIN ==========
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

# ========= NINOX API =========
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

st.sidebar.title("Menú")
st.sidebar.write("Solo Facturación")

st.title("Facturación")

# --- Obtener datos de Ninox ---
facturas_raw = obtener_tabla("Facturas")
clientes_raw = obtener_tabla("Clientes")
productos_raw = obtener_tabla("Productos")

if not clientes_raw:
    st.warning("No hay clientes en Ninox.")
    st.stop()
if not productos_raw:
    st.warning("No hay productos en Ninox.")
    st.stop()

facturas_dict = {f["fields"].get("Factura No.", ""): f for f in facturas_raw if f["fields"].get("Factura No.", "")}
facturas_numeros = sorted(list(facturas_dict.keys()))
clientes_dict = {c["fields"].get("Nombre", ""): c["fields"] for c in clientes_raw}

# ============= NUEVO: Selección de Factura Existente =============
st.markdown("#### (Opcional) Seleccione un Número de Factura para autocompletar")
factura_no_existente = st.selectbox("Factura existente", [""] + facturas_numeros, format_func=lambda x: x if x else "Nueva factura")

# Variables a llenar (se llenan desde la factura si se selecciona, sino se llenan normal)
if factura_no_existente and factura_no_existente in facturas_dict:
    # Recuperar datos de la factura seleccionada
    f = facturas_dict[factura_no_existente]
    fields = f.get("fields", {})
    lineas = fields.get("LíneasFactura", [])
    cliente_nombre = lineas[0].get("Cliente", "") if lineas else ""
    cliente_data = clientes_dict.get(cliente_nombre, {})
    productos_factura = [{
        "codigo": l.get("Código", ""),
        "descripcion": l.get("Descripción", ""),
        "cantidad": float(l.get("Cantidad", 0)),
        "precioUnitario": float(l.get("Precio Unitario", 0)),
        "valorITBMS": float(l.get("ITBMS", 0))
    } for l in lineas]
    medio_pago = fields.get("Medio de Pago", "")
    emisor = fields.get("Emitido por", "")
    factura_no = fields.get("Factura No.", "")
    fecha_emision = pd.to_datetime(fields.get("Fecha + Hora", datetime.today()))
else:
    cliente_data = {}
    productos_factura = []
    medio_pago = "Efectivo"
    emisor = ""
    factura_no = calcular_siguiente_factura_no(facturas_raw)
    fecha_emision = datetime.today()

# --- Selección de Cliente (editable) ---
nombres_clientes = [c['fields']['Nombre'] for c in clientes_raw]
cliente_idx = st.selectbox("Seleccione Cliente", range(len(nombres_clientes)), 
    format_func=lambda x: nombres_clientes[x],
    index=nombres_clientes.index(cliente_data.get("Nombre", "")) if cliente_data.get("Nombre", "") in nombres_clientes else 0
)
cliente = clientes_raw[cliente_idx]["fields"]

col1, col2 = st.columns(2)
with col1:
    st.text_input("RUC", value=cliente.get('RUC', ''), disabled=True)
    st.text_input("DV", value=cliente.get('DV', ''), disabled=True)
    st.text_area("Dirección", value=cliente.get('Dirección', ''), disabled=True)
with col2:
    st.text_input("Teléfono", value=cliente.get('Teléfono', ''), disabled=True)
    st.text_input("Correo", value=cliente.get('Correo', ''), disabled=True)

# --- Factura No y Fecha ---
st.text_input("Factura No.", value=factura_no, disabled=True)
fecha_emision = st.date_input("Fecha Emisión", value=fecha_emision)

# --- Agregar Productos ---
if 'items' not in st.session_state or factura_no_existente:
    st.session_state['items'] = productos_factura.copy()

st.markdown("### Agregar Productos a la Factura")
nombres_productos = [f"{p['fields'].get('Código','')} | {p['fields'].get('Descripción','')}" for p in productos_raw]
prod_idx = st.selectbox("Producto", range(len(nombres_productos)), format_func=lambda x: nombres_productos[x])
prod_elegido = productos_raw[prod_idx]['fields']
cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
if st.button("Agregar ítem"):
    st.session_state['items'].append({
        "codigo": prod_elegido.get('Código', ''),
        "descripcion": prod_elegido.get('Descripción', ''),
        "cantidad": cantidad,
        "precioUnitario": float(prod_elegido.get('Precio Unitario', 0)),
        "valorITBMS": float(prod_elegido.get('ITBMS', 0))
    })

if st.session_state['items']:
    st.write("#### Ítems de la factura")
    for idx, i in enumerate(st.session_state['items']):
        st.write(f"{idx+1}. {i['codigo']} | {i['descripcion']} | {i['cantidad']} | {i['precioUnitario']} | {i['valorITBMS']}")
    if st.button("Limpiar Ítems"):
        st.session_state['items'] = []

total_neto = sum(i["cantidad"] * i["precioUnitario"] for i in st.session_state['items'])
total_itbms = sum(i["valorITBMS"] for i in st.session_state['items'])
total_factura = total_neto + total_itbms

st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_factura:.2f}")

medio_pago = st.selectbox("Medio de Pago", ["Efectivo", "Débito", "Crédito"], index=["Efectivo", "Débito", "Crédito"].index(medio_pago) if medio_pago in ["Efectivo", "Débito", "Crédito"] else 0)
emisor = st.text_input("Nombre de quien emite la factura (obligatorio)", value=emisor)

# --- Enviar a DGI ---
def construir_payload_DGI():
    forma_pago = {
        "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Crédito": "03"}.get(medio_pago, "01"),
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
                    } for i in st.session_state['items']
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
                "nroItems": str(len(st.session_state['items'])),
                "totalTodosItems": f"{total_factura:.2f}",
                "listaFormaPago": {
                    "formaPago": [forma_pago]
                }
            }
        }
    }
    return payload

if st.button("Enviar Factura a DGI"):
    if not emisor.strip():
        st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
    elif not st.session_state['items']:
        st.error("Debe agregar al menos un producto.")
    else:
        payload = construir_payload_DGI()
        st.write("JSON enviado:")
        st.json(payload)
        url = "https://ninox-factory-server.onrender.com/enviar-factura"
        try:
            response = requests.post(url, json=payload)
            st.success(f"Respuesta DGI: {response.text}")
        except Exception as e:
            st.error(f"Error al enviar: {str(e)}")

