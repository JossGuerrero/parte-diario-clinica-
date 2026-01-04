import pyodbc
import psycopg2
import logging

# =========================
# CONFIGURACIÓN
# =========================
ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")

try:
    # =========================
    # CONEXIÓN ACCESS
    # =========================
    acc_conn = pyodbc.connect(
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};"
    )
    acc_cur = acc_conn.cursor()

    # =========================
    # CONEXIÓN POSTGRES
    # =========================
    pg_conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS
    )
    pg_cur = pg_conn.cursor()

    # =========================
    # 1. LLENAR TABLA INSTITUCION
    # =========================
    logging.info("🚀 Extrayendo nombres de instituciones de EqTraSec.[Grupo2]...")
    
    acc_cur.execute("SELECT DISTINCT [Grupo2] FROM EqTraSec WHERE [Grupo2] IS NOT NULL")
    rows_inst = acc_cur.fetchall()
    
    for (grupo2,) in rows_inst:
        nombre_inst = grupo2.strip()
        if nombre_inst:
            pg_cur.execute("""
                INSERT INTO institucion (nombre, activo)
                VALUES (%s, True)
                ON CONFLICT (nombre) DO NOTHING
            """, (nombre_inst,))
    
    pg_conn.commit()
    logging.info("✅ Tabla 'institucion' poblada.")

    # =========================
    # 2. VINCULAR PACIENTES (institucion_id)
    # =========================
    logging.info("🔄 Actualizando institucion_id en la tabla paciente...")

    # Necesitamos saber qué institución (Grupo2) tiene cada paciente (cedula)
    # Unimos EqTraSec con EqCtaCli en Access para obtener la relación
    query_vinculo = """
        SELECT DISTINCT C.cedula, T.Grupo2
        FROM EqTraSec AS T
        INNER JOIN EqCtaCli AS C ON T.CodCli = C.CodCli
        WHERE T.Grupo2 IS NOT NULL AND C.cedula IS NOT NULL
    """
    acc_cur.execute(query_vinculo)
    vinculos = acc_cur.fetchall()

    actualizados = 0
    for cedula, nombre_inst in vinculos:
        c_cedula = cedula.strip()
        c_inst = nombre_inst.strip()

        # Buscamos el ID generado en la tabla institucion y lo ponemos en paciente
        pg_cur.execute("""
            UPDATE paciente 
            SET institucion_id = (SELECT id FROM institucion WHERE nombre = %s)
            WHERE cedula = %s
        """, (c_inst, c_cedula))
        actualizados += pg_cur.rowcount

    pg_conn.commit()
    logging.info(f"✅ Se actualizaron {actualizados} pacientes con su institucion_id.")

except Exception as e:
    logging.error(f"❌ Error: {e}", exc_info=True)
    if 'pg_conn' in locals(): pg_conn.rollback()
finally:
    if 'acc_cur' in locals(): acc_cur.close()
    if 'acc_conn' in locals(): acc_conn.close()
    if 'pg_cur' in locals(): pg_cur.close()
    if 'pg_conn' in locals(): pg_conn.close()