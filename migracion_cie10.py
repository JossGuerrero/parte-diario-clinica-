import pyodbc
import psycopg2
import logging

ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")

try:
    # ---------- ACCESS ----------
    access_conn = pyodbc.connect(
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};"
    )
    access_cursor = access_conn.cursor()

    # ---------- POSTGRES ----------
    pg_conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    pg_cursor = pg_conn.cursor()

    logging.info("🚀 Migrando CIE10 (SOLO registros válidos)...")

    access_cursor.execute("""
        SELECT CIE10, DIAGNO
        FROM EqCIE10
        WHERE CIE10 IS NOT NULL
          AND TRIM(CIE10) <> ''
          AND DIAGNO IS NOT NULL
    """)

    rows = access_cursor.fetchall()
    logging.info(f"✅ Registros válidos encontrados: {len(rows)}")

    for codigo, descripcion in rows:
        pg_cursor.execute(
            """
            INSERT INTO cie10 (codigo, descripcion)
            VALUES (%s, %s)
            ON CONFLICT (codigo) DO NOTHING
            """,
            (codigo.strip(), descripcion.strip())
        )

    pg_conn.commit()
    logging.info("✅ Migración CIE10 FINALIZADA SIN ERRORES")

except Exception as e:
    logging.error(f"❌ Error durante la migración: {e}", exc_info=True)
    if 'pg_conn' in locals():
        pg_conn.rollback()

finally:
    if 'access_cursor' in locals():
        access_cursor.close()
    if 'access_conn' in locals():
        access_conn.close()
    if 'pg_cursor' in locals():
        pg_cursor.close()
    if 'pg_conn' in locals():
        pg_conn.close()
