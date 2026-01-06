import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import io
import time
from sqlalchemy import create_engine, text
import hashlib

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
    st.session_state.theme = 'medical'
    st.session_state.current_data = None
    st.session_state.filtered_data = None

# ============================================================================
# TEMAS PREMIUM
# ============================================================================

THEMES = {
    "medical": {
        "primary": "#10b981",
        "secondary": "#059669",
        "accent": "#34d399",
        "background": "#f0fdf4",
        "card": "#ffffff",
        "text": "#047857",
        "border": "#d1fae5",
        "chart1": "#10b981",
        "chart2": "#34d399",
        "chart3": "#6ee7b7",
    },
    "dark": {
        "primary": "#3b82f6",
        "secondary": "#1e40af",
        "accent": "#60a5fa",
        "background": "#0f172a",
        "card": "#1e293b",
        "text": "#e2e8f0",
        "border": "#334155",
        "chart1": "#3b82f6",
        "chart2": "#60a5fa",
        "chart3": "#93c5fd",
    },
    "corporate": {
        "primary": "#1d4ed8",
        "secondary": "#1e40af",
        "accent": "#3b82f6",
        "background": "#f9fafb",
        "card": "#ffffff",
        "text": "#1f2937",
        "border": "#e5e7eb",
        "chart1": "#1d4ed8",
        "chart2": "#3b82f6",
        "chart3": "#60a5fa",
    }
}

