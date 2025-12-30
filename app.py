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
DB_NAME = os.getenv("PG_DB", "parte_diario")
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# --- FUNCIONES DE CONSULTA ---
@st.cache_data(show_spinner=False)
def get_medicos():
    try:
        query = "SELECT DISTINCT medico FROM atencion ORDER BY medico"
        df = pd.read_sql(query, engine)
        return df['medico'].dropna().tolist()
    except Exception as e:
        st.error(f"Error al obtener médicos: {e}")
        return []

@st.cache_data(show_spinner=False)
def get_data(start_date, end_date, medico=None):
    try:
        query = """
            SELECT fecha_atencion, especialidad, medico, valor_consulta, valor_medicina
            FROM atencion
            WHERE fecha_atencion BETWEEN :start AND :end
        """
        params = {"start": start_date, "end": end_date}
        if medico and medico != "Todos":
            query += " AND medico = :med"
            params["med"] = medico
        df = pd.read_sql(text(query), engine, params=params)
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

# --- CONSULTA PRINCIPAL ---
if start_date > end_date:
    st.error("La fecha de inicio no puede ser mayor que la fecha de fin.")
    st.stop()

df = get_data(start_date, end_date, medico)

# --- UI PRINCIPAL ---
st.title("Dashboard Clínico - Parte Diario")

