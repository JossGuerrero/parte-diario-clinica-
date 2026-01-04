import pyodbc
import psycopg2
import logging

ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")

try:
    # ACCESS
    acc = pyodbc.connect(
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};"
    )
    acc_cur = acc.cursor()

    # POSTGRES
    pg = psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        host="localhost",
        port="5432"
    )
    pg_cur = pg.cursor()

    logging.info("🚀 Migrando PACIENTES desde EqCtaCli...")

    acc_cur.execute("""
        SELECT
            [nomcli],
            [cedula],
            [FechaN],
            [genero],
            [telefono],
            [DIRECCION]
        FROM EqCtaCli
        WHERE [cedula] IS NOT NULL
    """)

    rows = acc_cur.fetchall()
    logging.info(f"✅ Registros encontrados: {len(rows)}")

    for r in rows:
        nombre, cedula, fecha_n, genero, telefono, direccion = r

        pg_cur.execute("""
            INSERT INTO paciente
            (nombre, cedula, fecha_nacimiento, genero, telefono, direccion)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (cedula) DO NOTHING
        """, (
            nombre.strip() if nombre else None,
            str(cedula).strip(),
            fecha_n,
            genero.strip() if genero else None,
            telefono.strip() if telefono else None,
            direccion.strip() if direccion else None
        ))

    pg.commit()
    logging.info("✅ PACIENTES MIGRADOS CORRECTAMENTE")

except Exception as e:
    logging.error(f"❌ Error: {e}", exc_info=True)
    pg.rollback()

finally:
    acc_cur.close()
    acc.close()
    pg_cur.close()
    pg.close()
