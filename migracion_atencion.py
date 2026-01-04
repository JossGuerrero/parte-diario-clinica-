import pyodbc
import psycopg2
import logging
from datetime import datetime

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

def calcular_edad(fecha_nac, fecha_atenc):
    if not fecha_nac or not fecha_atenc: return 0
    try:
        return fecha_atenc.year - fecha_nac.year - ((fecha_atenc.month, fecha_atenc.day) < (fecha_nac.month, fecha_nac.day))
    except: return 0

try:
    acc_conn = pyodbc.connect(r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};" f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};")
    acc_cur = acc_conn.cursor()

    pg_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)
    pg_cur = pg_conn.cursor()

    logging.info("🚀 Iniciando migración de ATENCIONES con columnas verificadas...")

    # SQL AJUSTADO SEGÚN TUS TABLAS
    # Nota: Usamos T.numfac para unir con E.numfac (que es lo común en estos sistemas)
    query_access = """
        SELECT 
            T.[FechaIng], 
            C.[cedula], 
            C.[genero], 
            C.[FechaN],
            T.[Cie10], 
            T.[Grupo2], 
            V.[VENDEDOR],
            T.[SEspecialidad],
            E.[base_b], 
            E.[dstvfac]
        FROM (((EqTraSec AS T
        LEFT JOIN EqCtaCli AS C ON T.[CodCli] = C.[CodCli])
        LEFT JOIN EQCTAVDD AS V ON T.[CodVen] = V.[CODVEN])
        LEFT JOIN EqEncPto AS E ON T.[numfac] = E.[numfac])
        WHERE T.[FechaIng] IS NOT NULL
    """
    
    acc_cur.execute(query_access)
    rows = acc_cur.fetchall()
    logging.info(f"📊 Registros encontrados: {len(rows)}")

    insertados = 0
    for row in rows:
        # Extraer y Limpiar
        f_atencion = row.FechaIng
        cedula_p   = str(row.cedula).strip() if row.cedula else None
        gen_p      = str(row.genero).strip()[:10] if row.genero else None
        f_nac_p    = row.FechaN
        cod_cie10  = str(row.Cie10).strip() if row.Cie10 else None
        nom_tipo   = str(row.Grupo2).strip() if row.Grupo2 else None
        nom_vend   = str(row.VENDEDOR).strip() if row.VENDEDOR else None
        especialid = str(row.SEspecialidad).strip() if row.SEspecialidad else None
        val_cons   = float(row.base_b) if row.base_b else 0.0
        val_med    = float(row.dstvfac) if row.dstvfac else 0.0

        edad_p = calcular_edad(f_nac_p, f_atencion)

        # Buscar IDs en Postgres
        pg_cur.execute("SELECT id FROM paciente WHERE cedula = %s", (cedula_p,))
        res = pg_cur.fetchone()
        paciente_id = res[0] if res else None

        pg_cur.execute("SELECT id FROM cie10 WHERE codigo = %s", (cod_cie10,))
        res = pg_cur.fetchone()
        cie10_id = res[0] if res else None

        pg_cur.execute("SELECT id FROM se_solicita_a WHERE nombre = %s", (nom_vend,))
        res = pg_cur.fetchone()
        solicita_id = res[0] if res else None

        pg_cur.execute("SELECT id FROM tipo_consulta WHERE nombre = %s", (nom_tipo,))
        res = pg_cur.fetchone()
        tipo_id = res[0] if res else None

        # Usamos vendedor como nombre de médico si no tienes tabla de médicos aparte
        pg_cur.execute("SELECT id FROM medico WHERE nombre = %s", (nom_vend,))
        res = pg_cur.fetchone()
        medico_id = res[0] if res else None

        if paciente_id:
            pg_cur.execute("""
                INSERT INTO atencion (
                    fecha_atencion, medico_id, tipo_consulta_id, 
                    se_solicita_a_id, paciente_id, cie10_id, 
                    edad, genero, valor_consulta, valor_medicina, 
                    observaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                f_atencion, medico_id, tipo_id,
                solicita_id, paciente_id, cie10_id,
                edad_p, gen_p, val_cons, val_med, especialid
            ))
            insertados += 1
        
        if insertados % 100 == 0:
            pg_conn.commit()

    pg_conn.commit()
    logging.info(f"✅ MIGRACIÓN FINALIZADA: {insertados} registros.")

except Exception as e:
    logging.error(f"❌ Error: {e}", exc_info=True)
    if 'pg_conn' in locals(): pg_conn.rollback()
finally:
    if 'acc_cur' in locals(): acc_cur.close()
    if 'acc_conn' in locals(): acc_conn.close()
    if 'pg_cur' in locals(): pg_cur.close()
    if 'pg_conn' in locals(): pg_conn.close()