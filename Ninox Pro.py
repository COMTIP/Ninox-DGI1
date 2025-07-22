import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from io import BytesIO

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
menu = st.sidebar.radio(
    "Seleccione una opción:",
    ["Facturación", "Ver historial", "Consultar factura por número"]
)

# ========== FACTURACIÓN ==========
if menu == "Facturación":
    st.set_page_config(page_title="Factura Electrónica Ninox + DGI", layout="centered")
    st.title("Factura Electrónica")
    if st.button("Actualizar datos de Ninox"):
        st.session_state.pop("clientes", None)
        st.session_state.pop("productos", None)
        st.session_state.pop("facturas", None)
    if "clientes" not in st.session_state:
        st.session_state["clientes"] = obtener_tabla("Clientes")
    if "productos" not in st.session_state:
        st.session_state["productos"] = obtener_tabla("Productos")
    if "facturas" not in st.session_state:
        st.session_state["facturas"] = obtener_tabla("Facturas")
    clientes = st.session_state["clientes"]
    productos = st.session_state["productos"]
    facturas = st.session_state["facturas"]
    if not clientes:
        st.warning("No hay clientes en Ninox")
        st.stop()
    if not productos:
        st.warning("No hay productos en Ninox")
        st.stop()
    nombres_clientes = [c['fields']['Nombre'] for c in clientes]
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
    factura_no_preview = calcular_siguiente_factura_no(facturas)
    st.text_input("Factura No.", value=factura_no_preview, disabled=True)
    fecha_emision = st.date_input("Fecha Emisión", value=datetime.today())
    if 'items' not in st.session_state:
        st.session_state['items'] = []
    st.markdown("### Agregar Productos a la Factura")
    nombres_productos = [f"{p['fields'].get('Código','')} | {p['fields'].get('Descripción','')}" for p in productos]
    prod_idx = st.selectbox("Producto", range(len(nombres_productos)), format_func=lambda x: nombres_productos[x])
    prod_elegido = productos[prod_idx]['fields']
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
    medio_pago = st.selectbox("Medio de Pago", ["Efectivo", "Débito", "Crédito"])
    if "emisor" not in st.session_state:
        st.session_state["emisor"] = ""
    st.session_state["emisor"] = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state["emisor"])
    def obtener_facturas_actualizadas():
        return obtener_tabla("Facturas")
    def crear_factura_ninox(
        factura_no, fecha, medio_pago, total, emitido_por, lineas_items
    ):
        url_facturas = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
        headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
        factura_payload = {
            "fields": {
                "Factura No.": factura_no,
                "Fecha + Hora": fecha,
                "Medio de Pago": medio_pago,
                "Total": total,
                "Emitido por": emitido_por
            }
        }
        response_factura = requests.post(url_facturas, headers=headers, json=factura_payload)
        if not response_factura.ok:
            return False, f"Error al guardar la factura en Ninox: {response_factura.text}"
        factura_id = response_factura.json().get("id")
        url_lineas = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/LíneasFactura/records"
        for item in lineas_items:
            linea_payload = {
                "fields": {
                    "Factura": factura_id,
                    "Factura No.": factura_no,
                    "Cliente": cliente.get("Nombre", ""),
                    "Código": item.get("codigo", ""),
                    "Descripción": item.get("descripcion", ""),
                    "Cantidad": item.get("cantidad", 1),
                    "Precio Unitario": item.get("precioUnitario", 0),
                    "ITBMS": item.get("valorITBMS", 0),
                    "Subtotal Línea": float(item.get("cantidad", 1)) * float(item.get("precioUnitario", 0))
                }
            }
            response_linea = requests.post(url_lineas, headers=headers, json=linea_payload)
            if not response_linea.ok:
                return False, f"Error en la línea: {response_linea.text}"
        return True, "Factura registrada correctamente en Ninox."
    if st.button("Enviar Factura a DGI"):
        if not st.session_state["emisor"].strip():
            st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
        elif not st.session_state['items']:
            st.error("Debe agregar al menos un producto.")
        else:
            facturas_actualizadas = obtener_facturas_actualizadas()
            factura_no_final = calcular_siguiente_factura_no(facturas_actualizadas)
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
                        "numeroDocumentoFiscal": factura_no_final,
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
            st.write("JSON enviado:")
            st.json(payload)
            url = "https://ninox-factory-server.onrender.com/enviar-factura"
            try:
                response = requests.post(url, json=payload)
                st.success(f"Respuesta DGI: {response.text}")
                exito, mensaje = crear_factura_ninox(
                    factura_no_final,
                    str(fecha_emision),
                    medio_pago,
                    total_factura,
                    st.session_state["emisor"],
                    [
                        {
                            "codigo": i["codigo"],
                            "descripcion": i["descripcion"],
                            "cantidad": i["cantidad"],
                            "precioUnitario": i["precioUnitario"],
                            "valorITBMS": i["valorITBMS"]
                        } for i in st.session_state['items']
                    ]
                )
                if exito:
                    st.success("Factura guardada en Ninox correctamente.")
                    st.session_state["facturas"] = obtener_facturas_actualizadas()
                    st.session_state['items'] = []
                else:
                    st.error(mensaje)
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ========== HISTORIAL ==========
elif menu == "Ver historial":
    st.title("Historial de Facturas - Datos reales desde Ninox")
    with st.spinner("Cargando datos desde Ninox..."):
        clientes_raw = obtener_tabla("Clientes")
        facturas_raw = obtener_tabla("Facturas")
    if not facturas_raw or not clientes_raw:
        st.warning("No se encontraron registros en Ninox.")
        st.stop()
    clientes_dict = {c["fields"].get("Nombre"): c["fields"] for c in clientes_raw}
    historial = []
    for f in facturas_raw:
        fields = f.get("fields", {})
        factura_no = fields.get("Factura No.", "")
        fecha = fields.get("Fecha + Hora", "")
        medio_pago = fields.get("Medio de Pago", "")
        total = fields.get("Total", 0)
        emitido_por = fields.get("Emitido por", "")
        lineas = fields.get("LíneasFactura", [])
        if not lineas:
            historial.append({
                "Factura No.": factura_no,
                "Fecha": fecha,
                "Medio de Pago": medio_pago,
                "Total": total,
                "Emitido por": emitido_por,
                "Cliente": "",
                "RUC": "",
                "DV": "",
                "Teléfono": "",
                "Correo": "",
                "Código": "",
                "Descripción": "",
                "Cantidad": "",
                "Precio Unitario": "",
                "ITBMS": "",
                "Subtotal Línea": ""
            })
        else:
            for linea in lineas:
                cliente_nombre = linea.get("Cliente", "")
                cliente = clientes_dict.get(cliente_nombre, {})
                historial.append({
                    "Factura No.": factura_no,
                    "Fecha": fecha,
                    "Medio de Pago": medio_pago,
                    "Total": total,
                    "Emitido por": emitido_por,
                    "Cliente": cliente_nombre,
                    "RUC": cliente.get("RUC", ""),
                    "DV": cliente.get("DV", ""),
                    "Teléfono": cliente.get("Teléfono", ""),
                    "Correo": cliente.get("Correo", ""),
                    "Código": linea.get("Código", ""),
                    "Descripción": linea.get("Descripción", ""),
                    "Cantidad": linea.get("Cantidad", ""),
                    "Precio Unitario": linea.get("Precio Unitario", ""),
                    "ITBMS": linea.get("ITBMS", ""),
                    "Subtotal Línea": linea.get("Subtotal Línea", "")
                })
    df = pd.DataFrame(historial)
    st.dataframe(df, use_container_width=True)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button(
        label="Descargar historial en Excel",
        data=output.getvalue(),
        file_name='historial_facturas_detallado.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ========== CONSULTA POR NÚMERO ==========
elif menu == "Consultar factura por número":
    st.title("Consultar Factura por Número")
    facturas_raw = obtener_tabla("Facturas")
    if not facturas_raw:
        st.warning("No se encontraron facturas en Ninox.")
        st.stop()
    facturas_dict = {f["fields"].get("Factura No.", ""): f for f in facturas_raw if f["fields"].get("Factura No.", "")}
    facturas_numeros = sorted(list(facturas_dict.keys()))
    factura_seleccionada = st.selectbox("Seleccione el Número de Factura", facturas_numeros)
    if factura_seleccionada:
        f = facturas_dict[factura_seleccionada]
        fields = f.get("fields", {})
        st.subheader(f"Detalles de la Factura {factura_seleccionada}")
        st.write(f"**Fecha:** {fields.get('Fecha + Hora', '')}")
        st.write(f"**Medio de Pago:** {fields.get('Medio de Pago', '')}")
        st.write(f"**Emitido por:** {fields.get('Emitido por', '')}")
        st.write(f"**Total:** ${fields.get('Total', 0)}")
        lineas = fields.get("LíneasFactura", [])
        cliente = ""
        if lineas:
            cliente = lineas[0].get("Cliente", "")
        clientes_raw = obtener_tabla("Clientes")
        clientes_dict = {c["fields"].get("Nombre"): c["fields"] for c in clientes_raw}
        datos_cliente = clientes_dict.get(cliente, {})
        st.markdown("### Cliente")
        st.write(f"**Nombre:** {cliente}")
        st.write(f"**RUC:** {datos_cliente.get('RUC', '')}")
        st.write(f"**DV:** {datos_cliente.get('DV', '')}")
        st.write(f"**Teléfono:** {datos_cliente.get('Teléfono', '')}")
        st.write(f"**Correo:** {datos_cliente.get('Correo', '')}")
        if lineas:
            detalle = []
            for l in lineas:
                detalle.append({
                    "Código": l.get("Código", ""),
                    "Descripción": l.get("Descripción", ""),
                    "Cantidad": l.get("Cantidad", ""),
                    "Precio Unitario": l.get("Precio Unitario", ""),
                    "ITBMS": l.get("ITBMS", ""),
                    "Subtotal Línea": l.get("Subtotal Línea", "")
                })
            df = pd.DataFrame(detalle)
            st.markdown("### Detalle de Productos / Servicios")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay líneas de producto asociadas a esta factura.")

