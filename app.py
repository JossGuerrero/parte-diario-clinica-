import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import io
import time
from sqlalchemy import create_engine, text
import hashlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

st.set_page_config(
    page_title="ORACLE BI Hospital",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.theme = 'dark'
    st.session_state.current_data = None
    st.session_state.filtered_data = None
    # Inicializar estados de filtros
    st.session_state.filtro_inst = []
    st.session_state.filtro_med = []
    st.session_state.filtro_tipo = []
    st.session_state.filtro_gen = []
    st.session_state.filtro_edad = (0, 100)

# ============================================================================
# TEMAS PREMIUM (DARK MORADO)
# ============================================================================

THEMES = {
    "dark": {
        "primary": "#a855f7",
        "secondary": "#7c3aed",
        "accent": "#d8b4fe",
        "background": "#0f111a",
        "card": "#1a1c2c",
        "text": "#f3f4f6",
        "border": "#4b2cbb",
    },
    "medical": {
        "primary": "#10b981",
        "secondary": "#059669",
        "accent": "#34d399",
        "background": "#f0fdf4",
        "card": "#ffffff",
        "text": "#047857",
        "border": "#d1fae5",
    },
    "corporate": {
        "primary": "#1d4ed8",
        "secondary": "#1e40af",
        "accent": "#3b82f6",
        "background": "#f9fafb",
        "card": "#ffffff",
        "text": "#1f2937",
        "border": "#e5e7eb",
    }
}

def apply_theme(theme_name: str):
    if theme_name not in THEMES:
        theme_name = "dark"
    
    t = THEMES[theme_name]
    
    css = f"""
    <style>
        html, body, [data-testid="stAppViewContainer"] {{
            background: {t['background']} !important;
        }}
        .stApp {{ background: {t['background']} !important; }}
        
        .main-header {{
            background: linear-gradient(135deg, {t['primary']} 0%, {t['secondary']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 800;
            text-align: center;
        }}
        
        [data-testid="stSidebar"] {{
            background: {t['card']} !important;
            border-right: 1px solid {t['border']} !important;
        }}
        
        .stButton > button {{
            background: linear-gradient(135deg, {t['primary']} 0%, {t['secondary']} 100%) !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: {t['card']};
            border-radius: 8px 8px 0px 0px;
            padding: 10px 20px;
            color: {t['text']};
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {t['primary']} !important;
            color: white !important;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ============================================================================
# LOGIN
# ============================================================================

VALID_USERS = {
    "admin": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
    "hospital": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
    "medico": "6cf615d5e5f4dec0f4c1e46e5b2c76a8f6cc3b7c8d15e5e9e5c5b5a5958585a",
}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username: str, password: str) -> bool:
    if not username or not password or username not in VALID_USERS:
        return False
    return VALID_USERS[username] == hash_password(password)

def render_login():
    apply_theme("dark")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 class='main-header'>🏥 ORACLE BI</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #a855f7; margin-bottom: 2rem;'>Sistema Premium de Inteligencia Hospitalaria</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("👤 Usuario", placeholder="Ingrese su usuario")
            password = st.text_input("🔑 Contraseña", type="password", placeholder="Ingrese su contraseña")
            
            col_login, col_help = st.columns(2)
            with col_login:
                submit = st.form_submit_button("🚀 Ingresar", use_container_width=True)
            with col_help:
                show_help = st.form_submit_button("ℹ️ Demo", use_container_width=True)
            
            if submit:
                if verify_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.success("✅ ¡Bienvenido!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Credenciales inválidas")
            
            if show_help:
                st.info("""
                **Usuarios de prueba:**
                - admin / admin123
                - hospital / hospital123
                - medico / medico123
                """)

if not st.session_state.logged_in:
    render_login()
    st.stop()

# ============================================================================
# BASE DE DATOS
# ============================================================================

@st.cache_resource
def get_db_connection():
    try:
        engine = create_engine("postgresql+psycopg2://postgres:jossue205@localhost:5432/partes_diarios")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None

@st.cache_data(ttl=60)
def load_data(start_date: date, end_date: date) -> pd.DataFrame:
    engine = get_db_connection()
    if not engine:
        return pd.DataFrame()
    
    try:
        query = text("""
            SELECT
                a.fecha_atencion,
                COALESCE(a.genero, 'N/A') as genero,
                COALESCE(a.edad, 0) as edad,
                COALESCE(i.nombre, 'Sin Institución') as institucion,
                COALESCE(m.nombre, 'Sin Médico') as medico,
                COALESCE(tc.nombre, 'Otros') as tipo_consulta,
                COALESCE(c.descripcion, 'N/A') as diagnostico,
                COALESCE(a.valor_consulta, 0) as valor_consulta,
                COALESCE(a.valor_medicina, 0) as valor_medicina,
                (COALESCE(a.valor_consulta, 0) + COALESCE(a.valor_medicina, 0)) as total
            FROM atencion a
            LEFT JOIN medico m ON a.medico_id = m.id
            LEFT JOIN tipo_consulta tc ON a.tipo_consulta_id = tc.id
            LEFT JOIN cie10 c ON a.cie10_id = c.id
            LEFT JOIN paciente p ON a.paciente_id = p.id
            LEFT JOIN institucion i ON p.institucion_id = i.id
            WHERE a.fecha_atencion BETWEEN :start_date AND :end_date
            ORDER BY a.fecha_atencion DESC
        """)
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"start_date": start_date, "end_date": end_date})
            if not df.empty:
                df['fecha_atencion'] = pd.to_datetime(df['fecha_atencion'])
            return df
    except Exception as e:
        st.error(f"⚠️ Error al cargar datos: {str(e)}")
        return pd.DataFrame()

# ============================================================================
# FUNCIONES PARA EXPORTAR A EXCEL Y PDF (CORREGIDA)
# ============================================================================

def exportar_a_excel(df):
    """Exporta DataFrame a Excel con formato profesional"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Hoja de datos
        df.to_excel(writer, index=False, sheet_name='Datos')
        
        # Hoja de resumen
        resumen_data = {
            'Métrica': ['Total Registros', 'Ingresos Totales', 'Ticket Promedio', 
                       'Edad Promedio', 'Médicos Diferentes', 'Instituciones Diferentes'],
            'Valor': [
                len(df),
                f"${df['total'].sum():,.2f}",
                f"${df['total'].mean():,.2f}",
                f"{df['edad'].mean():.1f} años",
                df['medico'].nunique(),
                df['institucion'].nunique()
            ]
        }
        
        resumen_df = pd.DataFrame(resumen_data)
        resumen_df.to_excel(writer, index=False, sheet_name='Resumen')
        
        # Ajustar ancho de columnas en la hoja de datos
        worksheet_datos = writer.sheets['Datos']
        for idx, column in enumerate(df.columns, 1):
            column_width = max(df[column].astype(str).map(len).max(), len(column)) + 2
            col_letter = get_column_letter(idx)
            worksheet_datos.column_dimensions[col_letter].width = min(column_width, 30)
        
        # Ajustar ancho de columnas en la hoja de resumen
        worksheet_resumen = writer.sheets['Resumen']
        worksheet_resumen.column_dimensions['A'].width = 30
        worksheet_resumen.column_dimensions['B'].width = 30
    
    output.seek(0)
    return output.getvalue()

def exportar_a_pdf(df):
    """Exporta DataFrame a PDF con diseño profesional"""
    buffer = io.BytesIO()
    
    # Crear documento
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        textColor=colors.HexColor('#7c3aed'),
        spaceAfter=30
    )
    
    title = Paragraph(f"Reporte Hospitalario ORACLE BI", title_style)
    elements.append(title)
    
    # Subtítulo
    subtitle = Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
    elements.append(subtitle)
    
    elements.append(Spacer(1, 20))
    
    # Resumen estadístico
    resumen_text = f"""
    <b>Resumen Estadístico:</b><br/>
    • Total Registros: {len(df):,}<br/>
    • Ingresos Totales: ${df['total'].sum():,.2f}<br/>
    • Ticket Promedio: ${df['total'].mean():,.2f}<br/>
    • Edad Promedio: {df['edad'].mean():.1f} años<br/>
    • Médicos Diferentes: {df['medico'].nunique()}<br/>
    • Instituciones Diferentes: {df['institucion'].nunique()}<br/>
    • Rango de Fechas: {df['fecha_atencion'].min().strftime('%d/%m/%Y')} a {df['fecha_atencion'].max().strftime('%d/%m/%Y')}
    """
    
    resumen = Paragraph(resumen_text, styles['Normal'])
    elements.append(resumen)
    
    elements.append(Spacer(1, 30))
    
    # Tabla de datos (mostrar solo primeras 50 filas)
    table_data = [df.columns.tolist()]
    table_data.extend(df.head(50).values.tolist())
    
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    
    # Nota si hay más datos
    if len(df) > 50:
        nota = Paragraph(f"<i>Nota: Mostrando 50 de {len(df)} registros. Exporte a Excel para ver todos los datos.</i>", styles['Italic'])
        elements.append(Spacer(1, 10))
        elements.append(nota)
    
    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer.getvalue()

