import streamlit as st
import requests
from datetime import datetime

# ========== LOGIN ==========
USUARIOS = {
    "Mispanama": "Maxilo2000",
    "usuario1": "password123"
}
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if not st.session_state["autenticado"]:
    st.markdown("<h2 style='text-align:center; color:#1c6758'>Acceso</h2>", unsafe_allow_html=True)
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

# ========== NINOX API CONFIG ==========
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

def _get(url):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers, timeout=30)
    return r.json() if r.ok else []

def obtener_clientes():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Clientes/records"
    return _get(url)

def obtener_productos():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Productos/records"
    return _get(url)

def obtener_facturas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    return _get(url)

def calcular_siguiente_factura_no(facturas):
    max_factura = 0
    for f in facturas:
        valor = f.get("fields", {}).get("Factura No.", "")
        try:
            n = int(valor)
            max_factura = max(max_factura, n)
        except Exception:
            continue
    return f"{max_factura + 1:08d}"

# ========== CARGA DE DATOS ==========
if st.button("Actualizar datos de Ninox"):
    for k in ("clientes", "productos", "facturas"):
        st.session_state.pop(k, None)

if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_clientes()
if "productos" not in st.session_state:
    st.session_state["productos"] = obtener_productos()
if "facturas" not in st.session_state:
    st.session_state["facturas"] = obtener_facturas()

clientes = st.session_state["clientes"]
productos = st.session_state["productos"]
facturas = st.session_state["facturas"]

if not clientes:
    st.warning("No hay clientes en Ninox")
    st.stop()
if not productos:
    st.warning("No hay productos en Ninox")
    st.stop()

# ========== SELECCIÓN DE CLIENTE ==========
st.header("Datos del Cliente")
nombres_clientes = [c['fields'].get('Nombre', f"Cliente {i}") for i, c in enumerate(clientes)]
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

# ========== FACTURAS ==========
facturas_pendientes = [
    f for f in facturas
    if f.get("fields", {}).get("Estado", "").strip().lower() == "pendiente"
]
if facturas_pendientes:
    opciones_facturas = [f.get('fields', {}).get("Factura No.", "") for f in facturas_pendientes]
    idx_factura = st.selectbox("Seleccione Factura Pendiente", range(len(opciones_facturas)), format_func=lambda x: opciones_facturas[x])
    factura_no_preview = opciones_facturas[idx_factura]
else:
    factura_no_preview = calcular_siguiente_factura_no(facturas)

st.text_input("Factura No.", value=factura_no_preview, disabled=True)
fecha_emision = st.date_input("Fecha Emisión", value=datetime.today())

# ========== AGREGAR PRODUCTOS ==========
st.header("Agregar Productos a la Factura")
if 'items' not in st.session_state:
    st.session_state['items'] = []

nombres_productos = [f"{p['fields'].get('Código','')} | {p['fields'].get('Descripción','')}" for p in productos]
prod_idx = st.selectbox("Producto", range(len(nombres_productos)), format_func=lambda x: nombres_productos[x])
prod_elegido = productos[prod_idx]['fields']

cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)

if st.button("Agregar ítem"):
    # Si tu campo 'ITBMS' es tasa (0.07), el valor ITBMS por ítem = cantidad * precio * tasa
    tasa_itbms = float(prod_elegido.get('ITBMS', 0))
    precio_u = float(prod_elegido.get('Precio Unitario', 0))
    valor_itbms = round(cantidad * precio_u * tasa_itbms, 2)

    st.session_state['items'].append({
        "codigo": prod_elegido.get('Código', ''),
        "descripcion": prod_elegido.get('Descripción', ''),
        "cantidad": float(cantidad),
        "precioUnitario": precio_u,
        "tasaITBMS": tasa_itbms,
        "valorITBMS": valor_itbms
    })

if st.session_state['items']:
    st.write("#### Ítems de la factura")
    for idx, i in enumerate(st.session_state['items']):
        st.write(f"{idx+1}. {i['codigo']} | {i['descripcion']} | {i['cantidad']} | {i['precioUnitario']:.2f} | ITBMS {i['valorITBMS']:.2f}")
    if st.button("Limpiar Ítems"):
        st.session_state['items'] = []

total_neto = sum(i["cantidad"] * i["precioUnitario"] for i in st.session_state['items'])
total_itbms = sum(i["valorITBMS"] for i in st.session_state['items'])
total_factura = total_neto + total_itbms

