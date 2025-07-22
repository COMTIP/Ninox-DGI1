import streamlit as st
import requests
import pandas as pd

# ========= LOGIN ==========
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

st.sidebar.title("Menú")
st.sidebar.write("Solo Facturación")

st.title("Facturación")

# ========== FLUJO PRINCIPAL ==========

# 1. Traer datos Ninox
facturas_raw = obtener_tabla("Facturas")
clientes_raw = obtener_tabla("Clientes")
productos_raw = obtener_tabla("Productos")

if not facturas_raw:
    st.warning("No hay facturas en Ninox.")
    st.stop()
if not clientes_raw:
    st.warning("No hay clientes en Ninox.")
    st.stop()

# Diccionarios para fácil búsqueda
facturas_dict = {f["fields"].get("Factura No.", ""): f for f in facturas_raw if f["fields"].get("Factura No.", "")}
clientes_dict = {c["fields"].get("Nombre", ""): c["fields"] for c in clientes_raw}

factura_numeros = sorted(list(facturas_dict.keys()))

# Selección de Factura
factura_seleccionada = st.selectbox("Seleccione el Número de Factura", factura_numeros)

if factura_seleccionada:
    f = facturas_dict[factura_seleccionada]
    fields = f.get("fields", {})
    lineas = fields.get("LíneasFactura", [])

    st.subheader(f"Detalles de la Factura {factura_seleccionada}")
    st.write(f"**Fecha:** {fields.get('Fecha + Hora', '')}")
    st.write(f"**Medio de Pago:** {fields.get('Medio de Pago', '')}")
    st.write(f"**Emitido por:** {fields.get('Emitido por', '')}")
    st.write(f"**Total:** ${fields.get('Total', 0)}")

    # Cliente (de la primera línea asociada, como en Ninox)
    cliente = ""
    if lineas:
        cliente = lineas[0].get("Cliente", "")
    datos_cliente = clientes_dict.get(cliente, {})
    st.markdown("### Cliente")
    st.write(f"**Nombre:** {cliente}")
    st.write(f"**RUC:** {datos_cliente.get('RUC', '')}")
    st.write(f"**DV:** {datos_cliente.get('DV', '')}")
    st.write(f"**Teléfono:** {datos_cliente.get('Teléfono', '')}")
    st.write(f"**Correo:** {datos_cliente.get('Correo', '')}")

    # Tabla de productos
    total_neto = 0
    total_itbms = 0
    detalle = []
    for l in lineas:
        cantidad = float(l.get("Cantidad", 0))
        precio_unitario = float(l.get("Precio Unitario", 0))
        valor_itbms = float(l.get("ITBMS", 0))
        subtotal = float(l.get("Subtotal Línea", cantidad * precio_unitario))
        detalle.append({
            "Código": l.get("Código", ""),
            "Descripción": l.get("Descripción", ""),
            "Cantidad": cantidad,
            "Precio Unitario": precio_unitario,
            "ITBMS": valor_itbms,
            "Subtotal Línea": subtotal
        })
        total_neto += cantidad * precio_unitario
        total_itbms += valor_itbms

    total_factura = total_neto + total_itbms

    if detalle:
        df = pd.DataFrame(detalle)
        st.markdown("### Detalle de Productos / Servicios")
        st.dataframe(df, use_container_width=True)
        st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_factura:.2f}")
    else:
        st.info("No hay líneas de producto asociadas a esta factura.")

    # -------- ENVÍO A DGI --------
    def construir_payload_DGI():
        medio_pago_ninox = fields.get('Medio de Pago', 'Efectivo')
        forma_pago = {
            "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Crédito": "03"}.get(medio_pago_ninox, "01"),
            "valorCuotaPagada": f"{total_factura:.2f}"
        }
        payload = {
            "documento": {
                "codigoSucursalEmisor": "0000",
                "tipoSucursal": "1",
                "datosTransaccion": {
                    "tipoEmision": "01",
                    "tipoDocumento": "01",
                    "numeroDocumentoFiscal": factura_seleccionada,
                    "puntoFacturacionFiscal": "001",
                    "naturalezaOperacion": "01",
                    "tipoOperacion": 1,
                    "destinoOperacion": 1,
                    "formatoCAFE": 1,
                    "entregaCAFE": 1,
                    "envioContenedor": 1,
                    "procesoGeneracion": 1,
                    "tipoVenta": 1,
                    "fechaEmision": str(fields.get('Fecha + Hora', '')) + "T09:00:00-05:00",
                    "cliente": {
                        "tipoClienteFE": "02",
                        "tipoContribuyente": 1,
                        "numeroRUC": datos_cliente.get('RUC', '').replace("-", ""),
                        "digitoVerificadorRUC": datos_cliente.get('DV', ''),
                        "razonSocial": cliente,
                        "direccion": datos_cliente.get('Dirección', ''),
                        "telefono1": datos_cliente.get('Teléfono', ''),
                        "correoElectronico1": datos_cliente.get('Correo', ''),
                        "pais": "PA"
                    }
                },
                "listaItems": {
                    "item": [
                        {
                            "codigo": l.get("Código", ""),
                            "descripcion": l.get("Descripción", ""),
                            "codigoGTIN": "0",
                            "cantidad": f"{float(l.get('Cantidad', 0)):.2f}",
                            "precioUnitario": f"{float(l.get('Precio Unitario', 0)):.2f}",
                            "precioUnitarioDescuento": "0.00",
                            "precioItem": f"{float(l.get('Cantidad', 0)) * float(l.get('Precio Unitario', 0)):.2f}",
                            "valorTotal": f"{float(l.get('Subtotal Línea', 0)) + float(l.get('ITBMS', 0)):.2f}",
                            "cantGTINCom": f"{float(l.get('Cantidad', 0)):.2f}",
                            "codigoGTINInv": "0",
                            "tasaITBMS": "01" if float(l.get("ITBMS", 0)) > 0 else "00",
                            "valorITBMS": f"{float(l.get('ITBMS', 0)):.2f}",
                            "cantGTINComInv": f"{float(l.get('Cantidad', 0)):.2f}"
                        } for l in lineas
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
                    "nroItems": str(len(lineas)),
                    "totalTodosItems": f"{total_factura:.2f}",
                    "listaFormaPago": {
                        "formaPago": [forma_pago]
                    }
                }
            }
        }
        return payload

    st.markdown("### Enviar esta factura a la DGI")
    if st.button("Enviar Factura a DGI"):
        payload = construir_payload_DGI()
        st.write("JSON enviado:")
        st.json(payload)
        url = "https://ninox-factory-server.onrender.com/enviar-factura"
        try:
            response = requests.post(url, json=payload)
            st.success(f"Respuesta DGI: {response.text}")
        except Exception as e:
            st.error(f"Error al enviar: {str(e)}")

