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

    logging.info("🚀 Migrando SE_SOLICITA_A desde EQCTAVDD...")

    # =========================
    # EXTRACCIÓN ACCESS
    # =========================
    acc_cur.execute("""
        SELECT DISTINCT
            VENDEDOR
        FROM EQCTAVDD
        WHERE VENDEDOR IS NOT NULL
    """)

    rows = acc_cur.fetchall()
    logging.info(f"✅ Registros encontrados: {len(rows)}")

    # =========================
    # INSERCIÓN POSTGRES
    # =========================
    for (vendedor,) in rows:
        nombre = vendedor.strip()

        pg_cur.execute("""
            INSERT INTO se_solicita_a (nombre)
            VALUES (%s)
        """, (nombre,))

    pg_conn.commit()
    logging.info("✅ MIGRACIÓN SE_SOLICITA_A COMPLETADA")

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
