
# reparar_atenciones.py
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)

conn = psycopg2.connect(
    dbname="partes_diarios",
    user="postgres",
    password="jossue205",
    host="localhost"
)
cur = conn.cursor()

# 1. Encontrar atenciones sin tipo_consulta
cur.execute("""
    SELECT COUNT(*) FROM atencion 
    WHERE tipo_consulta_id IS NULL
""")
sin_tipo = cur.fetchone()[0]
logging.info(f"Atenciones sin tipo_consulta: {sin_tipo}")

# 2. Asignar tipo_consulta por defecto (primero disponible)
if sin_tipo > 0:
    cur.execute("""
        UPDATE atencion 
        SET tipo_consulta_id = (SELECT id FROM tipo_consulta LIMIT 1)
        WHERE tipo_consulta_id IS NULL
    """)
    conn.commit()
    logging.info(f"✅ Reparadas {cur.rowcount} atenciones")

# 3. Verificar integridad
cur.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN medico_id IS NULL THEN 1 END) as sin_medico,
        COUNT(CASE WHEN tipo_consulta_id IS NULL THEN 1 END) as sin_tipo,
        COUNT(CASE WHEN paciente_id IS NULL THEN 1 END) as sin_paciente,
        COUNT(CASE WHEN cie10_id IS NULL THEN 1 END) as sin_cie10
    FROM atencion
""")
total, sin_medico, sin_tipo, sin_paciente, sin_cie10 = cur.fetchone()

logging.info(f"""
    📊 ESTADO ATENCIONES:
    Total: {total}
    Sin médico: {sin_medico}
    Sin tipo consulta: {sin_tipo}
    Sin paciente: {sin_paciente}
    Sin CIE10: {sin_cie10}
""")

cur.close()
conn.close()