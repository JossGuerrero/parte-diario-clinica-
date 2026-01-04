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
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    pg_cur = pg_conn.cursor()

    logging.info("🚀 Migrando TIPO_CONSULTA desde EqEncPto...")

    # =========================
    # EXTRACCIÓN ACCESS (SOLO EqEncPto)
    # =========================
    acc_cur.execute("""
        SELECT DISTINCT
            [detalle],
            [detalle2],
            [base_b]
        FROM EqEncPto
        WHERE [detalle] IS NOT NULL
    """)

    rows = acc_cur.fetchall()
    logging.info(f"✅ Registros encontrados: {len(rows)}")

    # =========================
    # INSERCIÓN POSTGRES
    # =========================
    for detalle, detalle2, base_b in rows:
        nombre = detalle.strip()
        descripcion = detalle2.strip() if detalle2 else None
        valor_base = float(base_b) if base_b else None

        pg_cur.execute("""
            INSERT INTO tipo_consulta (nombre, descripcion, valor_base)
            VALUES (%s, %s, %s)
            ON CONFLICT (nombre) DO NOTHING
        """, (nombre, descripcion, valor_base))

    pg_conn.commit()
    logging.info("✅ MIGRACIÓN TIPO_CONSULTA COMPLETADA")

except Exception as e:
    logging.error(f"❌ Error durante la migración: {e}", exc_info=True)
    if 'pg_conn' in locals():
        pg_conn.rollback()

finally:
    if 'acc_cur' in locals():
        acc_cur.close()
    if 'acc_conn' in locals():
        acc_conn.close()
    if 'pg_cur' in locals():
        pg_cur.close()
    if 'pg_conn' in locals():
        pg_conn.close()
