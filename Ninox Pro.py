import streamlit as st
import requests
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
DATABASE_ID = "yoq1qy9euurq"  # AJUSTA AQUÍ SI CAMBIA

def obtener_tabla(tabla):
    url = f"https://api.ninox.com/v1/teams/{TEAM_ID}/databases/{DATABASE_ID}/tables/{tabla}/records"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.ok:
        return r.json()
    return []

st.sidebar.title("Menú")
menu = st.sidebar.radio(
    "Seleccione una opción:",
    ["Historial de Facturas"]
)

if menu == "Historial de Facturas":
    st.title("Historial de Facturas con Detalle de Cliente")

    with st.spinner("Cargando datos desde Ninox..."):
        clientes_raw = obtener_tabla("Clientes")
        facturas_raw = obtener_tabla("Facturas")

    if not facturas_raw or not clientes_raw:
        st.warning("No se encontraron registros en Ninox.")
        st.stop()

    # Diccionario rápido de clientes por Nombre
    clientes_dict = {c["fields"].get("Nombre"): c["fields"] for c in clientes_raw}

    # Construir historial detallado
    historial = []
    for f in facturas_raw:
        fields = f.get("fields", {})
        factura_no = fields.get("Factura No.", "")
        fecha = fields.get("Fecha + Hora", "")
        medio_pago = fields.get("Medio de Pago", "")
        total = fields.get("Total", 0)
        emitido_por = fields.get("Emitido por", "")
        lineas = fields.get("LíneasFactura", [])

        # Si no hay líneas, igual muestra la factura básica
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
                "Descripción": "",
                "Cantidad": "",
                "Precio Unitario": "",
                "ITBMS": ""
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
                    "Descripción": linea.get("Descripción", ""),
                    "Cantidad": linea.get("Cantidad", ""),
                    "Precio Unitario": linea.get("Precio Unitario", ""),
                    "ITBMS": linea.get("ITBMS", "")
                })

    df = pd.DataFrame(historial)
    st.dataframe(df, use_container_width=True)

    # Descargar como Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button(
        label="Descargar historial en Excel",
        data=output.getvalue(),
        file_name='historial_facturas_detallado.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
