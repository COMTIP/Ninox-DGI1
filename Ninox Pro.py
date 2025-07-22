import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from io import BytesIO

# Configuración Ninox API
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

def get_ninox(table):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{table}/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def buscar_cliente_por_nombre(nombre, clientes):
    nombre = nombre.strip().lower()
    for c in clientes:
        if c["fields"].get("Nombre", "").strip().lower() == nombre:
            return c["fields"]
    return {}

# --------- APP ---------
st.set_page_config(page_title="Factura desde Ninox", layout="centered")
st.title("Factura electrónica DGI (todo desde Ninox)")

# Traer datos de Ninox
facturas = get_ninox("Facturas")
lineas = get_ninox("Líneas Factura")
clientes = get_ninox("Clientes")

# Selector de factura
nums_factura = [f["fields"].get("Factura No.", "Sin número") for f in facturas]
if not nums_factura:
    st.warning("No hay facturas en Ninox.")
    st.stop()
factura_idx = st.selectbox("Selecciona Factura", range(len(nums_factura)), format_func=lambda x: nums_factura[x])
factura = facturas[factura_idx]["fields"]

# Extraer líneas asociadas
lineas_factura = [l["fields"] for l in lineas if l["fields"].get("Factura No.", "") == factura["Factura No."]]
if not lineas_factura:
    st.warning("No hay líneas asociadas a esta factura.")
    st.stop()

# Buscar cliente por nombre (en la PRIMERA línea)
cliente_nombre = lineas_factura[0].get("Cliente", "")
cliente = buscar_cliente_por_nombre(cliente_nombre, clientes)

st.header("Datos de la factura")
st.write(f"**Factura No.:** {factura.get('Factura No.','')}")
st.write(f"**Fecha + Hora:** {factura.get('Fecha + Hora','')}")
st.write(f"**Medio de Pago:** {factura.get('Medio de Pago','')}")
st.write(f"**Total:** ${factura.get('Total', 0):,.2f}")
st.write(f"**Emitido por:** {factura.get('Emitido por','')}")

st.subheader("Datos del cliente principal")
if not cliente:
    st.error("No se encontró el cliente en la tabla Clientes.")
else:
    st.write(f"**Nombre:** {cliente.get('Nombre','')}")
    st.write(f"**RUC:** {cliente.get('RUC','')}")
    st.write(f"**DV:** {cliente.get('DV','')}")
    st.write(f"**Dirección:** {cliente.get('Dirección','')}")
    st.write(f"**Teléfono:** {cliente.get('Teléfono','')}")
    st.write(f"**Correo:** {cliente.get('Correo','')}")

st.subheader("Detalle (líneas de factura)")
if lineas_factura:
    df = pd.DataFrame([
        {
            "Descripción": l.get("Descripción", ""),
            "Cantidad": l.get("Cantidad", ""),
            "Precio Unitario": l.get("Precio Unitario", ""),
            "ITBMS": l.get("ITBMS", ""),
            "Subtotal Línea": l.get("Subtotal Línea", ""),
        }
        for l in lineas_factura
    ])
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Sin líneas de factura.")

# Mostrar el JSON para la DGI
if cliente:
    medio_pago = factura.get("Medio de Pago", "Efectivo")
    forma_pago = {
        "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Crédito": "03"}.get(medio_pago, "01"),
        "valorCuotaPagada": str(factura.get("Total", 0))
    }
    fecha = factura.get("Fecha + Hora", "")
    try:
        fecha_iso = datetime.strptime(fecha, "%m/%d/%Y %I:%M %p").strftime("%Y-%m-%dT%H:%M:%S-05:00")
    except Exception:
        fecha_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-05:00")
    payload = {
        "documento": {
            "codigoSucursalEmisor": "0000",
            "tipoSucursal": "1",
            "datosTransaccion": {
                "tipoEmision": "01",
                "tipoDocumento": "01",
                "numeroDocumentoFiscal": factura.get("Factura No.", ""),
                "puntoFacturacionFiscal": "001",
                "naturalezaOperacion": "01",
                "tipoOperacion": 1,
                "destinoOperacion": 1,
                "formatoCAFE": 1,
                "entregaCAFE": 1,
                "envioContenedor": 1,
                "procesoGeneracion": 1,
                "tipoVenta": 1,
                "fechaEmision": fecha_iso,
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
                        "codigo": l.get("Código", ""),
                        "descripcion": l.get("Descripción", ""),
                        "codigoGTIN": "0",
                        "cantidad": f"{l.get('Cantidad', 1):.2f}",
                        "precioUnitario": f"{l.get('Precio Unitario', 0):.2f}",
                        "precioUnitarioDescuento": "0.00",
                        "precioItem": f"{float(l.get('Cantidad', 1)) * float(l.get('Precio Unitario', 0)):.2f}",
                        "valorTotal": f"{float(l.get('Cantidad', 1)) * float(l.get('Precio Unitario', 0)) + float(l.get('ITBMS', 0)):.2f}",
                        "cantGTINCom": f"{l.get('Cantidad', 1):.2f}",
                        "codigoGTINInv": "0",
                        "tasaITBMS": "01" if l.get("ITBMS", 0) > 0 else "00",
                        "valorITBMS": f"{l.get('ITBMS', 0):.2f}",
                        "cantGTINComInv": f"{l.get('Cantidad', 1):.2f}"
                    } for l in lineas_factura
                ]
            },
            "totalesSubTotales": {
                "totalPrecioNeto": f"{factura.get('Total', 0):.2f}",
                "totalITBMS": f"{sum(float(l.get('ITBMS', 0)) for l in lineas_factura):.2f}",
                "totalMontoGravado": f"{sum(float(l.get('ITBMS', 0)) for l in lineas_factura):.2f}",
                "totalDescuento": "0.00",
                "totalAcarreoCobrado": "0.00",
                "valorSeguroCobrado": "0.00",
                "totalFactura": f"{factura.get('Total', 0):.2f}",
                "totalValorRecibido": f"{factura.get('Total', 0):.2f}",
                "vuelto": "0.00",
                "tiempoPago": "1",
                "nroItems": str(len(lineas_factura)),
                "totalTodosItems": f"{factura.get('Total', 0):.2f}",
                "listaFormaPago": {
                    "formaPago": [forma_pago]
                }
            }
        }
    }
    st.subheader("JSON para DGI")
    st.json(payload)


    # ========== ENVÍO A DGI ==========
    if st.button("Enviar a DGI"):
        url = "https://ninox-factory-server.onrender.com/enviar-factura"
        try:
            response = requests.post(url, json=payload)
            st.success(f"Respuesta DGI: {response.text}")
            # Guardar en historial
            if "historial" not in st.session_state:
                st.session_state["historial"] = []
            st.session_state["historial"].append({
                "Factura No.": factura.get("Factura No.", ""),
                "Cliente": cliente.get("Nombre", ""),
                "Fecha": fecha_iso,
                "Total": factura.get("Total", 0),
                "Respuesta DGI": response.text
            })
        except Exception as e:
            st.error(f"Error enviando a DGI: {str(e)}")

# ================== HISTORIAL =======================
elif menu == "Historial de envíos":
    st.title("Historial de facturas enviadas a la DGI")
    historial = st.session_state.get("historial", [])
    if not historial:
        st.info("No hay envíos en esta sesión.")
    else:
        df = pd.DataFrame(historial)
        st.dataframe(df, use_container_width=True)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            label="Descargar historial en Excel",
            data=output.getvalue(),
            file_name='historial_envios.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