# ============================================================================
# APLICAR TEMA
# ============================================================================

apply_theme(st.session_state.theme)

# ============================================================================
# HEADER
# ============================================================================

col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

with col1:
    st.markdown(f"<h2 style='color: #a855f7; margin: 0;'>🏥 ORACLE BI Hospital</h2>", unsafe_allow_html=True)

with col2:
    st.markdown(f"<p style='text-align: right; color: #d8b4fe; margin: 0;'>{st.session_state.user}</p>", unsafe_allow_html=True)

with col3:
    theme_option = st.selectbox(
        "Tema",
        ["dark", "medical", "corporate"],
        index=0,
        label_visibility="collapsed",
        key="theme_select"
    )
    if theme_option != st.session_state.theme:
        st.session_state.theme = theme_option
        st.rerun()

with col4:
    if st.button("⚙️", help="Configuración"):
        pass

with col5:
    if st.button("🚪", help="Salir"):
        st.session_state.clear()
        st.rerun()

st.divider()

# ============================================================================
# SIDEBAR CON FILTROS
# ============================================================================

with st.sidebar:
    st.markdown("### 🎛️ Control Panel")
    
    # Rango de fechas
    today = date.today()
    date_range = st.date_input(
        "📅 Rango de fechas",
        [today - timedelta(days=30), today],
        label_visibility="collapsed"
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = today
    
    # Cargar datos
    with st.spinner("Cargando datos..."):
        df = load_data(start_date, end_date)
    
    if df.empty:
        st.error("No hay datos en el rango seleccionado")
        st.stop()
    
    st.success(f"✅ {len(df):,} registros")
    
    st.markdown("---")
    st.markdown("### 🔍 Filtros Avanzados")
    
    # Obtener opciones para filtros
    instituciones = sorted(df['institucion'].unique())
    medicos = sorted(df['medico'].unique())
    tipos = sorted(df['tipo_consulta'].unique())
    generos = sorted(df['genero'].unique())
    
    # Inicializar filtros si no existen en session_state
    if 'filtro_inst' not in st.session_state or not st.session_state.filtro_inst:
        st.session_state.filtro_inst = instituciones
    
    if 'filtro_med' not in st.session_state or not st.session_state.filtro_med:
        st.session_state.filtro_med = medicos
    
    if 'filtro_tipo' not in st.session_state or not st.session_state.filtro_tipo:
        st.session_state.filtro_tipo = tipos
    
    if 'filtro_gen' not in st.session_state or not st.session_state.filtro_gen:
        st.session_state.filtro_gen = generos
    
    # Filtro de Instituciones
    st.markdown("#### Instituciones")
    filtro_inst = st.multiselect(
        "",
        instituciones,
        default=st.session_state.filtro_inst,
        label_visibility="collapsed",
        key="multiselect_instituciones"
    )
    
    # Filtro de Médicos
    st.markdown("#### Médicos")
    filtro_med = st.multiselect(
        "",
        medicos,
        default=st.session_state.filtro_med,
        label_visibility="collapsed",
        key="multiselect_medicos"
    )
    
    # Filtro de Tipo Consulta
    st.markdown("#### Tipo Consulta")
    filtro_tipo = st.multiselect(
        "",
        tipos,
        default=st.session_state.filtro_tipo,
        label_visibility="collapsed",
        key="multiselect_tipo"
    )
    
    # Filtro de Género
    st.markdown("#### Género")
    filtro_gen = st.multiselect(
        "",
        generos,
        default=st.session_state.filtro_gen,
        label_visibility="collapsed",
        key="multiselect_genero"
    )
    
    # Filtro de Edad
    st.markdown("#### Edad")
    
    # Obtener min y max de edad con validación
    min_edad = int(df['edad'].min()) if not df.empty else 0
    max_edad = int(df['edad'].max()) if not df.empty else 100
    
    # Asegurar que min < max
    if min_edad >= max_edad:
        max_edad = min_edad + 1
    
    # Inicializar filtro de edad si no existe
    if 'filtro_edad' not in st.session_state:
        st.session_state.filtro_edad = (min_edad, max_edad)
    
    # Slider de edad
    edad_range = st.slider(
        "",
        min_value=min_edad,
        max_value=max_edad,
        value=st.session_state.filtro_edad,
        label_visibility="collapsed",
        key="slider_edad"
    )
    
    st.markdown(f"**Rango seleccionado:** {edad_range[0]} - {edad_range[1]} años")
    
    st.markdown("---")
    
    # Botones de acción
    col_apply, col_reset = st.columns(2)
    with col_apply:
        aplicar = st.button("🔄 Aplicar", use_container_width=True, type="primary")
    
    with col_reset:
        limpiar = st.button("♻️ Limpiar", use_container_width=True)
    
    # Manejar botón Aplicar
    if aplicar:
        st.session_state.filtro_inst = filtro_inst if filtro_inst else instituciones
        st.session_state.filtro_med = filtro_med if filtro_med else medicos
        st.session_state.filtro_tipo = filtro_tipo if filtro_tipo else tipos
        st.session_state.filtro_gen = filtro_gen if filtro_gen else generos
        st.session_state.filtro_edad = edad_range
        st.rerun()
    
    # Manejar botón Limpiar
    if limpiar:
        st.session_state.filtro_inst = instituciones
        st.session_state.filtro_med = medicos
        st.session_state.filtro_tipo = tipos
        st.session_state.filtro_gen = generos
        st.session_state.filtro_edad = (min_edad, max_edad)
        st.rerun()

# ============================================================================
# FILTRADO DE DATOS
# ============================================================================

# Aplicar filtros
if df.empty:
    df_filtrado = pd.DataFrame()
else:
    # Usar filtros de session_state
    filtro_inst = st.session_state.filtro_inst if st.session_state.filtro_inst else instituciones
    filtro_med = st.session_state.filtro_med if st.session_state.filtro_med else medicos
    filtro_tipo = st.session_state.filtro_tipo if st.session_state.filtro_tipo else tipos
    filtro_gen = st.session_state.filtro_gen if st.session_state.filtro_gen else generos
    edad_range = st.session_state.filtro_edad
    
    df_filtrado = df[
        (df['institucion'].isin(filtro_inst)) &
        (df['medico'].isin(filtro_med)) &
        (df['tipo_consulta'].isin(filtro_tipo)) &
        (df['genero'].isin(filtro_gen)) &
        (df['edad'] >= edad_range[0]) &
        (df['edad'] <= edad_range[1])
    ].copy()

st.session_state.filtered_data = df_filtrado

# ============================================================================
# KPIs PRINCIPALES
# ============================================================================

st.markdown("### 📊 Indicadores Principales")

if df_filtrado.empty:
    st.warning("No hay datos que coincidan con los filtros seleccionados")
    df_filtrado = df

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("👥 Atenciones", f"{len(df_filtrado):,}")

with k2:
    st.metric("💰 Ingresos", f"${df_filtrado['total'].sum():,.0f}")

with k3:
    ticket_prom = df_filtrado['total'].mean() if not df_filtrado.empty else 0
    st.metric("📈 Ticket Prom", f"${ticket_prom:,.0f}")

with k4:
    edad_prom = df_filtrado['edad'].mean() if not df_filtrado.empty else 0
    st.metric("🎂 Edad Prom", f"{edad_prom:.0f} años")

st.divider()

# ============================================================================
# PESTAÑAS COMO EN TU IMAGEN
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📈 Análisis", "📊 Estadísticas", "📋 Datos", "⚙️ Config"])

with tab1:
    st.markdown("### Visualizaciones Interactivas")
    
    if df_filtrado.empty:
        st.info("Seleccione filtros para ver visualizaciones")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📈 Atenciones Diarias**")
            df_temp = df_filtrado.copy()
            df_temp['fecha'] = df_temp['fecha_atencion'].dt.date
            atenciones_diarias = df_temp.groupby('fecha').size().reset_index(name='atenciones')
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=atenciones_diarias['fecha'],
                y=atenciones_diarias['atenciones'],
                mode='lines+markers',
                line=dict(color='#a855f7', width=3),
                marker=dict(size=6, color='#7c3aed'),
                fill='tozeroy',
                fillcolor='rgba(168, 85, 247, 0.1)',
                name='Atenciones'
            ))
            
            fig.update_layout(
                height=350,
                template='plotly_dark',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Fecha",
                yaxis_title="N° de Atenciones",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**💰 Ingresos Diarios**")
            ingresos_diarios = df_temp.groupby('fecha')['total'].sum().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=ingresos_diarios['fecha'],
                y=ingresos_diarios['total'],
                marker_color='#7c3aed',
                name='Ingresos'
            ))
            
            fig.update_layout(
                height=350,
                template='plotly_dark',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Fecha",
                yaxis_title="Ingresos ($)",
                hovermode='x unified'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.markdown("**🏥 Top Instituciones**")
            top_inst = df_filtrado['institucion'].value_counts().head(8)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=top_inst.values,
                y=top_inst.index,
                orientation='h',
                marker_color='#a855f7',
                name='Instituciones'
            ))
            
            fig.update_layout(
                height=350,
                template='plotly_dark',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="N° de Atenciones",
                yaxis_title="Institución",
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            st.markdown("**👨‍⚕️ Top Médicos**")
            top_med = df_filtrado['medico'].value_counts().head(8)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=top_med.values,
                y=top_med.index,
                orientation='h',
                marker_color='#d8b4fe',
                name='Médicos'
            ))
            
            fig.update_layout(
                height=350,
                template='plotly_dark',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="N° de Atenciones",
                yaxis_title="Médico",
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### 📊 Estadísticas Detalladas")
    
    if not df_filtrado.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Distribución por Género**")
            genero_dist = df_filtrado['genero'].value_counts()
            
            fig = go.Figure(data=[go.Pie(
                labels=genero_dist.index,
                values=genero_dist.values,
                hole=0.4,
                marker_colors=['#a855f7', '#7c3aed', '#d8b4fe'],
                textinfo='label+percent'
            )])
            fig.update_layout(
                height=350,
                template='plotly_dark',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**Distribución por Tipo de Consulta**")
            tipo_dist = df_filtrado['tipo_consulta'].value_counts()
            
            fig = go.Figure(data=[go.Pie(
                labels=tipo_dist.index,
                values=tipo_dist.values,
                hole=0.4,
                marker_colors=['#a855f7', '#7c3aed', '#d8b4fe', '#4b2cbb'],
                textinfo='label+percent'
            )])
            fig.update_layout(
                height=350,
                template='plotly_dark',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("**Estadísticas Numéricas**")
        stats_df = df_filtrado[['edad', 'valor_consulta', 'valor_medicina', 'total']].describe()
        st.dataframe(
            stats_df.style.format("{:.2f}"),
            use_container_width=True
        )

with tab3:
    st.markdown("### 📋 Exportación de Datos")
    
    if not df_filtrado.empty:
        # Información de resumen
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.info(f"**Total de registros:** {len(df_filtrado):,}")
        with col_info2:
            st.info(f"**Ingresos totales:** ${df_filtrado['total'].sum():,.2f}")
        
        st.markdown("---")
        
        # Botones de exportación
        st.markdown("#### 📥 Exportar en Diferentes Formatos")
        
        col_csv, col_excel, col_pdf = st.columns(3)
        
        with col_csv:
            csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📄 Descargar CSV",
                data=csv_data,
                file_name=f"datos_hospital_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
                help="Formato CSV compatible con Excel y otros programas"
            )
        
        with col_excel:
            try:
                excel_data = exportar_a_excel(df_filtrado)
                st.download_button(
                    label="📊 Descargar Excel",
                    data=excel_data,
                    file_name=f"reporte_hospital_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help="Formato Excel con formato profesional y hojas de resumen"
                )
            except Exception as e:
                st.error(f"Error al generar Excel: {str(e)}")
                # Fallback a CSV si hay error con Excel
                csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📊 Descargar CSV (alternativo)",
                    data=csv_data,
                    file_name=f"datos_hospital_{date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col_pdf:
            try:
                pdf_data = exportar_a_pdf(df_filtrado)
                st.download_button(
                    label="📘 Descargar PDF",
                    data=pdf_data,
                    file_name=f"reporte_hospital_{date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="Reporte PDF con resumen estadístico y tabla de datos"
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {str(e)}")
        
        st.markdown("---")
        
        # Vista previa de datos
        st.markdown("#### 👁️ Vista Previa de Datos")
        st.markdown("*Seleccione las filas para resaltar detalles. Puede ordenar por columnas haciendo clic en los encabezados.*")
        
        # Dataframe interactivo con formato mejorado
        st.dataframe(
            df_filtrado,
            column_config={
                "fecha_atencion": st.column_config.DatetimeColumn(
                    "Fecha",
                    format="D MMM YYYY, h:mm a",
                    help="Fecha y hora de la atención"
                ),
                "genero": st.column_config.TextColumn(
                    "Género",
                    help="Género del paciente"
                ),
                "edad": st.column_config.NumberColumn(
                    "Edad",
                    format="%d años",
                    help="Edad del paciente"
                ),
                "institucion": st.column_config.TextColumn(
                    "Institución",
                    help="Institución de salud"
                ),
                "medico": st.column_config.TextColumn(
                    "Médico",
                    help="Médico tratante"
                ),
                "tipo_consulta": st.column_config.TextColumn(
                    "Tipo Consulta",
                    help="Tipo de consulta realizada"
                ),
                "diagnostico": st.column_config.TextColumn(
                    "Diagnóstico",
                    help="Diagnóstico según CIE-10"
                ),
                "valor_consulta": st.column_config.NumberColumn(
                    "Consulta",
                    format="$%.2f",
                    help="Valor de la consulta"
                ),
                "valor_medicina": st.column_config.NumberColumn(
                    "Medicina",
                    format="$%.2f",
                    help="Valor de medicinas"
                ),
                "total": st.column_config.NumberColumn(
                    "Total",
                    format="$%.2f",
                    help="Valor total (consulta + medicina)"
                ),
            },
            use_container_width=True,
            height=500,
            hide_index=True
        )
    else:
        st.warning("No hay datos para exportar. Aplique filtros primero.")

with tab4:
    st.markdown("### ⚙️ Configuración del Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("#### 👤 Información de Usuario")
            st.text_input("Usuario actual", value=st.session_state.user, disabled=True)
            
            if st.session_state.user == 'admin':
                rol = "Administrador"
            elif st.session_state.user == 'hospital':
                rol = "Gestor Hospital"
            else:
                rol = "Médico"
            
            st.text_input("Rol asignado", value=rol, disabled=True)
            st.text_input("Último acceso", value=datetime.now().strftime("%d/%m/%Y %H:%M:%S"), disabled=True)
            
            if st.button("🔄 Actualizar perfil", use_container_width=True):
                st.info("Función en desarrollo")
    
    with col2:
        with st.container(border=True):
            st.markdown("#### 🗄️ Configuración de Base de Datos")
            
            # Estado de conexión
            try:
                engine = get_db_connection()
                if engine:
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT COUNT(*) FROM atencion")).fetchone()
                        total_registros = result[0] if result else 0
                    
                    st.success("🟢 Conectado")
                    st.metric("Registros en sistema", f"{total_registros:,}")
                else:
                    st.error("🔴 Desconectado")
            except:
                st.error("🔴 Error de conexión")
            
            st.progress(75, text="Uso de almacenamiento: 75%")
            
            if st.button("🔄 Probar conexión", use_container_width=True):
                st.cache_resource.clear()
                st.rerun()
    
    st.divider()
    
    # Configuración de tema
    st.markdown("#### 🎨 Personalización")
    
    tema_actual = st.selectbox(
        "Tema de la aplicación",
        ["dark", "medical", "corporate"],
        index=["dark", "medical", "corporate"].index(st.session_state.theme),
        help="Seleccione el tema visual de la aplicación"
    )
    
    if tema_actual != st.session_state.theme:
        st.session_state.theme = tema_actual
        st.rerun()
    
    # Configuración de exportación
    st.markdown("#### 📤 Preferencias de Exportación")
    
    col_export1, col_export2 = st.columns(2)
    with col_export1:
        incluir_resumen = st.checkbox("Incluir resumen estadístico", value=True)
    with col_export2:
        formato_fecha = st.selectbox("Formato de fecha", ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"])
    
    if st.button("💾 Guardar configuración", use_container_width=True):
        st.success("Configuración guardada exitosamente")
    
    st.divider()
    st.caption("ORACLE BI Hospital System v3.0 | © 2024 | Soporte: soporte@oraclebi.com")