if df.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    # Renombrar columnas para consistencia
    df = df.rename(columns={
        'fecha_atencion': 'fecha',
        'valor_consulta': 'valor_consulta',
        'valor_medicina': 'valor_medicina',
        'medico': 'medico_id'
    })

    # Asegura tipos correctos para columnas numéricas
    for col in ['valor_consulta', 'valor_medicina']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- NUEVO: Calcular rango de edad ---
    def clasificar_edad(edad):
        if pd.isnull(edad):
            return "Sin dato"
        edad = int(edad)
        if 10 <= edad <= 14:
            return "10a14"
        elif 15 <= edad <= 19:
            return "15a19"
        elif 20 <= edad <= 49:
            return "20a49"
        elif 50 <= edad <= 64:
            return "50a64"
        elif edad >= 65:
            return "Mayor 65"
        else:
            return "Sin dato"
    if 'edad' in df.columns:
        df['rango_edad'] = df['edad'].apply(clasificar_edad)
    else:
        df['rango_edad'] = "Sin dato"

    # --- APLICAR FILTROS ---
    if not df.empty:
        # Filtro por institución
        if 'institucion' in df.columns and institucion != "Todas":
            df = df[df['institucion'] == institucion]

        # Filtro por género
        if 'genero' in df.columns and genero != "Todos":
            df = df[df['genero'] == genero]

        # Filtro por médico
        if 'medico_id' in df.columns and medico != "Todos":
            df = df[df['medico_id'] == medico]

        # Filtro por rango de edad
        if 'rango_edad' in df.columns and edad_rango != "Todos":
            df = df[df['rango_edad'] == edad_rango]

    # --- MÉTRICAS PRINCIPALES ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Atenciones", len(df))
    col2.metric("Recaudado Consultas", f"${df['valor_consulta'].sum():,.2f}")
    col3.metric("Recaudado Medicinas", f"${df['valor_medicina'].sum():,.2f}")

    # --- Estadísticas avanzadas ---
    with st.expander("Estadísticas avanzadas"):
        st.write(f"Filas únicas por especialidad: {df['especialidad'].nunique() if 'especialidad' in df.columns else 'N/A'}")
        if 'valor_consulta' in df.columns:
            st.write(f"Valor consulta - min: {df['valor_consulta'].min()}, max: {df['valor_consulta'].max()}, promedio: {df['valor_consulta'].mean():.2f}")
        if 'valor_medicina' in df.columns:
            st.write(f"Valor medicina - min: {df['valor_medicina'].min()}, max: {df['valor_medicina'].max()}, promedio: {df['valor_medicina'].mean():.2f}")
        if 'edad' in df.columns:
            st.write(f"Edades - min: {df['edad'].min()}, max: {df['edad'].max()}, promedio: {df['edad'].mean():.2f}")
        if 'genero' in df.columns:
            st.write("Distribución por género:")
            st.dataframe(df['genero'].value_counts(dropna=False))
        if 'institucion' in df.columns:
            st.write("Top 5 instituciones:")
            st.dataframe(df['institucion'].value_counts(dropna=False).head(5))

    # --- LAYOUT DE GRÁFICOS ---
    graf1, graf2 = st.columns(2)

    # Gráfico de barras apiladas: Especialidad por género
    if 'especialidad' in df.columns and 'genero' in df.columns:
        espec_genero = df.groupby(['especialidad', 'genero']).size().reset_index(name='atenciones')
        fig_espec = px.bar(
            espec_genero,
            x="especialidad",
            y="atenciones",
            color="genero",
            barmode="stack",
            title="Atenciones por Especialidad y Género"
        )
        graf1.plotly_chart(fig_espec, use_container_width=True)

    # Pie chart: Distribución por rango de edad
    if 'rango_edad' in df.columns:
        edad_counts = df['rango_edad'].value_counts().reset_index()
        edad_counts.columns = ['rango_edad', 'atenciones']
        fig_edad = px.pie(
            edad_counts,
            names='rango_edad',
            values='atenciones',
            title="Distribución por Rango de Edad"
        )
        graf2.plotly_chart(fig_edad, use_container_width=True)

    # Segunda fila de gráficos
    graf3, graf4 = st.columns(2)

    # Pie chart: Distribución por género
    if 'genero' in df.columns:
        genero_counts = df['genero'].value_counts().reset_index()
        genero_counts.columns = ['genero', 'atenciones']
        fig_genero = px.pie(
            genero_counts,
            names='genero',
            values='atenciones',
            title="Distribución por Género"
        )
        graf3.plotly_chart(fig_genero, use_container_width=True)

    # Pie chart: Distribución por institución
    if 'institucion' in df.columns:
        inst_counts = df['institucion'].value_counts().head(8).reset_index()
        inst_counts.columns = ['institucion', 'atenciones']
        fig_inst = px.pie(
            inst_counts,
            names='institucion',
            values='atenciones',
            title="Top 8 Instituciones"
        )
        graf4.plotly_chart(fig_inst, use_container_width=True)

    # Pie chart: Top 8 especialidades
    if 'especialidad' in df.columns:
        espec_counts = df['especialidad'].value_counts().head(8).reset_index()
        espec_counts.columns = ['especialidad', 'atenciones']
        fig_espec_pie = px.pie(
            espec_counts,
            names='especialidad',
            values='atenciones',
            title="Top 8 Especialidades"
        )
        st.plotly_chart(fig_espec_pie, use_container_width=True)

    # Gráfico de líneas: Atenciones por día
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'])
        atenciones_dia = df.groupby(df['fecha'].dt.date).size().reset_index(name='atenciones')
        fig_linea = px.line(
            atenciones_dia,
            x='fecha',
            y='atenciones',
            markers=True,
            title="Atenciones por Día"
        )
        st.plotly_chart(fig_linea, use_container_width=True)

    # --- Top 5 especialidades y médicos ---
    st.subheader("Top 5 Especialidades")
    st.bar_chart(df['especialidad'].value_counts().head(5))

    st.subheader("Top 5 Médicos (ID)")
    st.bar_chart(df['medico_id'].value_counts().head(5))

    # --- Tabla resumida por día ---
    resumen = df.groupby(df['fecha'].dt.date).agg({
        'valor_consulta': 'sum',
        'valor_medicina': 'sum',
        'especialidad': 'count'
    }).rename(columns={'especialidad': 'atenciones'})
    st.subheader("Resumen Diario")
    st.dataframe(resumen)

    # --- Descarga CSV ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar CSV", csv, "parte_diario.csv", "text/csv")

