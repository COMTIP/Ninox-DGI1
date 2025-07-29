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

# ======= CONFIGURACIÓN NINOX ==========
API_TOKEN = "TU_API_TOKEN_REAL"  # <---- Reemplaza con tu API Token
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"

# IDs de tablas Ninox (UUID)
TABLA_CLIENTES = "d3c82d50-60d4-11f0-9dd2-0154422825e5"  # Clientes
TABLA_PRODUCTOS = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TABLA_FACTURAS = "d3c82d50-60d4-11f0-9dd2-0154422825e5"

def obtener_registros(tabla_id):
    url = f"https://api.ninoxdb.de/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{tabla_id}/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    else:
        st.error(f"Error {r.status_code}: {r.text}")
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

# ==================== MENÚ LATERAL ====================
st.sidebar.title("Menú")
menu = st.sidebar.radio(
    "Seleccione una opción:",
    ["Facturación", "Ver historial"]
)

# ================== FACTURACIÓN ======================
if menu == "Facturación":

    st.title("Factura Electrónica DGI")

    if st.button("Actualizar datos de Ninox"):
        st.session_state.pop("clientes", None)
        st.session_state.pop("productos", None)
        st.session_state.pop("facturas", None)

    # Cachear datos en sesión
    if "clientes" not in st.session_state:
        st.session_state["clientes"] = obtener_registros(TABLA_CLIENTES)
    if "productos" not in st.session_state:
        st.session_state["productos"] = obtener_registros(TABLA_PRODUCTOS)
    if "facturas" not in st.session_state:
        st.session_state["facturas"] = obtener_registros(TABLA_FACTURAS)

    clientes = st.session_state["clientes"]
    productos = st.session_state["productos"]
    facturas = st.session_state["facturas"]

    if not clientes:
        st.warning("No hay clientes en Ninox")
        st.stop()
    if not productos:
        st.warning("No hay productos en Ninox")
        st.stop()

    # Selección de Cliente
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

    # --- Factura No y Fecha ---
    factura_no_preview = calcular_siguiente_factura_no(facturas)
    st.text_input("Factura No.", value=factura_no_preview, disabled=True)
    fecha_emision = st.date_input("Fecha Emisión", value=datetime.today())

    # --- AGREGAR PRODUCTOS (Items) ---
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

    # --- Mostrar Items ---
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

    # ----------- EMISOR OBLIGATORIO ----------
    if "emisor" not in st.session_state:
        st.session_state["emisor"] = ""
    st.session_state["emisor"] = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state["emisor"])

    # --- Enviar a DGI ---
    if st.button("Enviar Factura a DGI"):
        if not st.session_state["emisor"].strip():
            st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
        elif not st.session_state['items']:
            st.error("Debe agregar al menos un producto.")
        else:
            factura_no_final = calcular_siguiente_factura_no(obtener_registros(TABLA_FACTURAS))
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
                        "totalFactura": f"{total_factura:.2f}",
                        "totalValorRecibido": f"{total_factura:.2f}",
                        "vuelto": "0.00",
                        "tiempoPago": "1",
                        "nroItems": str(len(st.session_state['items'])),
                        "totalTodosItems": f"{total_factura:.2f}",
                        "listaFormaPago": {"formaPago": [forma_pago]}
                    }
                }
            }

            st.json(payload)
            url = "https://ninox-factory-server.onrender.com/enviar-factura"
            try:
                response = requests.post(url, json=payload)
                st.success(f"Respuesta DGI: {response.text}")
                # Guarda en historial local
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
