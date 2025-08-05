import streamlit as st
import requests
from datetime import datetime
import pandas as pd

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

# ========== NINOX API CONFIG ==========
API_TOKEN = "d3c82d50-60d4-11f0-9dd2-0154422825e5"
TEAM_ID = "6dA5DFvfDTxCQxpDF"
DATABASE_ID = "yoq1qy9euurq"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def obtener_tabla(tabla):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{tabla}/records"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.ok else []

def dict_id_fields(lista):
    return {item["id"]: item["fields"] for item in lista}

# ========== MENU LATERAL ==========
st.sidebar.title("Menú")
tipo_documento = st.sidebar.radio(
    "Seleccione documento a enviar:",
    ["Factura", "Nota de Crédito"]
)

FACTORY_URL = "https://ninox-factory-server.onrender.com/enviar-factura"

# ========== FACTURACIÓN ==========
if tipo_documento == "Factura":
    st.title("📄 Enviar Factura a la DGI")

    facturas_lista = obtener_tabla("Facturas")
    lineas_lista = obtener_tabla("Lineas Factura")
    clientes = dict_id_fields(obtener_tabla("Clientes"))

    if not facturas_lista:
        st.warning("No hay facturas registradas.")
        st.stop()

    df_facturas = pd.DataFrame([f["fields"] | {"_id": f["id"]} for f in facturas_lista])
    st.dataframe(df_facturas[["Factura No.", "Fecha + Hora", "Total", "Estado Pendiente"]], use_container_width=True)

    facturas_ids = df_facturas["_id"].tolist()
    seleccion_id = st.selectbox("Seleccione Factura", facturas_ids, format_func=lambda x: df_facturas[df_facturas["_id"]==x]["Factura No."].values[0])
    datos_factura = dict_id_fields(facturas_lista)[seleccion_id]
    lineas = [l for l in lineas_lista if l["fields"].get("Factura") == seleccion_id]

    # Procesa líneas (productos)
    df_lineas = pd.DataFrame([l["fields"] for l in lineas])
    if not df_lineas.empty:
        st.dataframe(df_lineas[["Descripción", "Cantidad", "Precio Unitario", "ITBMS"]], use_container_width=True)
    else:
        st.info("No hay líneas asociadas a esta factura.")

    # Datos de totales
    total_neto = df_lineas["Cantidad"].astype(float).mul(df_lineas["Precio Unitario"].astype(float)).sum() if not df_lineas.empty else 0
    total_itbms = df_lineas["ITBMS"].astype(float).sum() if not df_lineas.empty else 0
    total_factura = total_neto + total_itbms

    # Prepara JSON
    cliente_id = datos_factura.get("Clientes", [""])[0] if datos_factura.get("Clientes") else ""
    cliente = clientes.get(cliente_id, {})

    forma_pago = {
        "formaPagoFact": "01",
        "valorCuotaPagada": f"{total_factura:.2f}"
    }

    payload = {
        "documento": {
            "codigoSucursalEmisor": "0000",
            "tipoSucursal": "1",
            "datosTransaccion": {
                "tipoEmision": "01",
                "tipoDocumento": "01",  # Factura
                "numeroDocumentoFiscal": datos_factura.get("Factura No.", ""),
                "puntoFacturacionFiscal": "001",
                "naturalezaOperacion": "01",
                "tipoOperacion": 1,
                "destinoOperacion": 1,
                "formatoCAFE": 1,
                "entregaCAFE": 1,
                "envioContenedor": 1,
                "procesoGeneracion": 1,
                "tipoVenta": 1,
                "fechaEmision": str(datos_factura.get("Fecha + Hora", ""))[:10] + "T09:00:00-05:00",
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
                        "cantidad": f"{float(l.get('Cantidad', 0)):.2f}",
                        "precioUnitario": f"{float(l.get('Precio Unitario', 0)):.2f}",
                        "precioUnitarioDescuento": "0.00",
                        "precioItem": f"{float(l.get('Cantidad', 0))*float(l.get('Precio Unitario', 0)):.2f}",
                        "valorTotal": f"{float(l.get('Cantidad', 0))*float(l.get('Precio Unitario', 0)) + float(l.get('ITBMS', 0)):.2f}",
                        "cantGTINCom": f"{float(l.get('Cantidad', 0)):.2f}",
                        "codigoGTINInv": "0",
                        "tasaITBMS": "01" if float(l.get('ITBMS', 0)) > 0 else "00",
                        "valorITBMS": f"{float(l.get('ITBMS', 0)):.2f}",
                        "cantGTINComInv": f"{float(l.get('Cantidad', 0)):.2f}"
                    } for l in lineas
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
                "nroItems": str(len(lineas)),
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
    if st.button("Enviar Factura a DGI"):
        response = requests.post(FACTORY_URL, json=payload)
        if response.ok:
            st.success("Factura enviada correctamente ✅")
            st.json(response.json())
        else:
            st.error("Error al enviar")
            st.text(response.text)

# ========== NOTA DE CRÉDITO ==========
elif tipo_documento == "Nota de Crédito":
    st.title("💳 Enviar Nota de Crédito a la DGI")

    notas_lista = obtener_tabla("Nota de Credito")
    clientes = dict_id_fields(obtener_tabla("Clientes"))
    facturas = dict_id_fields(obtener_tabla("Facturas"))
    lineas_lista = obtener_tabla("Lineas Factura")  # Si tienes línea de la nota de crédito

    if not notas_lista:
        st.warning("No hay notas de crédito registradas.")
        st.stop()

    df_notas = pd.DataFrame([n["fields"] | {"_id": n["id"]} for n in notas_lista])
    st.dataframe(df_notas[["Credit No", "Fecha", "Monto", "Estado"]], use_container_width=True)

    notas_ids = df_notas["_id"].tolist()
    seleccion_id = st.selectbox("Seleccione Nota de Crédito", notas_ids, format_func=lambda x: df_notas[df_notas["_id"]==x]["Credit No"].values[0])
    datos_nota = dict_id_fields(notas_lista)[seleccion_id]

    cliente_id = datos_nota.get("Clientes", [""])[0] if datos_nota.get("Clientes") else ""
    factura_id = datos_nota.get("Facturas", [""])[0] if datos_nota.get("Facturas") else ""
    cliente = clientes.get(cliente_id, {})
    factura_relacionada = facturas.get(factura_id, {})

    # Busca líneas relacionadas a la factura (puedes adaptar para tener líneas de la nota)
    lineas = [l for l in lineas_lista if l["fields"].get("Factura") == factura_id]

    # Prepara líneas negativas para la nota de crédito (así se suele hacer)
    df_lineas = pd.DataFrame([l["fields"] for l in lineas])
    items_nota = [
        {
            "codigo": l.get("Código", ""),
            "descripcion": l.get("Descripción", ""),
            "codigoGTIN": "0",
            "cantidad": f"-{float(l.get('Cantidad', 0)):.2f}",  # Negativo para nota crédito
            "precioUnitario": f"{float(l.get('Precio Unitario', 0)):.2f}",
            "precioUnitarioDescuento": "0.00",
            "precioItem": f"-{float(l.get('Cantidad', 0))*float(l.get('Precio Unitario', 0)):.2f}",
            "valorTotal": f"-{float(l.get('Cantidad', 0))*float(l.get('Precio Unitario', 0)) + float(l.get('ITBMS', 0)):.2f}",
            "cantGTINCom": f"-{float(l.get('Cantidad', 0)):.2f}",
            "codigoGTINInv": "0",
            "tasaITBMS": "01" if float(l.get('ITBMS', 0)) > 0 else "00",
            "valorITBMS": f"-{float(l.get('ITBMS', 0)):.2f}",
            "cantGTINComInv": f"-{float(l.get('Cantidad', 0)):.2f}"
        } for l in lineas
    ]

    total_neto = sum(-float(l["Cantidad"])*float(l["Precio Unitario"]) for l in df_lineas.to_dict("records")) if not df_lineas.empty else 0
    total_itbms = -df_lineas["ITBMS"].astype(float).sum() if not df_lineas.empty else 0
    total_factura = total_neto + total_itbms

    payload = {
        "documento": {
            "codigoSucursalEmisor": "0000",
            "tipoSucursal": "1",
            "datosTransaccion": {
                "tipoEmision": "01",
                "tipoDocumento": "03",  # Nota de crédito
                "numeroDocumentoFiscal": datos_nota.get("Credit No", ""),
                "numeroDocumentoReferencia": factura_relacionada.get("Factura No.", ""),
                "puntoFacturacionFiscal": "001",
                "naturalezaOperacion": "01",
                "tipoOperacion": 1,
                "destinoOperacion": 1,
                "formatoCAFE": 1,
                "entregaCAFE": 1,
                "envioContenedor": 1,
                "procesoGeneracion": 1,
                "tipoVenta": 1,
                "fechaEmision": str(datos_nota.get("Fecha", ""))[:10] + "T09:00:00-05:00",
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
                "item": items_nota
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
                "nroItems": str(len(items_nota)),
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
    if st.button("Enviar Nota de Crédito a DGI"):
        response = requests.post(FACTORY_URL, json=payload)
        if response.ok:
            st.success("Nota de crédito enviada correctamente ✅")
            st.json(response.json())
        else:
            st.error("Error al enviar")
            st.text(response.text)
