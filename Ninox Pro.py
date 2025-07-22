import streamlit as st
import requests
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

st.sidebar.title("Menú")
st.sidebar.write("Solo Facturación")

st.title("Facturación (Automática por Número de Factura)")

# --- Leer tablas ---
facturas_raw = obtener_tabla("Facturas")
clientes_raw = obtener_tabla("Clientes")
lineasfactura_raw = obtener_tabla("LíneasFactura")

# Crear índices
clientes_dict = {c["fields"]["Nombre"]: c["fields"] for c in clientes_raw if "Nombre" in c["fields"]}
facturas_dict = {f["fields"]["Factura No."]: f["fields"] for f in facturas_raw if "Factura No." in f["fields"]}

factura_numeros = sorted(list(facturas_dict.keys()))

# --- Seleccionar Factura ---
factura_no = st.selectbox("Seleccione Número de Factura", factura_numeros)

if factura_no:
    datos_factura = facturas_dict[factura_no]

    # Buscar líneas de factura asociadas a este número
    lineas = [l["fields"] for l in lineasfactura_raw if l["fields"].get("Factura No.") == factura_no]
    if not lineas:
        st.warning("No hay líneas asociadas a esta factura.")
        st.stop()

    # Tomar el primer cliente (asumimos que todas las líneas son del mismo cliente)
    cliente_nombre = lineas[0].get("Cliente", "")
    cliente = clientes_dict.get(cliente_nombre, {})

    st.markdown("### Datos del Cliente")
    st.write(f"**Nombre:** {cliente.get('Nombre', '')}")
    st.write(f"**RUC:** {cliente.get('RUC', '')}")
    st.write(f"**DV:** {cliente.get('DV', '')}")
    st.write(f"**Dirección:** {cliente.get('Dirección', '')}")
    st.write(f"**Teléfono:** {cliente.get('Teléfono', '')}")
    st.write(f"**Correo:** {cliente.get('Correo', '')}")

    st.markdown("### Detalle de Productos / Servicios")
    detalle = []
    total_neto = 0
    total_itbms = 0
    for l in lineas:
        cantidad = float(l.get("Cantidad", 0))
        precio_unitario = float(l.get("Precio Unitario", 0))
        itbms = float(l.get("ITBMS", 0))
        subtotal = float(l.get("Subtotal Línea", cantidad * precio_unitario))
        detalle.append({
            "Código": l.get("Código", ""),
            "Descripción": l.get("Descripción", ""),
            "Cantidad": cantidad,
            "Precio Unitario": precio_unitario,
            "ITBMS": itbms,
            "Subtotal Línea": subtotal
        })
        total_neto += cantidad * precio_unitario
        total_itbms += itbms
    df = pd.DataFrame(detalle)
    st.dataframe(df, use_container_width=True)

    st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_neto + total_itbms:.2f}")

    st.markdown("### Resumen de la Factura")
    st.write(f"**Medio de Pago:** {datos_factura.get('Medio de Pago', '')}")
    st.write(f"**Total:** ${datos_factura.get('Total', 0)}")
    st.write(f"**Emitido por:** {datos_factura.get('Emitido por', '')}")

    # ------- Construir JSON para DGI -------
    def construir_payload_DGI():
        medio_pago_ninox = datos_factura.get('Medio de Pago', 'Efectivo')
        forma_pago = {
            "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Crédito": "03"}.get(medio_pago_ninox, "01"),
            "valorCuotaPagada": f"{total_neto + total_itbms:.2f}"
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
                    "fechaEmision": str(datos_factura.get('Fecha + Hora', '')) + "T09:00:00-05:00",
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
                            "codigo": i["Código"],
                            "descripcion": i["Descripción"],
                            "codigoGTIN": "0",
                            "cantidad": f"{i['Cantidad']:.2f}",
                            "precioUnitario": f"{i['Precio Unitario']:.2f}",
                            "precioUnitarioDescuento": "0.00",
                            "precioItem": f"{i['Cantidad'] * i['Precio Unitario']:.2f}",
                            "valorTotal": f"{i['Cantidad'] * i['Precio Unitario'] + i['ITBMS']:.2f}",
                            "cantGTINCom": f"{i['Cantidad']:.2f}",
                            "codigoGTINInv": "0",
                            "tasaITBMS": "01" if i["ITBMS"] > 0 else "00",
                            "valorITBMS": f"{i['ITBMS']:.2f}",
                            "cantGTINComInv": f"{i['Cantidad']:.2f}"
                        } for i in detalle
                    ]
                },
                "totalesSubTotales": {
                    "totalPrecioNeto": f"{total_neto:.2f}",
                    "totalITBMS": f"{total_itbms:.2f}",
                    "totalMontoGravado": f"{total_itbms:.2f}",
                    "totalDescuento": "0.00",
                    "totalAcarreoCobrado": "0.00",
                    "valorSeguroCobrado": "0.00",
                    "totalFactura": f"{total_neto + total_itbms:.2f}",
                    "totalValorRecibido": f"{total_neto + total_itbms:.2f}",
                    "vuelto": "0.00",
                    "tiempoPago": "1",
                    "nroItems": str(len(detalle)),
                    "totalTodosItems": f"{total_neto + total_itbms:.2f}",
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
