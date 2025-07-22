import streamlit as st
import requests
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

# ======= NINOX API CONFIG ==========
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

def extraer_factura_numeros(facturas):
    return [f['fields'].get('Factura No.') for f in facturas if 'fields' in f and 'Factura No.' in f['fields']]

# ============ UI PRINCIPAL ============
st.title("Factura Electrónica DGI - Seleccione No. de Factura")

if st.button("Actualizar datos de Ninox"):
    st.session_state.pop("clientes", None)
    st.session_state.pop("facturas", None)
    st.session_state.pop("lineasfactura", None)

if "clientes" not in st.session_state:
    st.session_state["clientes"] = obtener_tabla("Clientes")
if "facturas" not in st.session_state:
    st.session_state["facturas"] = obtener_tabla("Facturas")
if "lineasfactura" not in st.session_state:
    st.session_state["lineasfactura"] = obtener_tabla("LineasFactura")  # Asegúrate del nombre exacto en Ninox

clientes = st.session_state["clientes"]
facturas = st.session_state["facturas"]
lineasfactura = st.session_state["lineasfactura"]

# Seleccionar Factura
nums_factura = extraer_factura_numeros(facturas)
if not nums_factura:
    st.warning("No hay facturas de Ninox registradas.")
    st.stop()

factura_seleccionada = st.selectbox("Seleccione Número de Factura", nums_factura)

# Obtener detalles de la factura seleccionada
factura = next((f for f in facturas if f['fields'].get('Factura No.') == factura_seleccionada), None)
if not factura:
    st.warning("No se encontró la factura seleccionada.")
    st.stop()

# Obtener líneas de factura asociadas
lineas = [l for l in lineasfactura if l["fields"].get("Factura No.") == factura_seleccionada]
if not lineas:
    st.warning(f"No hay líneas asociadas a esta factura ({factura_seleccionada}).")
    st.stop()

# Obtener cliente asociado a la primera línea de la factura
cliente_nombre = lineas[0]["fields"].get("Cliente") if lineas else None
cliente = next((c for c in clientes if c["fields"].get("Nombre") == cliente_nombre), None)

# Mostrar datos del cliente
st.header("Datos del Cliente")
if cliente:
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Nombre", value=cliente['fields'].get('Nombre',''), disabled=True)
        st.text_input("RUC", value=cliente['fields'].get('RUC',''), disabled=True)
        st.text_input("DV", value=cliente['fields'].get('DV',''), disabled=True)
    with col2:
        st.text_input("Dirección", value=cliente['fields'].get('Dirección',''), disabled=True)
        st.text_input("Teléfono", value=cliente['fields'].get('Teléfono',''), disabled=True)
        st.text_input("Correo", value=cliente['fields'].get('Correo',''), disabled=True)
else:
    st.warning("Cliente no encontrado para esta factura.")

# Mostrar líneas de factura (productos/servicios)
st.header("Detalle de Productos / Servicios")
df_lineas = pd.DataFrame([
    {
        "Código": l["fields"].get("Código", ""),
        "Descripción": l["fields"].get("Descripción", ""),
        "Cantidad": l["fields"].get("Cantidad", ""),
        "Precio Unitario": l["fields"].get("Precio Unitario", ""),
        "ITBMS": l["fields"].get("ITBMS", ""),
        "Subtotal Línea": l["fields"].get("Subtotal Línea", "")
    } for l in lineas
])
st.dataframe(df_lineas)

# Mostrar totales y otros datos de la factura
st.header("Totales y Datos Adicionales")
total_factura = factura["fields"].get("Total", 0)
medio_pago = factura["fields"].get("Medio de Pago", "")
emitido_por = factura["fields"].get("Emitido por", "")

col3, col4 = st.columns(2)
with col3:
    st.text_input("Medio de Pago", value=medio_pago, disabled=True)
    st.text_input("Emitido por", value=emitido_por, disabled=True)
with col4:
    st.text_input("Total", value=str(total_factura), disabled=True)

# Botón para enviar a la DGI (payload ejemplo)
if st.button("Enviar Factura a DGI"):
    payload = {
        "factura": factura_seleccionada,
        "cliente": cliente['fields'] if cliente else {},
        "lineas": df_lineas.to_dict(orient="records"),
        "total": total_factura,
        "medio_pago": medio_pago,
        "emitido_por": emitido_por
    }
    st.write("Se enviaría el siguiente payload (ejemplo):")
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

