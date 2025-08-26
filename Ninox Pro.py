import streamlit as st
import requests
from datetime import datetime

# ================== LOGIN ==================
USUARIOS = {"Mispanama": "Maxilo2000", "usuario1": "password123"}
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if not st.session_state["autenticado"]:
    st.markdown("<h2 style='text-align:center; color:#1c6758'>Acceso</h2>", unsafe_allow_html=True)
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

# ================== CONFIG ==================
API_TOKEN = "0b3a1130-785a-11f0-ace0-3fb1fcb242e2"
TEAM_ID = "ihp8o8AaLzfodwc4J"
DATABASE_ID = "u2g01uaua8tu"

BACKEND_URL = st.sidebar.text_input(
    "BACKEND_URL",
    value="https://ninox-factory-server.onrender.com",  # ajusta si usas otro host o subruta
)

# ================== HELPERS NINOX ==================
def _get(url):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        return r.json() if r.ok else []
    except Exception:
        return []

def obtener_clientes():
    return _get(f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Clientes/records")

def obtener_productos():
    return _get(f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Productos/records")

def obtener_facturas():
    return _get(f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/Facturas/records")

def calcular_siguiente_factura_no(facturas):
    max_fact = 0
    for f in facturas:
        try:
            n = int(f.get("fields", {}).get("Factura No.", "") or 0)
            max_fact = max(max_fact, n)
        except:
            pass
    return f"{max_fact + 1:08d}"

# ================== CARGA DE DATOS ==================
if st.button("Actualizar datos de Ninox"):
    for k in ("clientes", "productos", "facturas"):
        st.session_state.pop(k, None)

if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_clientes()
if "productos" not in st.session_state:
    st.session_state["productos"] = obtener_productos()
if "facturas" not in st.session_state:
    st.session_state["facturas"] = obtener_facturas()

clientes = st.session_state["clientes"]
productos = st.session_state["productos"]
facturas  = st.session_state["facturas"]

if not clientes:
    st.warning("No hay clientes en Ninox"); st.stop()
if not productos:
    st.warning("No hay productos en Ninox"); st.stop()

# ================== CLIENTE ==================
st.header("Datos del Cliente")
nombres = [c['fields'].get('Nombre', f"Cliente {i}") for i, c in enumerate(clientes)]
idx = st.selectbox("Seleccione Cliente", range(len(nombres)), format_func=lambda x: nombres[x])
cliente = clientes[idx]["fields"]

c1, c2 = st.columns(2)
with c1:
    st.text_input("RUC", value=cliente.get('RUC',''), disabled=True)
    st.text_input("DV", value=cliente.get('DV',''), disabled=True)
    st.text_area("Dirección", value=cliente.get('Dirección',''), disabled=True)
with c2:
    st.text_input("Teléfono", value=cliente.get('Teléfono',''), disabled=True)
    st.text_input("Correo", value=cliente.get('Correo',''), disabled=True)

# ================== FACTURAS ==================
# (Opcional) filtra pendientes del cliente actual si guardas esa relación en Ninox
pendientes = [
    f for f in facturas
    if f.get("fields", {}).get("Estado","").strip().lower() == "pendiente"
]
if pendientes:
    opciones = [f.get("fields", {}).get("Factura No.","") for f in pendientes]
    idxf = st.selectbox("Seleccione Factura Pendiente", range(len(opciones)), format_func=lambda x: opciones[x])
    factura_no_preview = opciones[idxf]
else:
    factura_no_preview = calcular_siguiente_factura_no(facturas)

st.text_input("Factura No.", value=factura_no_preview, disabled=True)
fecha_emision = st.date_input("Fecha Emisión", value=datetime.today())

# ================== ÍTEMS ==================
st.header("Agregar Productos a la Factura")
if "items" not in st.session_state: st.session_state["items"] = []

nombres_prod = [f"{p['fields'].get('Código','')} | {p['fields'].get('Descripción','')}" for p in productos]
pidx = st.selectbox("Producto", range(len(nombres_prod)), format_func=lambda x: nombres_prod[x])
prod = productos[pidx]["fields"]

cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)

if st.button("Agregar ítem"):
    precio = float(prod.get("Precio Unitario", 0))
    tasa   = float(prod.get("ITBMS", 0))  # 0.07 etc.
    valor_itbms = round(cantidad * precio * tasa, 2)
    st.session_state["items"].append({
        "codigo": prod.get("Código",""),
        "descripcion": prod.get("Descripción",""),
        "cantidad": float(cantidad),
        "precioUnitario": precio,
        "tasaITBMS": tasa,
        "valorITBMS": valor_itbms
    })

if st.session_state["items"]:
    st.write("#### Ítems de la factura")
    for i, it in enumerate(st.session_state["items"], 1):
        st.write(f"{i}. {it['codigo']} | {it['descripcion']} | {it['cantidad']} | {it['precioUnitario']:.2f} | ITBMS {it['valorITBMS']:.2f}")
    if st.button("Limpiar Ítems"):
        st.session_state["items"] = []

total_neto    = round(sum(i["cantidad"]*i["precioUnitario"] for i in st.session_state["items"]), 2)
total_itbms   = round(sum(i["valorITBMS"] for i in st.session_state["items"]), 2)
total_factura = round(total_neto + total_itbms, 2)
st.write(f"**Total Neto:** {total_neto:.2f}   **ITBMS:** {total_itbms:.2f}   **Total a Pagar:** {total_factura:.2f}")

medio_pago = st.selectbox("Medio de Pago", ["Efectivo","Débito","Crédito"])
emisor = st.text_input("Nombre de quien emite la factura (obligatorio)", value=st.session_state.get("emisor",""))

# ================== ENVIAR ==================
def refresh_facturas():
    st.session_state["facturas"] = obtener_facturas()

if st.button("Enviar Factura a DGI"):
    if not emisor.strip():
        st.error("Debe ingresar el nombre de quien emite la factura.")
    elif not st.session_state["items"]:
        st.error("Debe agregar al menos un producto.")
    else:
        forma_pago = {"formaPagoFact": {"Efectivo":"01","Débito":"02","Crédito":"03"}[medio_pago], "valorCuotaPagada": f"{total_factura:.2f}"}
        payload = {
            "documento": {
                "codigoSucursalEmisor": "0000",
                "tipoSucursal": "1",
                "datosTransaccion": {
                    "tipoEmision": "01",
                    "tipoDocumento": "01",
                    "numeroDocumentoFiscal": factura_no_preview,
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
                        "numeroRUC": cliente.get("RUC","").replace("-",""),
                        "digitoVerificadorRUC": cliente.get("DV",""),
                        "razonSocial": cliente.get("Nombre",""),
                        "direccion": cliente.get("Dirección",""),
                        "telefono1": cliente.get("Teléfono",""),
                        "correoElectronico1": cliente.get("Correo",""),
                        "pais": "PA"
                    }
                },
                "listaItems": {
                    "item": [{
                        "codigo": i["codigo"],
                        "descripcion": i["descripcion"],
                        "codigoGTIN": "0",
                        "cantidad": f"{i['cantidad']:.2f}",
                        "precioUnitario": f"{i['precioUnitario']:.2f}",
                        "precioUnitarioDescuento": "0.00",
                        "precioItem": f"{i['cantidad']*i['precioUnitario']:.2f}",
                        "valorTotal": f"{i['cantidad']*i['precioUnitario'] + i['valorITBMS']:.2f}",
                        "cantGTINCom": f"{i['cantidad']:.2f}",
                        "codigoGTINInv": "0",
                        "tasaITBMS": "01" if i["tasaITBMS"] > 0 else "00",
                        "valorITBMS": f"{i['valorITBMS']:.2f}",
                        "cantGTINComInv": f"{i['cantidad']:.2f}"
                    } for i in st.session_state["items"]]
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
                    "nroItems": str(len(st.session_state["items"])),
                    "totalTodosItems": f"{total_factura:.2f}",
                    "listaFormaPago": {"formaPago": [forma_pago]}
                }
            }
        }

        try:
            with st.spinner("Enviando..."):
                resp = requests.post(f"{BACKEND_URL}/enviar-factura", json=payload, timeout=60)
            if resp.ok:
                try:
                    data = resp.json()
                except Exception:
                    st.success(resp.text)
                    data = {}
                if data.get("ok"):
                    st.success("Factura enviada.")
                    st.json(data.get("respuesta", {}))
                    uid = data.get("uuid")
                    if uid:
                        st.session_state["ultima_factura_uuid"] = uid
                        st.info(f"UUID guardado: {uid}")
                    else:
                        st.warning("No se recibió UUID en la respuesta.")
                else:
                    st.error("Respuesta de envío no OK.")
                    st.write(data)
                st.session_state["items"] = []
                st.session_state["ultima_factura_no"] = factura_no_preview
                st.session_state["facturas"] = obtener_facturas()
            else:
                st.error(f"Error HTTP {resp.status_code}")
                st.text(resp.text)
        except Exception as e:
            st.error(f"Error: {e}")

# ================== DESCARGAR PDF ==================
st.markdown("---")
st.header("Descargar PDF de la Factura Electrónica")

uid = st.session_state.get("ultima_factura_uuid","")
if uid:
    st.text_input("UUID de la última factura", value=uid, disabled=True)

factura_para_pdf = st.text_input("Factura No. (fallback si no hay UUID)",
                                 value=st.session_state.get("ultima_factura_no", ""))

if st.button("Descargar PDF (por UUID si hay, si no por número)"):
    try:
        ok_uuid = False
        # 1) Preferido: UUID
        if uid:
            payload_uuid = {"uuid": uid, "documento": {"tipoDocumento": "01"}}
            with st.spinner("Descargando por UUID..."):
                r = requests.post(f"{BACKEND_URL}/descargar-pdf", json=payload_uuid, stream=True, timeout=120)
            if r.ok and r.headers.get("content-type","").startswith("application/pdf"):
                st.download_button("Descargar PDF", r.content, file_name=f"Factura_{uid}.pdf", mime="application/pdf")
                st.success("PDF descargado (UUID).")
                ok_uuid = True
            else:
                st.warning("Fallo por UUID. Probando por número...")
                st.text(r.text)

        # 2) Fallback: número
        if not ok_uuid:
            payload_num = {
                "datosDocumento": {
                    "codigoSucursalEmisor": "0000",
                    "numeroDocumentoFiscal": factura_para_pdf,
                    "puntoFacturacionFiscal": "001",
                    "serialDispositivo": "",
                    "tipoDocumento": "01",
                    "tipoEmision": "01"
                }
            }
            with st.spinner("Descargando por número..."):
                r2 = requests.post(f"{BACKEND_URL}/descargar-pdf", json=payload_num, stream=True, timeout=120)
            if r2.ok and r2.headers.get("content-type","").startswith("application/pdf"):
                st.download_button("Descargar PDF", r2.content, file_name=f"Factura_{factura_para_pdf}.pdf", mime="application/pdf")
                st.success("PDF descargado (número).")
            else:
                st.error("No se pudo descargar el PDF.")
                st.text(r2.text)
    except Exception as e:
        st.error(f"Error de conexión: {e}")









