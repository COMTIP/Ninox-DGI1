import streamlit as st
import requests
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
DATABASE_ID = "pc94o7zf3g3u"

def obtener_clientes():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Clientes/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def obtener_productos():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Productos/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def obtener_facturas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

def calcular_siguiente_factura_no(facturas):
    max_factura = 0
    for f in facturas:
        valor = f["fields"].get("Factura No.", "")
        try:
            n = int(valor)
            max_factura = max(max_factura, n)
        except:
            continue
    return f"{max_factura + 1:08d}"

# ================== FACTURACIÓN ======================
st.set_page_config(page_title="Factura Electrónica Ninox + DGI", layout="centered")
st.title("Factura Electrónica")

if st.button("Actualizar datos de Ninox"):
    st.session_state.pop("clientes", None)
    st.session_state.pop("productos", None)
    st.session_state.pop("facturas", None)

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

# --- AGREGAR PRODUCTOS ---
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

# --- Emisor ---
if "emisor" not in st.session_state:
    st.session_state["emisor"] = ""
st.session_state["emisor"] = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state["emisor"])

# --- Enviar a DGI ---
def obtener_facturas_actualizadas():
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.ok else []

if st.button("Enviar Factura a DGI"):
    if not st.session_state["emisor"].strip():
        st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
    elif not st.session_state['items']:
        st.error("Debe agregar al menos un producto.")
    else:
        facturas_actualizadas = obtener_facturas_actualizadas()
        factura_no_final = calcular_siguiente_factura_no(facturas_actualizadas)

        # JSON para DGI
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
            st.success(f"Respuesta: {response.text}")

            # ==== GENERAR PDF DE CAFE ====
            pdf_buffer = BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=letter)
            c.setTitle(f"CAFE_Factura_{factura_no_final}")

            c.setFont("Helvetica-Bold", 16)
            c.drawString(180, 760, "COMPROBANTE AUXILIAR - FACTURA ELECTRÓNICA")
            c.setFont("Helvetica", 10)
            c.drawString(50, 730, f"Factura No.: {factura_no_final}")
            c.drawString(50, 715, f"Fecha: {fecha_emision.strftime('%d/%m/%Y')}")
            c.drawString(50, 700, f"Cliente: {cliente.get('Nombre', '')}")
            c.drawString(50, 685, f"RUC: {cliente.get('RUC','')} - DV: {cliente.get('DV','')}")
            c.drawString(50, 670, f"Dirección: {cliente.get('Dirección','')}")

            # Tabla de productos
            y = 640
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "Código")
            c.drawString(150, y, "Descripción")
            c.drawString(350, y, "Cant.")
            c.drawString(400, y, "Precio")
            c.drawString(460, y, "Total")
            c.setFont("Helvetica", 10)
            y -= 20

            for item in st.session_state['items']:
                total_item = item['cantidad'] * item['precioUnitario']
                c.drawString(50, y, str(item['codigo']))
                c.drawString(150, y, str(item['descripcion'])[:25])
                c.drawRightString(380, y, f"{item['cantidad']:.2f}")
                c.drawRightString(440, y, f"{item['precioUnitario']:.2f}")
                c.drawRightString(510, y, f"{total_item:.2f}")
                y -= 15

            # Totales
            y -= 20
            c.setFont("Helvetica-Bold", 10)
            c.drawRightString(510, y, f"Total Neto: {total_neto:.2f}")
            y -= 15
            c.drawRightString(510, y, f"ITBMS: {total_itbms:.2f}")
            y -= 15
            c.drawRightString(510, y, f"Total: {total_factura:.2f}")

            c.showPage()
            c.save()
            pdf_buffer.seek(0)

            # Botón de descarga del PDF
            st.download_button(
                label="📄 Descargar Comprobante Auxiliar (PDF)",
                data=pdf_buffer,
                file_name=f"CAFE_Factura_{factura_no_final}.pdf",
                mime="application/pdf"
            )

            # Limpiar items para nueva factura
            st.session_state['items'] = []
            st.session_state["facturas"] = obtener_facturas_actualizadas()

        except Exception as e:
            st.error(f"Error: {str(e)}")


