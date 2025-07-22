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

def obtener_clientes():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Clientes/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

def obtener_facturas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

def obtener_lineas_factura():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/LineasFactura/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

# ==================== MENÚ LATERAL ====================
st.sidebar.title("Menú")
menu = st.sidebar.radio(
    "Seleccione una opción:",
    ["Facturación", "Ver historial"]
)

# ================== FACTURACIÓN ======================
if menu == "Facturación":

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

    if not facturas or not lineas_factura or not clientes:
        st.warning("No hay datos en Ninox")
        st.stop()

    # --- Seleccionar Factura No. ---
    factura_nos = [f['fields']['Factura No.'] for f in facturas if 'Factura No.' in f['fields']]
    factura_no_seleccionada = st.selectbox("Seleccione Número de Factura", factura_nos)

    # --- Filtrar la factura seleccionada ---
    factura = next((f for f in facturas if f['fields'].get('Factura No.') == factura_no_seleccionada), None)
    if not factura:
        st.warning(f"No se encontró la factura {factura_no_seleccionada}")
        st.stop()

    # --- Obtener líneas de factura ---
    lineas = [l['fields'] for l in lineas_factura if l['fields'].get('Factura No.') == factura_no_seleccionada]

    if not lineas:
        st.warning(f"No hay líneas asociadas a la factura seleccionada ({factura_no_seleccionada}).")
        st.stop()

    # --- Obtener cliente ---
    nombre_cliente = lineas[0].get('Cliente', '') if 'Cliente' in lineas[0] else ''
    cliente_ninox = next((c['fields'] for c in clientes if c['fields'].get('Nombre', '') == nombre_cliente), None)
    if not cliente_ninox:
        st.warning(f"No se encontró el cliente '{nombre_cliente}' en Ninox.")
        st.stop()

    # Mostrar datos del cliente
    st.subheader("Datos del Cliente")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Nombre", value=cliente_ninox.get('Nombre', ''), disabled=True)
        st.text_input("RUC", value=cliente_ninox.get('RUC', ''), disabled=True)
        st.text_input("DV", value=cliente_ninox.get('DV', ''), disabled=True)
    with col2:
        st.text_input("Dirección", value=cliente_ninox.get('Dirección', ''), disabled=True)
        st.text_input("Teléfono", value=cliente_ninox.get('Teléfono', ''), disabled=True)
        st.text_input("Correo", value=cliente_ninox.get('Correo', ''), disabled=True)

    # Mostrar líneas de factura (productos)
    st.subheader("Líneas de la Factura")
    df_lineas = pd.DataFrame(lineas)
    st.dataframe(df_lineas[["Código", "Descripción", "Cantidad", "Precio Unitario", "ITBMS", "Subtotal Línea"]])

    # Totales y datos de factura
    medio_pago = factura['fields'].get("Medio de Pago", "")
    total_factura = factura['fields'].get("Total", 0)
    emitido_por = factura['fields'].get("Emitido por", "")

    st.write(f"**Medio de Pago:** {medio_pago}")
    st.write(f"**Total de la Factura:** {total_factura}")
    st.write(f"**Emitido por:** {emitido_por}")

    # Construir payload para la DGI
    total_neto = df_lineas["Subtotal Línea"].astype(float).sum()
    total_itbms = df_lineas["ITBMS"].astype(float).sum()

    items_dgi = [
        {
            "codigo": row["Código"],
            "descripcion": row["Descripción"],
            "codigoGTIN": "0",
            "cantidad": f"{row['Cantidad']:.2f}",
            "precioUnitario": f"{float(row['Precio Unitario']):.2f}",
            "precioUnitarioDescuento": "0.00",
            "precioItem": f"{float(row['Subtotal Línea']):.2f}",
            "valorTotal": f"{float(row['Subtotal Línea']) + float(row['ITBMS']):.2f}",
            "cantGTINCom": f"{row['Cantidad']:.2f}",
            "codigoGTINInv": "0",
            "tasaITBMS": "01" if float(row["ITBMS"]) > 0 else "00",
            "valorITBMS": f"{float(row['ITBMS']):.2f}",
            "cantGTINComInv": f"{row['Cantidad']:.2f}"
        }
        for _, row in df_lineas.iterrows()
    ]

    payload = {
        "documento": {
            "codigoSucursalEmisor": "0000",
            "tipoSucursal": "1",
            "datosTransaccion": {
                "tipoEmision": "01",
                "tipoDocumento": "01",
                "numeroDocumentoFiscal": factura_no_seleccionada,
                "puntoFacturacionFiscal": "001",
                "naturalezaOperacion": "01",
                "tipoOperacion": 1,
                "destinoOperacion": 1,
                "formatoCAFE": 1,
                "entregaCAFE": 1,
                "envioContenedor": 1,
                "procesoGeneracion": 1,
                "tipoVenta": 1,
                "fechaEmision": factura['fields'].get("Fecha + Hora", str(datetime.today()))[:10] + "T09:00:00-05:00",
                "cliente": {
                    "tipoClienteFE": "02",
                    "tipoContribuyente": 1,
                    "numeroRUC": cliente_ninox.get('RUC', '').replace("-", ""),
                    "digitoVerificadorRUC": cliente_ninox.get('DV', ''),
                    "razonSocial": cliente_ninox.get('Nombre', ''),
                    "direccion": cliente_ninox.get('Dirección', ''),
                    "telefono1": cliente_ninox.get('Teléfono', ''),
                    "correoElectronico1": cliente_ninox.get('Correo', ''),
                    "pais": "PA"
                }
            },
            "listaItems": {
                "item": items_dgi
            },
            "totalesSubTotales": {
                "totalPrecioNeto": f"{total_neto:.2f}",
                "totalITBMS": f"{total_itbms:.2f}",
                "totalMontoGravado": f"{total_itbms:.2f}",
                "totalDescuento": "0.00",
                "totalAcarreoCobrado": "0.00",
                "valorSeguroCobrado": "0.00",
                "totalFactura": f"{float(total_factura):.2f}",
                "totalValorRecibido": f"{float(total_factura):.2f}",
                "vuelto": "0.00",
                "tiempoPago": "1",
                "nroItems": str(len(items_dgi)),
                "totalTodosItems": f"{float(total_factura):.2f}",
                "listaFormaPago": {
                    "formaPago": [{
                        "formaPagoFact": {"Efectivo": "01", "Débito": "02", "Credito": "03"}.get(medio_pago, "01"),
                        "valorCuotaPagada": f"{float(total_factura):.2f}"
                    }]
                }
            }
        }
    }

    st.subheader("JSON para enviar a la DGI")
    st.json(payload)

    if st.button("Enviar Factura a DGI"):
        url = "https://ninox-factory-server.onrender.com/enviar-factura"
        try:
            response = requests.post(url, json=payload)
            st.success(f"Respuesta: {response.text}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ================== HISTORIAL =======================
elif menu == "Ver historial":
    st.title("Historial de facturas enviadas")

    historial = st.session_state.get("historial", [])

    if not historial:
        st.info("No hay facturas enviadas en esta sesión.")
    else:
        df = pd.DataFrame(historial)
        st.dataframe(df, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            label="Descargar historial en Excel",
            data=output.getvalue(),
            file_name='historial_facturas.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

