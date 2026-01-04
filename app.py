import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import date

st.set_page_config(page_title="Parte clinico", layout="wide", page_icon="🧑‍⚕️📊")

# --- LOGIN SUPERUSER ---
SUPERUSER = os.getenv("SUPERUSER", "Hospital20")
SUPERPASS = os.getenv("SUPERPASS", "Hospital2026")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔒 Login Superusuario")
    user = st.text_input("Usuario", key="login_user")
    pwd = st.text_input("Contraseña", type="password", key="login_pwd")
    if st.button("Ingresar"):
        if user == SUPERUSER and pwd == SUPERPASS:
            st.session_state.logged_in = True
            st.success("¡Bienvenido!")
            st.rerun()  # Cambia experimental_rerun() por rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

if not st.session_state.logged_in:
    login()
    st.stop()

# --- LOGO INICIO ---
logo_path = os.path.join(os.path.dirname(__file__), "logo.jpeg")  # Cambia el nombre si tu logo es otro
if os.path.exists(logo_path):
    st.image(logo_path, width=120) 

st.title("🧑‍⚕️📊 Análisis parte")
st.markdown("Análisis de datos clínicos y visualizaciones interactivas.")

# --- CONFIGURACIÓN DE CONEXIÓN ---
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASS = os.getenv("PG_PWD", "jossue205")
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = os.getenv("PG_PORT", "5432")
DB_NAME = os.getenv("PG_DB", "partes_diario")
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    connect_args={"client_encoding": "UTF8"}
)

# --- FUNCIONES DE CONSULTA ---

# --- CONSULTA DESDE LA VISTA ---

@st.cache_data(show_spinner=False)
def get_medicos():
    try:
        query = "SELECT DISTINCT medico FROM vw_parte_diario ORDER BY medico"
        df = pd.read_sql(query, engine)
        # Limpiar caracteres problemáticos manualmente
        # Forzar decodificación desde bytes latin1 a str, reemplazando caracteres inválidos
        def clean_str(val):
            if isinstance(val, bytes):
                try:
                    return val.decode('latin1', errors='replace')
                except Exception:
                    return str(val)
            try:
                return str(val).encode('latin1', errors='replace').decode('latin1', errors='replace')
            except Exception:
                return str(val)
        df['medico'] = df['medico'].apply(clean_str)
        return df['medico'].dropna().tolist()
    except Exception as e:
        st.error(f"Error al obtener médicos: {e}")
        return []


@st.cache_data(show_spinner=False)
def get_data(start_date, end_date, medico=None):
    try:
        query = """
            SELECT * FROM vw_parte_diario
            WHERE fecha_atencion BETWEEN :start AND :end
        """
        params = {"start": start_date, "end": end_date}
        if medico and medico != "Todos":
            query += " AND medico = :med"
            params["med"] = medico
        df = pd.read_sql(text(query), engine, params=params)
        # Limpiar caracteres problemáticos en todas las columnas tipo string
        for col in df.columns:
            df[col] = df[col].apply(lambda x: clean_str(x))
        return df
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()


# --- SIDEBAR FILTROS ---
st.sidebar.title("Filtros")
today = date.today()
start_date = st.sidebar.date_input("Fecha inicio", value=today.replace(day=1))
end_date = st.sidebar.date_input("Fecha fin", value=today)
medicos = ["Todos"] + get_medicos()
medico = st.sidebar.selectbox("Médico", medicos)

# Filtros adicionales (se definen después de obtener el dataframe)
edad_rango = None
genero = None
especialidad = None

df = get_data(start_date, end_date, medico)

# --- BOTÓN RECARGAR DATOS ---
if 'reload' not in st.session_state:
    st.session_state.reload = False

if st.sidebar.button('🔄 Recargar datos'):
    st.cache_data.clear()
    st.session_state.reload = not st.session_state.reload

# --- CONSULTA PRINCIPAL ---
if start_date > end_date:
    st.error("La fecha de inicio no puede ser mayor que la fecha de fin.")
    st.stop()

df = get_data(start_date, end_date, medico)


# Definir opciones de filtros adicionales si hay datos
# (La vista ya entrega datos agregados, solo filtrar por médico y fecha)

# --- UI PRINCIPAL ---
st.title("Dashboard Clínico - Parte Diario")


if df.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    # --- MÉTRICAS PARTE DIARIO ---
    st.subheader("Parte Diario Clínico - Métricas Principales")
    col1, col2, col3 = st.columns(3)
    col1.metric("Número de Atenciones", int(df['total_atenciones'].sum()))
    col2.metric("Valor recaudado por Consultas", f"${df['total_consultas'].sum():,.2f}")
    col3.metric("Valor recaudado por Medicinas", f"${df['total_medicina'].sum():,.2f}")

    # --- Descarga CSV y Excel ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar CSV", csv, "parte_diario.csv", "text/csv")

    import io
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='ParteDiario')
    excel_buffer.seek(0)
    st.download_button(
        label="Descargar Excel",
        data=excel_buffer,
        file_name="parte_diario.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- Modo avanzado (dashboard completo) reservado para futura mejora ---
    # st.markdown(":gear: Modo avanzado próximamente disponible.")

# --- PANEL ACERCA DE ---
with st.expander("ℹ️ Acerca de este sistema"):
        st.markdown("""
        **Automatización del Parte Diario Clínico**
    
        Esta aplicación permite visualizar, analizar y descargar el parte diario médico de manera automática, eliminando procesos manuales y mejorando la toma de decisiones.
    
        - Fuente de datos: Access (legacy) → PostgreSQL
        - Visualización: Streamlit + Plotly
        - ETL y lógica: Python + Pandas

        Desarrollado por tu equipo. Para soporte o sugerencias, contacta a: [tu-xdearly12@gmail.com](mailto:tu-xdearly12@gmail.com)
        """)

# --- FOOTER ---
st.markdown("""
<hr style='margin-top:40px;margin-bottom:10px;border:1px solid #eee;'>
<div style='text-align:center; color:gray; font-size:0.95em;'>
    🏥 Automatización Parte Diario Clínico &nbsp;|&nbsp; Desarrollado por tu equipo &copy; 2025<br>
    <span style='font-size:0.9em;'>¿Prefieres modo oscuro o claro? Cambia el tema en el menú de Streamlit (☰ &rarr; Settings &rarr; Theme).</span>
</div>
""", unsafe_allow_html=True)

