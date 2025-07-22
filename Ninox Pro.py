import streamlit as st
import requests
from datetime import datetime

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

# ========== CONFIGURACIÓN NINOX ==========
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

def obtener_facturas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

def obtener_lineas_factura():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/LíneasFactura/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

def obtener_clientes():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Clientes/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

# ========== INTERFAZ PRINCIPAL ==========
st.set_page_config(page_title="Factura Electrónica DGI", layout="centered")
st.title("Facturación DGI - Seleccione No. de Factura")

if st.button("Actualizar datos de Ninox"):
    st.session_state.pop("facturas", None)
    st.session_state.pop("lineas", None)
    st.session_state.pop("clientes", None)

if "facturas" not in st.session_state:
    st.session_state["facturas"] = obtener_facturas()
if "lineas" not in st.session_state:
    st.session_state["lineas"] = obtener_lineas_factura()
if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_clientes()

facturas = st.session_state["facturas"]
lineas = st.session_state["lineas"]
clientes = st.session_state["clientes"]

if not facturas:
    st.warning("No hay facturas en Ninox")
    st.stop()

# Listar números de factura
factura_numeros = [f['fields'].get('Factura No.') for f in facturas if 'fields' in f and 'Factura No.' in f['fields']]
factura_seleccionada = st.selectbox("Seleccione Número de Factura", factura_numeros)

factura = next((f for f in facturas if f['fields'].get('Factura No.') == factura_seleccionada), None)
if not factura:
    st.warning("No se encontró la factura seleccionada.")
    st.stop()

fields = factura["fields"]
# Obtén las líneas de factura asociadas
lineas_factura = [l['fields'] for l in lineas if l['fields'].get('Factura No.') == factura_seleccionada]
if not lineas_factura:
    st.warning(f"No hay líneas asociadas a la factura seleccionada ({factura_seleccionada}).")
    st.stop()

# Busca el cliente correspondiente
cliente_nombre = lineas_factura[0].get("Cliente") if lineas_factura[0].get("Cliente") else ""
cliente_info = next((c['fields'] for c in clientes if c['fields'].get('Nombre') == cliente_nombre), {})

# ========== ARMA EL JSON OFICIAL DGI ==========
items = []
total_neto = 0
total_itbms = 0
for l in lineas_factura:
    cantidad = float(l.get("Cantidad", 1))
    precio = float(l.get("Precio Unitario", 0))
    itbms = float(l.get("ITBMS", 0))
    subtotal = cantidad * precio
    items.append({
        "codigo": l.get("Código", "GEN"),
        "descripcion": l.get("Descripción", ""),
        "codigoGTIN": "0",
        "cantidad": f"{cantidad:.2f}",
        "precioUnitario": f"{precio:.2f}",
        "precioUnitarioDescuento": "0.00",
        "precioItem": f"{subtotal:.2f}",
        "valorTotal": f"{subtotal + itbms:.2f}",
        "cantGTINCom": f"{cantidad:.2f}",
        "codigoGTINInv": "0",
        "tasaITBMS": "01" if itbms > 0 else "00",
        "valorITBMS": f"{itbms:.2f}",
        "cantGTINComInv": f"{cantidad:.2f}"
    })
    total_neto += subtotal
    total_itbms += itbms

total_factura = float(fields.get("Total", total_neto + total_itbms))

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
            "fechaEmision": (fields.get("Fecha + Hora", str(datetime.today()))[:10] + "T09:00:00-05:00"),
            "cliente": {
                "tipoClienteFE": "02",
                "tipoContribuyente": 1,
                "numeroRUC": cliente_info.get('RUC', '').replace("-", ""),
                "digitoVerificadorRUC": cliente_info.get('DV', ''),
                "razonSocial": cliente_info.get('Nombre', ''),
                "direccion": cliente_info.get('Dirección', ''),
                "telefono1": cliente_info.get('Teléfono', ''),
                "correoElectronico1": cliente_info.get('Correo', ''),
                "pais": "PA"
            }
        },
        "listaItems": {
            "item": items
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
                "formaPago": [{
                    "formaPagoFact": {"Efectivo": "01", "Debito": "02", "Credito": "03"}.get(fields.get("Medio de Pago", "Efectivo"), "01"),
                    "valorCuotaPagada": f"{total_factura:.2f}"
                }]
            }
        }
    }
}

# ========== MUESTRA Y ENVÍA ==========
st.subheader("Vista previa de los datos extraídos de la factura")
st.write("Cliente:", cliente_info)
st.write("Líneas:", lineas_factura)
st.write("JSON DGI:", payload)

if st.button("Enviar Factura a DGI"):
    st.subheader("JSON enviado a la DGI")
    st.json(payload)
            url = "https://ninox-factory-server.onrender.com/enviar-factura"
            try:
                response = requests.post(url, json=payload)
                st.success(f"Respuesta: {response.text}")
                # Guarda en historial local para tu control
                if "historial" not in st.session_state:
                    st.session_state["historial"] = []
                st.session_state["historial"].append({
                    "Factura No.": factura_no_final,
                    "Cliente": cliente.get("Nombre", ""),
                    "Fecha": str(fecha_emision),
                    "Total Neto": f"{total_neto:.2f}",
                    "Medio de Pago": medio_pago,
                    "Emitido por": st.session_state["emisor"]
                })
                # Refresca facturas
                st.session_state["facturas"] = obtener_facturas_actualizadas()
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ================== HISTORIAL =======================
elif menu == "Ver historial":
    st.title("Historial de facturas enviadas")

    # Cargar historial local de la sesión
    historial = st.session_state.get("historial", [])

    if not historial:
        st.info("No hay facturas enviadas en esta sesión.")
    else:
        df = pd.DataFrame(historial)
        st.dataframe(df, use_container_width=True)

        # Descargar como Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            label="Descargar historial en Excel",
            data=output.getvalue(),
            file_name='historial_facturas.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

