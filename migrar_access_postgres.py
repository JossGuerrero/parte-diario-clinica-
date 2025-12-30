import os
import logging
import pyodbc
import pandas as pd
from sqlalchemy import create_engine
import numpy as np
import time
import argparse
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

print("Iniciando migración de Access a PostgreSQL...")

# --- Medir tiempo de ejecución ---
start_time = time.time()

# --- Argumentos por línea de comandos ---
parser = argparse.ArgumentParser(description="Migrar datos de Access a PostgreSQL")
parser.add_argument('--fecha_inicio', type=str, help='Migrar solo desde esta fecha (YYYY-MM-DD)')
parser.add_argument('--fecha_fin', type=str, help='Migrar solo hasta esta fecha (YYYY-MM-DD)')
parser.add_argument('--excel', action='store_true', help='Exportar también a Excel')
parser.add_argument('--columnas', type=str, help='Lista separada por coma de columnas a migrar (ej: col1,col2,col3)')
args = parser.parse_args()

# 1. Conexión a Access
access_file = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
access_pwd = os.getenv('ACCESS_PWD', 'NeoAvanEcu22')
conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    f'DBQ={access_file};'
    f'PWD={access_pwd};'
)

try:
    print("Conectando a la base de datos Access...")
    conn = pyodbc.connect(conn_str)
    print("Conexión a Access exitosa.")
except Exception as e:
    logging.error(f"Error conectando a Access: {e}")
    print("Verifica que el archivo exista y la contraseña sea correcta.")
    exit(1)

# 2. Consulta con JOINs y transformaciones
print("Extrayendo datos de Access...")
query = '''
SELECT
    t.IDTS as id_atencion,
    t.FECHASAL as fecha_atencion,
    t.ESPECIALIDAD as especialidad,
    t.VALORCONSULTA as valorconsulta,
    t.TOTMEDICINA as totmedicina,
    t.TIPOCONSULTA as tipoconsulta,
    t.CIE10 as cie10,
    c.DIAGNO as nomcie10,
    v.VENDEDOR as sesolicitaa,
    cli.INSTITUCION as institucion,
    cli.SEXO as genero,
    cli.FECHAN as fecha_nacimiento
FROM
    EQTRASEC t
    LEFT JOIN EQCTAVDD v ON t.CODVEN = v.CODVEN
    LEFT JOIN EQCTACLI cli ON t.CODCLI = cli.CODCLI
    LEFT JOIN EQCIE10 c ON t.CIE10 = c.CIE10
'''
if args.fecha_inicio and args.fecha_fin:
    query += f" WHERE t.FECHASAL BETWEEN #{args.fecha_inicio}# AND #{args.fecha_fin}#"

try:
    df = pd.read_sql(query, conn)
    print(f"Datos extraídos: {len(df)} filas, {len(df.columns)} columnas.")
except Exception as e:
    logging.error(f"Error ejecutando la consulta: {e}")
    print("Revisa la consulta SQL y la estructura de la base de datos.")
    conn.close()
    exit(1)
finally:
    conn.close()

# --- Validación de columnas seleccionadas ---
if args.columnas:
    columnas_seleccionadas = [col.strip() for col in args.columnas.split(',')]
    columnas_no_encontradas = [col for col in columnas_seleccionadas if col not in df.columns]
    if columnas_no_encontradas:
        print(f"Advertencia: Las siguientes columnas no existen y serán ignoradas: {columnas_no_encontradas}")
    columnas_validas = [col for col in columnas_seleccionadas if col in df.columns]
    if not columnas_validas:
        print("Error: Ninguna de las columnas seleccionadas existe en los datos. Operación cancelada.")
        exit(1)
    df = df[columnas_validas]
    print(f"Solo se migrarán las columnas: {list(df.columns)}")