st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_factura:.2f}")

medio_pago = st.selectbox("Medio de Pago", ["Efectivo", "Débito", "Crédito"])
emisor = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state.get("emisor", ""))

# ========== ENVIAR FACTURA ==========
def obtener_facturas_actualizadas():
    return obtener_facturas()

BACKEND_URL = "https://ninox-factory-server.onrender.com"

if st.button("Enviar Factura a DGI"):
    if not emisor.strip():
        st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
    elif not st.session_state['items']:
        st.error("Debe agregar al menos un producto.")
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
                    "numeroDocumentoFiscal": factura_no_preview,
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
                            "tasaITBMS": "01" if i["tasaITBMS"] > 0 else "00",
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

        url = BACKEND_URL + "/enviar-factura"
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.ok:
                # Mostrar respuesta y guardar UUID si viene
                try:
                    data = response.json()
                except Exception:
                    st.success(f"Respuesta: {response.text}")
                    data = {}

                if data.get("ok"):
                    st.success("Factura enviada correctamente.")
                    st.json(data.get("respuesta", {}))
                    uid = data.get("uuid")
                    if uid:
                        st.session_state["ultima_factura_uuid"] = uid
                        st.info(f"UUID guardado: {uid}")
                    else:
                        st.warning("No se recibió UUID en la respuesta.")
                else:
                    st.write(data)

                st.session_state['items'] = []
                st.session_state["facturas"] = obtener_facturas_actualizadas()
                st.session_state["ultima_factura_no"] = factura_no_preview  # fallback por número
            else:
                st.error("Error al enviar la factura.")
                try:
                    st.write(response.json())
                except Exception:
                    st.write(response.text)
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ========== DESCARGAR PDF ==========
st.markdown("---")
st.header("Descargar PDF de la Factura Electrónica")

# Muestra el UUID si lo tenemos
ultima_uuid = st.session_state.get("ultima_factura_uuid", "")
if ultima_uuid:
    st.text_input("UUID de la última factura", value=ultima_uuid, disabled=True)

# Fallback por número
factura_para_pdf = st.text_input("Factura No. (fallback si no hay UUID)", value=st.session_state.get("ultima_factura_no", factura_no_preview))

# Opción preferida: descargar por UUID si existe
if st.button("Descargar PDF (por UUID si hay, si no por número)"):
    try:
        if st.session_state.get("ultima_factura_uuid"):
            # Descarga por UUID (preferido)
            payload_pdf_uuid = {
                "uuid": st.session_state["ultima_factura_uuid"],
                "documento": {"tipoDocumento": "01"}
            }
            url = BACKEND_URL + "/descargar-pdf"
            with requests.post(url, json=payload_pdf_uuid, stream=True, timeout=120) as response:
                if response.ok and response.headers.get("content-type", "").startswith("application/pdf"):
                    pdf_bytes = response.content
                    pdf_name = f"Factura_{st.session_state['ultima_factura_uuid']}.pdf"
                    st.download_button(
                        label="Descargar PDF",
                        data=pdf_bytes,
                        file_name=pdf_name,
                        mime="application/pdf"
                    )
                    st.success("PDF descargado correctamente (por UUID).")
                else:
                    st.warning("No se pudo descargar por UUID. Probando por número...")
                    raise Exception("Fallo por UUID, intenta por número")
        # Si no hay UUID o falló, intentar por número
        payload_pdf_numero = {
            "datosDocumento": {
                "codigoSucursalEmisor": "0000",
                "numeroDocumentoFiscal": factura_para_pdf,
                "puntoFacturacionFiscal": "001",
                "serialDispositivo": "",
                "tipoDocumento": "01",
                "tipoEmision": "01"
            }
        }
        url = BACKEND_URL + "/descargar-pdf"
        with requests.post(url, json=payload_pdf_numero, stream=True, timeout=120) as response:
            if response.ok and response.headers.get("content-type", "").startswith("application/pdf"):
                pdf_bytes = response.content
                pdf_name = f"Factura_{factura_para_pdf}.pdf"
                st.download_button(
                    label="Descargar PDF",
                    data=pdf_bytes,
                    file_name=pdf_name,
                    mime="application/pdf"
                )
                st.success("PDF descargado correctamente (por número).")
            else:
                st.error("No se pudo descargar el PDF.")
                try:
                    st.write(response.json())
                except Exception:
                    st.write(response.text)
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")










