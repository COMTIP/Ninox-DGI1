import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from io import BytesIO

# ========== LOGIN OBLIGATORIO ==========
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

# ======= NINOX API CONFIG ==========
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

def get_ninox(table):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{table}/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def buscar_cliente_por_nombre(nombre, clientes):
    for c in clientes:
        if c["fields"].get("Nombre", "") == nombre:
            return c["fields"]
    return {}

# ==================== MENÚ LATERAL ====================
st.sidebar.title("Menú")
menu = st.sidebar.radio(
    "Seleccione una opción:",
    ["Enviar a DGI", "Historial de envíos"]
)

# ================== ENVIAR FACTURA ======================
if menu == "Enviar a DGI":
    st.set_page_config(page_title="Enviar Factura Ninox a DGI", layout="centered")
    st.title("Enviar factura existente a DGI (extraída de Ninox)")

    # Traer datos de Ninox
    facturas = get_ninox("Facturas")
    lineas = get_ninox("Líneas Factura")
    clientes = get_ninox("Clientes")

    # Mostrar selector de factura
    nums_factura = [f["fields"].get("Factura No.", "Sin número") for f in facturas]
    if not nums_factura:
        st.warning("No hay facturas en Ninox.")
        st.stop()
    factura_idx = st.selectbox("Selecciona Factura para enviar a DGI", range(len(nums_factura)), format_func=lambda x: nums_factura[x])
    factura = facturas[factura_idx]["fields"]

    # Mostrar datos principales de la factura seleccionada
    st.write(f"**Factura No.:** {factura.get('Factura No.', '')}")
    st.write(f"**Fecha + Hora:** {factura.get('Fecha + Hora', '')}")
    st.write(f"**Medio de Pago:** {factura.get('Medio de Pago', '')}")
    st.write(f"**Total:** ${factura.get('Total', 0):,.2f}")
    st.write(f"**Emitido por:** {factura.get('Emitido por', '')}")

    # Buscar todas las líneas asociadas
    lineas_factura = [l["fields"] for l in lineas if l["fields"].get("Factura No.", "") == factura["Factura No."]]
    if not lineas_factura:
        st.warning("No hay líneas asociadas a esta factura.")
        st.stop()

    st.write("### Detalle de la factura:")
    df_lineas = pd.DataFrame(lineas_factura)
    st.dataframe(df_lineas, use_container_width=True)

    # Buscar cliente principal (de la primera línea, asumiendo que todas las líneas son del mismo cliente)
    cliente_nombre = lineas_factura[0].get("Cliente", "")
    cliente = buscar_cliente_por_nombre(cliente_nombre, clientes)

    # Validar cliente
    if not cliente:
        st.warning("No se encontró el cliente asociado.")
        st.stop()

    # Generar JSON para DGI
    fecha = factura.get("Fecha + Hora", "")
    try:
        fecha_iso = datetime.strptime(fecha, "%m/%d/%Y %I:%M %p").strftime("%Y-%m-%dT%H:%M:%S-05:00")
    except Exception:
        fecha_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-05:00")

    medio_pago = factura.get("Medio de Pago", "Efectivo")
    forma_pago = {
        "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Crédito": "03"}.get(medio_pago, "01"),
        "valorCuotaPagada": str(factura.get("Total", 0))
    }

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
                        "precioItem": f"{l.get('Cantidad', 1) * l.get('Precio Unitario', 0):.2f}",
                        "valorTotal": f"{l.get('Cantidad', 1) * l.get('Precio Unitario', 0) + l.get('ITBMS', 0):.2f}",
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
                "totalITBMS": f"{sum(l.get('ITBMS', 0) for l in lineas_factura):.2f}",
                "totalMontoGravado": f"{sum(l.get('ITBMS', 0) for l in lineas_factura):.2f}",
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

    st.subheader("JSON generado para la DGI")
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