# 3. Calcular edad (considerando años bisiestos)
print("Calculando edades...")
df['fecha_atencion'] = pd.to_datetime(df['fecha_atencion'], errors='coerce')
df['fecha_nacimiento'] = pd.to_datetime(df['fecha_nacimiento'], errors='coerce')
df['edad'] = df.apply(
    lambda row: row['fecha_atencion'].year - row['fecha_nacimiento'].year
    - ((row['fecha_atencion'].month, row['fecha_atencion'].day) < (row['fecha_nacimiento'].month, row['fecha_nacimiento'].day))
    if pd.notnull(row['fecha_atencion']) and pd.notnull(row['fecha_nacimiento']) else None,
    axis=1
)

for col in ['valorconsulta', 'totmedicina']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# 3.1. Validación de duplicados
print("Eliminando duplicados (si existen)...")
before = len(df)
df = df.drop_duplicates()
after = len(df)
if before != after:
    print(f"Se eliminaron {before - after} filas duplicadas.")

# 3.2. Resumen de valores nulos por columna
print("\nValores nulos por columna:")
print(df.isnull().sum())

# 3.3. Guardar log detallado en archivo
file_handler = logging.FileHandler('migracion.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)

# 4. Conexión a PostgreSQL (usar variables de entorno)
pg_user = os.getenv('PG_USER', 'postgres')
pg_pwd = os.getenv('PG_PWD', 'jossue205')
pg_host = os.getenv('PG_HOST', 'localhost')
pg_port = os.getenv('PG_PORT', '5432')
pg_db = os.getenv('PG_DB', 'parte_diario')
table_name = os.getenv('PG_TABLE', 'atencion')
engine = create_engine(f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_host}:{pg_port}/{pg_db}')

# Confirmación antes de sobrescribir
if_exists = 'replace'
if table_name in pd.read_sql("SELECT tablename FROM pg_tables WHERE schemaname='public'", engine)['tablename'].values:
    resp = input(f"La tabla '{table_name}' ya existe. ¿Deseas reemplazarla? (s/n): ")
    if resp.lower() != 's':
        print("Operación cancelada por el usuario.")
        exit(0)

# 5. Exportar a PostgreSQL
# --- Validación de datos antes de exportar ---
if df.isnull().all(axis=None):
    print("Error: Todos los valores son nulos. Operación cancelada.")
    exit(1)
if len(df) == 0:
    print("Error: No hay datos para migrar después de aplicar filtros/selección de columnas.")
    exit(1)

try:
    print("Exportando datos a PostgreSQL...")
    with pd.option_context('mode.chained_assignment', None):
        for i, chunk in enumerate(np.array_split(df, 10)):
            chunk.to_sql(table_name, engine, if_exists=if_exists if i == 0 else 'append', index=False)
            print(f"Progreso: {int((i+1)*10)}%")
    logging.info(f"¡Migración completada! Filas migradas: {len(df)}")
    print(f"¡Migración completada! Filas migradas: {len(df)}")
    print(f"Columnas migradas: {list(df.columns)}")
    
    # --- PANEL DE RESUMEN CON ESTILO ---
    resumen_html = f"""
    <div style="background: linear-gradient(90deg, #e3ffe8 0%, #f9f9f9 100%);
                border-radius: 12px; padding: 24px; margin: 24px 0; box-shadow: 0 2px 8px #0001;">
        <h2 style="color:#2b7a0b; margin-top:0;">✅ Resumen de la Migración</h2>
        <ul style="font-size:1.1em;">
            <li><b>Filas migradas:</b> {len(df)}</li>
            <li><b>Columnas:</b> {', '.join(df.columns)}</li>
        </ul>
        <h4 style="margin-bottom:4px;">Tipos de datos:</h4>
        <pre style="background:#f4f4f4; border-radius:8px; padding:8px;">{df.dtypes.to_string()}</pre>
    """

    if 'valorconsulta' in df.columns:
        resumen_html += f"<p><b>Total valorconsulta:</b> {df['valorconsulta'].sum():,.2f}</p>"
    if 'totmedicina' in df.columns:
        resumen_html += f"<p><b>Total totmedicina:</b> {df['totmedicina'].sum():,.2f}</p>"
    if 'edad' in df.columns:
        resumen_html += (
            f"<p><b>Edad mínima:</b> {df['edad'].min()}, "
            f"<b>máxima:</b> {df['edad'].max()}, "
            f"<b>promedio:</b> {df['edad'].mean():.2f}</p>"
        )
    resumen_html += "<h4>Primeras 3 filas de datos:</h4>"
    resumen_html += f"<pre style='background:#f4f4f4; border-radius:8px; padding:8px;'>{df.head(3).to_string(index=False)}</pre>"
    resumen_html += "</div>"

    # --- Exportar resumen visual a HTML ---
    resumen_path = "resumen_migracion.html"
    with open(resumen_path, "w", encoding="utf-8") as f:
        f.write(resumen_html)
    print(f"Resumen visual guardado en {resumen_path}")

    # --- Mostrar tiempo total ---
    elapsed = time.time() - start_time
    print(f"Tiempo total de ejecución: {elapsed:.2f} segundos")

    # --- Exportar a Excel si se solicita ---
    if args.excel:
        excel_path = "migracion_atencion.xlsx"
        df.to_excel(excel_path, index=False)
        print(f"Datos exportados también a {excel_path}")

except Exception as e:
    logging.error(f"Error exportando a PostgreSQL: {e}")
    print("Verifica la conexión y permisos en PostgreSQL.")

# --- Notificación sonora al finalizar (Windows y multiplataforma) ---
try:
    import winsound
    winsound.MessageBeep()
except ImportError:
    try:
        import os
        os.system('echo -e "\a"')
    except Exception:
        pass

# --- Exportar resumen a Excel ---
try:
    resumen_excel_path = "resumen_migracion.xlsx"
    with pd.ExcelWriter(resumen_excel_path) as writer:
        df.head(100).to_excel(writer, sheet_name="PrimerasFilas", index=False)
        stats = {
            "Filas migradas": [len(df)],
            "Columnas": [', '.join(df.columns)],
            "Tipos de datos": [df.dtypes.astype(str).to_dict()],
            "Total valorconsulta": [df['valorconsulta'].sum() if 'valorconsulta' in df.columns else None],
            "Total totmedicina": [df['totmedicina'].sum() if 'totmedicina' in df.columns else None],
            "Edad mínima": [df['edad'].min() if 'edad' in df.columns else None],
            "Edad máxima": [df['edad'].max() if 'edad' in df.columns else None],
            "Edad promedio": [df['edad'].mean() if 'edad' in df.columns else None],
        }
        pd.DataFrame(stats).T.rename(columns={0: "Valor"}).to_excel(writer, sheet_name="Resumen", header=True)
    print(f"Resumen y primeras filas exportados a {resumen_excel_path}")
    print("Para descargar el archivo, simplemente busca 'resumen_migracion.xlsx' en la carpeta del script y ábrelo con Excel.")
    print("Si deseas que el usuario descargue el archivo desde una interfaz web, usa Streamlit o una app web.")
    print("Por ejemplo, en Streamlit puedes usar st.download_button para permitir la descarga directa.")
except Exception as e:
    print(f"Error exportando resumen a Excel: {e}")

# --- Estadísticas adicionales y validaciones avanzadas ---
def print_advanced_stats(df):
    print("\n--- Estadísticas avanzadas ---")
    print(f"Filas únicas por especialidad: {df['especialidad'].nunique() if 'especialidad' in df.columns else 'N/A'}")
    if 'valorconsulta' in df.columns:
        print(f"Valor consulta - min: {df['valorconsulta'].min()}, max: {df['valorconsulta'].max()}, promedio: {df['valorconsulta'].mean():.2f}")
    if 'totmedicina' in df.columns:
        print(f"Valor medicina - min: {df['totmedicina'].min()}, max: {df['totmedicina'].max()}, promedio: {df['totmedicina'].mean():.2f}")
    if 'edad' in df.columns:
        print(f"Edades - min: {df['edad'].min()}, max: {df['edad'].max()}, promedio: {df['edad'].mean():.2f}")
    if 'genero' in df.columns:
        print("Distribución por género:")
        print(df['genero'].value_counts(dropna=False))
    if 'institucion' in df.columns:
        print("Top 5 instituciones:")
        print(df['institucion'].value_counts(dropna=False).head(5))
    print("--- Fin estadísticas avanzadas ---\n")

try:
    # ...existing code for export...
    print_advanced_stats(df)

    # --- Gráficos de pastel ---
    def save_pie_chart(series, title, filename):
        plt.figure(figsize=(6, 6))
        series = series.dropna()
        if series.empty:
            print(f"No hay datos para el gráfico de {title}.")
            return
        series.value_counts().plot.pie(autopct='%1.1f%%', startangle=90, shadow=True)
        plt.title(title)
        plt.ylabel('')
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()
        print(f"Gráfico de pastel '{title}' guardado como {filename}")

    if 'genero' in df.columns:
        save_pie_chart(df['genero'], "Distribución por Género", "pastel_genero.png")
    if 'institucion' in df.columns:
        save_pie_chart(df['institucion'], "Distribución por Institución", "pastel_institucion.png")
    if 'especialidad' in df.columns:
        top_especialidades = df['especialidad'].value_counts().head(8)
        save_pie_chart(top_especialidades, "Top 8 Especialidades", "pastel_especialidad.png")
    if 'rango_edad' in df.columns:
        save_pie_chart(df['rango_edad'], "Distribución por Rango de Edad", "pastel_rango_edad.png")
    elif 'edad' in df.columns:
        # Crear rangos de edad si no existen
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
        df['rango_edad'] = df['edad'].apply(clasificar_edad)
        save_pie_chart(df['rango_edad'], "Distribución por Rango de Edad", "pastel_rango_edad.png")

    # ...existing code...
except Exception as e:
    # ...existing code...

# --- Guardar estadísticas avanzadas en el Excel de resumen ---
try:
    resumen_excel_path = "resumen_migracion.xlsx"
    with pd.ExcelWriter(resumen_excel_path, mode='a', if_sheet_exists='replace') as writer:
        # ...existing code for PrimerasFilas y Resumen...
        # Nueva hoja: Estadísticas avanzadas
        stats_adv = []
        if 'especialidad' in df.columns:
            stats_adv.append(['Especialidades únicas', df['especialidad'].nunique()])
        if 'valorconsulta' in df.columns:
            stats_adv.append(['Valor consulta min', df['valorconsulta'].min()])
            stats_adv.append(['Valor consulta max', df['valorconsulta'].max()])
            stats_adv.append(['Valor consulta promedio', df['valorconsulta'].mean()])
        if 'totmedicina' in df.columns:
            stats_adv.append(['Valor medicina min', df['totmedicina'].min()])
            stats_adv.append(['Valor medicina max', df['totmedicina'].max()])
            stats_adv.append(['Valor medicina promedio', df['totmedicina'].mean()])
        if 'edad' in df.columns:
            stats_adv.append(['Edad min', df['edad'].min()])
            stats_adv.append(['Edad max', df['edad'].max()])
            stats_adv.append(['Edad promedio', df['edad'].mean()])
        if 'genero' in df.columns:
            genero_counts = df['genero'].value_counts(dropna=False)
            for g, c in genero_counts.items():
                stats_adv.append([f'Cantidad género {g}', c])
        if 'institucion' in df.columns:
            inst_counts = df['institucion'].value_counts(dropna=False).head(5)
            for i, c in inst_counts.items():
                stats_adv.append([f'Top institución {i}', c])
        if stats_adv:
            pd.DataFrame(stats_adv, columns=["Estadística", "Valor"]).to_excel(writer, sheet_name="EstadísticasAvanzadas", index=False)
    print("Estadísticas avanzadas agregadas al resumen Excel.")
except Exception as e:
    print(f"Error guardando estadísticas avanzadas en Excel: {e}")
