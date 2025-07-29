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

    if "emisor" not in st.session_state:
        st.session_state["emisor"] = ""
    st.session_state["emisor"] = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state["emisor"])

    # --- Enviar a DGI y descargar PDF ---
    if st.button("Enviar Factura a DGI"):
        if not st.session_state["emisor"].strip():
            st.error("Debe ingresar el nombre de quien emite la factura antes de enviarla.")
        elif not st.session_state['items']:
            st.error("Debe agregar al menos un producto.")
        else:
            factura_no_final = calcular_siguiente_factura_no(obtener_facturas())
            payload = {
                "numeroDocumentoFiscal": factura_no_final,
                "cliente": cliente,
                "items": st.session_state['items'],
                "totalFactura": total_factura,
                "fechaEmision": str(fecha_emision),
                "medioPago": medio_pago
            }

            try:
                # 1. Enviar factura
                url_envio = "https://ninox-factory-server.onrender.com/enviar-factura"
                response = requests.post(url_envio, json=payload)
                st.success(f"Factura enviada. Respuesta: {response.text}")

                # 2. Descargar PDF
                url_pdf = "https://ninox-factory-server.onrender.com/descargar-pdf"
                pdf_response = requests.post(url_pdf, json={"numeroDocumentoFiscal": factura_no_final})
                if pdf_response.ok:
                    st.download_button(
                        "Descargar PDF",
                        pdf_response.content,
                        file_name=f"Factura_{factura_no_final}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("No se pudo descargar el PDF.")

            except Exception as e:
                st.error(f"Error: {str(e)}")
