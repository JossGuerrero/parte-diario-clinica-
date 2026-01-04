import pyodbc
import psycopg2
import logging

# ================== CONFIG ==================
ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"
# ============================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")

try:
    # ---------- CONEXIONES ----------
    access_conn = pyodbc.connect(
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};"
    )
    access_cursor = access_conn.cursor()

    pg_conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )
    pg_cursor = pg_conn.cursor()

    logging.info("🚀 Migrando PACIENTES...")

    # ---------- SELECT ACCESS (CORRECTO) ----------
    access_cursor.execute("""
        SELECT DISTINCT
            [HCL],
            [CEDULA],
            [NOMBRE],
            [SEXO],
            [FECHANAC],
            [DIRECCION],
            [TELEFONO]
        FROM [EQCTACLI]
        WHERE [CEDULA] IS NOT NULL
    """)

    rows = access_cursor.fetchall()
    logging.info(f"✅ Pacientes encontrados: {len(rows)}")

    # ---------- INSERT POSTGRES ----------
    for row in rows:
        hcl, cedula, nombre, sexo, fecha_nac, direccion, telefono = row

        pg_cursor.execute("""
            INSERT INTO paciente (
                hcl,
                cedula,
                nombre,
                sexo,
                fecha_nacimiento,
                direccion,
                telefono
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cedula) DO NOTHING
        """, (
            str(hcl).strip() if hcl else None,
            str(cedula).strip(),
            nombre.strip() if nombre else None,
            sexo.strip() if sexo else None,
            fecha_nac,
            direccion.strip() if direccion else None,
            telefono.strip() if telefono else None
        ))

    pg_conn.commit()
    logging.info("✅ MIGRACIÓN DE PACIENTES COMPLETADA")

except Exception as e:
    logging.error(f"❌ Error: {e}", exc_info=True)
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