def apply_theme(theme_name: str):
    """Aplica tema premium con CSS avanzado"""
    if theme_name not in THEMES:
        theme_name = "medical"
    
    t = THEMES[theme_name]
    
    css = f"""
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        html, body, [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, {t['background']} 0%, {t['background']} 100%);
        }}
        
        .stApp {{ 
            background: linear-gradient(135deg, {t['background']} 0%, {t['background']} 100%);
        }}
        
        /* HEADER */
        .main-header {{
            background: linear-gradient(135deg, {t['primary']} 0%, {t['secondary']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3.5rem;
            font-weight: 900;
            text-align: center;
            margin-bottom: 1rem;
            letter-spacing: -2px;
            text-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .subtitle {{
            text-align: center;
            color: {t['text']};
            font-size: 1.1rem;
            margin-bottom: 2rem;
            opacity: 0.8;
            letter-spacing: 0.5px;
        }}
        
        /* BOTONES */
        .stButton > button {{
            background: linear-gradient(135deg, {t['primary']} 0%, {t['secondary']} 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            padding: 14px 28px !important;
            font-size: 1rem !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important;
            cursor: pointer !important;
            letter-spacing: 0.5px;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4) !important;
        }}
        
        .stButton > button:active {{
            transform: translateY(-1px) !important;
        }}
        
        /* INPUTS */
        .stTextInput > div > div > input {{
            border-radius: 10px !important;
            border: 2px solid {t['border']} !important;
            padding: 14px 16px !important;
            font-size: 1rem !important;
            background: {t['card']} !important;
            color: {t['text']} !important;
            transition: all 0.3s ease !important;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: {t['primary']} !important;
            box-shadow: 0 0 0 4px {t['accent']}33 !important;
            background: {t['card']} !important;
        }}
        
        /* FORM */
        .stForm {{
            border: none !important;
            background: {t['card']} !important;
            border-radius: 16px !important;
            padding: 2.5rem !important;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08) !important;
            border: 1px solid {t['border']} !important;
        }}
        
        /* MÉTRICA */
        [data-testid="metric-container"] {{
            background: {t['card']} !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            border: 1px solid {t['border']} !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
            transition: all 0.3s ease !important;
        }}
        
        [data-testid="metric-container"]:hover {{
            transform: translateY(-4px) !important;
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.15) !important;
        }}
        
        /* SELECTBOX */
        .stSelectbox > div > div {{
            border-radius: 10px !important;
            border: 2px solid {t['border']} !important;
            background: {t['card']} !important;
            padding: 10px !important;
        }}
        
        .stSelectbox > div > div > div {{
            color: {t['text']} !important;
        }}
        
        /* MULTISELECT */
        .stMultiSelect > div > div {{
            border-radius: 10px !important;
            border: 2px solid {t['border']} !important;
            background: {t['card']} !important;
            padding: 10px !important;
        }}
        
        /* SLIDER */
        .stSlider > div > div > div > div {{
            border-radius: 10px !important;
        }}
        
        /* DIVIDER */
        hr {{
            border: none !important;
            height: 1px !important;
            background: linear-gradient(90deg, transparent, {t['border']}, transparent) !important;
            margin: 2rem 0 !important;
        }}
        
        /* TABS */
        .stTabs {{
            padding: 0;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            color: {t['text']}80 !important;
            border-bottom: 2px solid transparent !important;
            padding: 16px 24px !important;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .stTabs [aria-selected="true"] {{
            color: {t['primary']} !important;
            border-bottom-color: {t['primary']} !important;
        }}
        
        /* SIDEBAR */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {t['card']} 0%, {t['background']} 100%) !important;
            border-right: 1px solid {t['border']} !important;
        }}
        
        /* ALERT/INFO */
        .stAlert {{
            border-radius: 10px !important;
            border-left: 4px solid {t['primary']} !important;
            padding: 1.2rem !important;
            background: {t['card']} !important;
        }}
        
        /* CONTAINER */
        .stContainer {{
            border-radius: 12px !important;
            border: 1px solid {t['border']} !important;
            padding: 1.5rem !important;
            background: {t['card']} !important;
        }}
        
        /* SCROLLBAR */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: {t['background']};
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: {t['accent']};
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: {t['primary']};
        }}
        
        /* ESPACIOS */
        h1, h2, h3 {{
            color: {t['text']} !important;
            font-weight: 700 !important;
        }}
        
        p, span, label {{
            color: {t['text']} !important;
        }}
        
        /* RESPONSIVE */
        @media (max-width: 768px) {{
            .main-header {{ font-size: 2.2rem; }}
            .stButton > button {{ padding: 12px 20px !important; }}
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
    apply_theme("medical")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 class='main-header'>🏥 ORACLE BI</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Sistema Premium de Inteligencia Hospitalaria</p>", unsafe_allow_html=True)
        
        with st.form("login_form", border=False):
            st.markdown("### 🔐 Acceso al Sistema")
            st.markdown("---")
            
            username = st.text_input(
                "👤 Usuario",
                placeholder="Ingrese su usuario",
                label_visibility="collapsed"
            )
            
            password = st.text_input(
                "🔑 Contraseña",
                type="password",
                placeholder="Ingrese su contraseña",
                label_visibility="collapsed"
            )
            
            st.markdown("")
            col_login, col_help = st.columns([2, 1])
            
            with col_login:
                submit = st.form_submit_button(
                    "🚀 Ingresar",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_help:
                show_help = st.form_submit_button(
                    "ℹ️ Demo",
                    use_container_width=True
                )
            
            if submit:
                if not username or not password:
                    st.error("⚠️ Complete todos los campos")
                elif verify_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.success("✅ ¡Bienvenido!")
                    time.sleep(0.8)
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
        
        st.markdown("---")
        st.caption("🔒 Seguridad empresarial | ORACLE BI v3.0")

if not st.session_state.logged_in:
    render_login()
    st.stop()

# ============================================================================
# BD
# ============================================================================
# Busca esta parte en TU código (arriba) y verifica la contraseña
@st.cache_resource(show_spinner="Conectando a PostgreSQL...")
def get_db_connection():
    try:
        # Credenciales exactas según tu configuración
        user = "postgres"
        password = "jossue205"
        host = "localhost" 
        port = "5432"
        dbname = "partes_diarios"
        
        conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        engine = create_engine(conn_str, pool_size=5, max_overflow=10)
        
        # Validar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        # Solo imprime el error técnico en la terminal para diagnóstico
        print(f"DEBUG: Fallo de conexión -> {e}")
        return None

@st.cache_data(ttl=60) # Actualización cada minuto
def load_data(start_date: date, end_date: date) -> pd.DataFrame:
    engine = get_db_connection()
    
    # Estructura base de la tabla (vacía por defecto)
    columns = [
        'fecha_atencion', 'genero', 'edad', 'institucion', 'medico', 
        'tipo_consulta', 'diagnostico', 'valor_consulta', 'valor_medicina', 'total'
    ]
    
    if not engine:
        st.error("❌ No se pudo establecer conexión con el servidor de base de datos.")
        return pd.DataFrame(columns=columns)

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
            
            if df.empty:
                st.info(f"ℹ️ No existen registros entre {start_date} y {end_date}.")
                return pd.DataFrame(columns=columns)
            
            # Asegurar formato de fecha para Streamlit
            df['fecha_atencion'] = pd.to_datetime(df['fecha_atencion'])
            return df

    except Exception as e:
        st.error(f"⚠️ Error al consultar la tabla 'atencion': {e}")
        return pd.DataFrame(columns=columns)

# ============================================================================
# TEMA
# ============================================================================

apply_theme(st.session_state.theme)

# ============================================================================
# HEADER
# ============================================================================

col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2, 1, 0.8, 0.8, 0.8])

with col_h1:
    st.markdown(f"<h2 style='margin:0; color: #10b981;'>🏥 ORACLE BI Hospital</h2>", unsafe_allow_html=True)

with col_h2:
    st.markdown(f"<p style='text-align:right; font-weight:600; margin:0;'>{st.session_state.user.upper()}</p>", unsafe_allow_html=True)
    st.caption(f"{date.today().strftime('%d/%m/%Y')}")

with col_h3:
    new_theme = st.selectbox(
        "T",
        ["medical", "dark", "corporate"],
        index=["medical", "dark", "corporate"].index(st.session_state.theme),
        label_visibility="collapsed",
        key="theme_sel"
    )
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

with col_h4:
    if st.button("⚙️", help="Configuración"):
        pass

with col_h5:
    if st.button("🚪", help="Salir"):
        st.session_state.clear()
        st.rerun()

st.divider()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### 🎛️ Control Panel")
    st.markdown("")
    
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
    
    with st.spinner("⏳ Cargando datos..."):
        df = load_data(start_date, end_date)
    
    if not df.empty:
        st.session_state.current_data = df
        st.success(f"✅ {len(df):,} registros")
    else:
        st.error("❌ Sin datos")
        st.stop()
    
    st.markdown("---")
    st.markdown("### 🔍 Filtros Avanzados")
    
    instituciones = sorted(df['institucion'].unique())
    filtro_inst = st.multiselect(
        "🏥 Instituciones",
        instituciones,
        default=instituciones[:min(2, len(instituciones))],
        key="f_inst"
    )
    
    medicos = sorted(df['medico'].unique())
    filtro_med = st.multiselect(
        "👨‍⚕️ Médicos",
        medicos,
        default=medicos[:min(2, len(medicos))],
        key="f_med"
    )
    
    tipos = sorted(df['tipo_consulta'].unique())
    filtro_tipo = st.multiselect(
        "📋 Tipo Consulta",
        tipos,
        default=tipos,
        key="f_tipo"
    )
    
    generos = sorted(df['genero'].unique())
    filtro_gen = st.multiselect(
        "⚧ Género",
        generos,
        default=generos,
        key="f_gen"
    )
    
    min_edad, max_edad = int(df['edad'].min()), int(df['edad'].max())
    edad_range = st.slider(
        "🎂 Edad",
        min_edad, max_edad, (min_edad, max_edad),
        key="f_edad"
    )
    
    st.markdown("")
    if st.button("🔄 Aplicar", type="primary", use_container_width=True):
        st.rerun()

# ============================================================================
# FILTRAR
# ============================================================================

df_filtrado = df[
    (df['institucion'].isin(filtro_inst)) &
    (df['medico'].isin(filtro_med)) &
    (df['tipo_consulta'].isin(filtro_tipo)) &
    (df['genero'].isin(filtro_gen)) &
    (df['edad'].between(edad_range[0], edad_range[1]))
].copy()

if df_filtrado.empty:
    st.warning("⚠️ Sin resultados")
    df_filtrado = df.copy()

st.session_state.filtered_data = df_filtrado

# ============================================================================
# KPIs PREMIUM
# ============================================================================

st.markdown("### 📊 Indicadores Principales")

k1, k2, k3, k4, k5, k6 = st.columns(6)

metrics = [
    (k1, "👥", "Atenciones", f"{len(df_filtrado):,}", "#10b981"),
    (k2, "💰", "Ingresos", f"${df_filtrado['total'].sum():,.0f}", "#059669"),
    (k3, "📈", "Ticket Prom", f"${df_filtrado['total'].mean():,.0f}", "#34d399"),
    (k4, "🎂", "Edad Prom", f"{df_filtrado['edad'].mean():.0f}", "#6ee7b7"),
    (k5, "👨‍⚕️", "Médicos", f"{df_filtrado['medico'].nunique()}", "#10b981"),
    (k6, "🏥", "Instituciones", f"{df_filtrado['institucion'].nunique()}", "#059669"),
]

for col, icon, label, value, color in metrics:
    with col:
        st.metric(f"{icon} {label}", value)

st.divider()

# ============================================================================
# ANÁLISIS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📈 Análisis", "📊 Estadísticas", "📋 Datos", "⚙️ Config"])

with tab1:
    st.markdown("### Visualizaciones Interactivas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📈 Atenciones Diarias**")
        df_temp = df_filtrado.copy()
        df_temp['fecha'] = df_temp['fecha_atencion'].dt.date
        daily = df_temp.groupby('fecha').agg({'fecha_atencion': 'count', 'total': 'sum'}).rename(columns={'fecha_atencion': 'atenciones'})
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily.index,
            y=daily['atenciones'],
            name='Atenciones',
            mode='lines+markers',
            line=dict(color='#10b981', width=3),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.1)',
            hovertemplate='<b>%{x}</b><br>%{y} atenciones<extra></extra>'
        ))
        fig.update_layout(
            height=350,
            margin=dict(t=20, b=20, l=40, r=20),
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=11, color='#047857'),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(16, 185, 129, 0.1)')
        )
        st.plotly_chart(fig, use_container_width=True, config={'responsive': True, 'displayModeBar': False})
    
    with col2:
        st.markdown("**💰 Ingresos Diarios**")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily.index,
            y=daily['total'],
            name='Ingresos',
            marker=dict(
                color=daily['total'],
                colorscale=[[0, '#d1fae5'], [1, '#059669']],
                showscale=False
            ),
            hovertemplate='<b>%{x}</b><br>${%{y:,.0f}}<extra></extra>'
        ))
        fig.update_layout(
            height=350,
            margin=dict(t=20, b=20, l=40, r=20),
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=11, color='#047857'),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(16, 185, 129, 0.1)'),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'responsive': True, 'displayModeBar': False})
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("**🏥 Top Instituciones**")
        top_inst = df_filtrado['institucion'].value_counts().head(8)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_inst.index,
            x=top_inst.values,
            orientation='h',
            marker=dict(
                color=top_inst.values,
                colorscale=[[0, '#d1fae5'], [1, '#047857']],
                showscale=False
            ),
            text=top_inst.values,
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>%{x} atenciones<extra></extra>'
        ))
        fig.update_layout(
            height=350,
            margin=dict(t=20, b=20, l=150, r=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=11, color='#047857'),
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(16, 185, 129, 0.1)'),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'responsive': True, 'displayModeBar': False})
    
    with col4:
        st.markdown("**👨‍⚕️ Top Médicos**")
        top_med = df_filtrado['medico'].value_counts().head(8)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_med.index,
            x=top_med.values,
            orientation='h',
            marker=dict(
                color=top_med.values,
                colorscale=[[0, '#d1fae5'], [1, '#047857']],
                showscale=False
            ),
            text=top_med.values,
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>%{x} atenciones<extra></extra>'
        ))
        fig.update_layout(
            height=350,
            margin=dict(t=20, b=20, l=120, r=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=11, color='#047857'),
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(16, 185, 129, 0.1)'),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'responsive': True, 'displayModeBar': False})
    
    st.markdown("**📋 Distribución por Tipo Consulta**")
    tipo_dist = df_filtrado['tipo_consulta'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=tipo_dist.index,
        values=tipo_dist.values,
        hole=0.35,
        marker=dict(colors=['#10b981', '#34d399', '#6ee7b7', '#d1fae5', '#a7f3d0'][:len(tipo_dist)]),
        hovertemplate='<b>%{label}</b><br>%{value} (%{percent})<extra></extra>'
    )])
    fig.update_layout(
        height=400,
        margin=dict(t=30, b=30),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12, color='#047857')
    )
    st.plotly_chart(fig, use_container_width=True, config={'responsive': True, 'displayModeBar': False})

with tab2:
    st.markdown("### 📊 Estadísticas Detalladas")
    
    # 1. Resumen Estadístico
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("**Resumen Numérico**")
        stats = df_filtrado[['edad', 'valor_consulta', 'valor_medicina', 'total']].describe().T
        st.dataframe(stats.style.format("{:.2f}"), use_container_width=True)
    
    with col2:
        st.markdown("**Matriz: Institución vs Género**")
        # Tabla pivote real usando los datos
        try:
            pivot = pd.pivot_table(
                df_filtrado, 
                values='total', 
                index='institucion', 
                columns='genero', 
                aggfunc='sum',
                fill_value=0
            )
            # Mapa de calor simple usando dataframe gradient
            st.dataframe(
                pivot.style.background_gradient(cmap='Greens', axis=None).format("${:,.0f}"),
                use_container_width=True
            )
        except Exception as e:
            st.error(f"No hay suficientes datos para generar la matriz: {e}")

    st.divider()
    
    # 2. Top Diagnósticos
    st.markdown("### 🩺 Diagnósticos Frecuentes")
    col3, col4 = st.columns(2)
    
    with col3:
        diag_counts = df_filtrado['diagnostico'].value_counts().reset_index()
        diag_counts.columns = ['Diagnóstico', 'Cantidad']
        st.dataframe(diag_counts, use_container_width=True, hide_index=True)
        
    with col4:
        # Gráfico de dispersión Edad vs Costo
        fig_scatter = go.Figure(data=go.Scatter(
            x=df_filtrado['edad'],
            y=df_filtrado['total'],
            mode='markers',
            marker=dict(
                size=8,
                color=df_filtrado['valor_consulta'], # Color por valor
                colorscale='Viridis',
                showscale=True
            ),
            text=df_filtrado['diagnostico'],
            hovertemplate="<b>%{text}</b><br>Edad: %{x}<br>Total: $%{y}<extra></extra>"
        ))
        fig_scatter.update_layout(
            title="Relación Edad vs Costo Total",
            xaxis_title="Edad del Paciente",
            yaxis_title="Costo Total ($)",
            height=300,
            margin=dict(l=20, r=20, t=30, b=20),
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

with tab3:
    st.markdown("### 📋 Exportación de Datos")
    
    col_dl1, col_dl2 = st.columns([4, 1])
    with col_dl1:
        st.info("💡 Seleccione las filas para resaltar detalles. Puede ordenar por columnas haciendo clic en los encabezados.")
    with col_dl2:
        # Botón de descarga CSV
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f'reporte_hospital_{date.today()}.csv',
            mime='text/csv',
            type="primary"
        )
    
    # Dataframe interactivo
    st.dataframe(
        df_filtrado,
        column_config={
            "fecha_atencion": st.column_config.DatetimeColumn("Fecha", format="D MMM YYYY, h:mm a"),
            "valor_consulta": st.column_config.NumberColumn("Consulta", format="$%.2f"),
            "valor_medicina": st.column_config.NumberColumn("Medicina", format="$%.2f"),
            "total": st.column_config.NumberColumn("Total", format="$%.2f"),
            "genero": st.column_config.TextColumn("Género", width="small"),
            "edad": st.column_config.ProgressColumn("Edad", format="%d años", min_value=0, max_value=100),
        },
        use_container_width=True,
        height=500,
        hide_index=True
    )

with tab4:
    st.markdown("### ⚙️ Configuración del Sistema")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("#### 👤 Perfil de Usuario")
        with st.container(border=True):
            st.text_input("Usuario actual", value=st.session_state.user, disabled=True)
            st.text_input("Rol asignado", value="Administrador" if st.session_state.user == 'admin' else "Usuario Estándar", disabled=True)
            st.text_input("Último acceso", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), disabled=True)
            
    with c2:
        st.markdown("#### 🔧 Preferencias de Base de Datos")
        with st.container(border=True):
            db_status = "🟢 Conectado" if get_db_connection() else "🟠 Modo Demo (Sin conexión)"
            st.markdown(f"**Estado del Servidor:** {db_status}")
            
            st.markdown("Reintentar conexión manualmente:")
            if st.button("🔄 Reconectar DB"):
                st.cache_resource.clear()
                st.rerun()

    st.markdown("---")
    st.caption("Oracle BI Hospital System v3.0 | Soporte Técnico: admin@hospital.com")