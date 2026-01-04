import unittest
import os
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date

# Configuración de conexión (igual que en app.py)
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASS = os.getenv("PG_PWD", "jossue205")
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = os.getenv("PG_PORT", "5432")
DB_NAME = os.getenv("PG_DB", "parte_diario")
engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

class TestParteDiarioBackend(unittest.TestCase):
    def test_conexion_postgres(self):
        """Verifica conexión a PostgreSQL"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            self.assertEqual(result, 1)

    def test_tabla_atencion_existe(self):
        """Verifica que la tabla 'atencion' existe"""
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'atencion'
                )
            """)).scalar()
            self.assertTrue(result)

    def test_columnas_clave(self):
        """Verifica que las columnas clave existen en 'atencion'"""
        columnas_esperadas = {"fecha_atencion", "medico", "especialidad", "valor_consulta", "valor_medicina"}
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM atencion LIMIT 1"))
            columnas = set(result.keys())
            self.assertTrue(columnas_esperadas.issubset(columnas))

    def test_consulta_rango_fechas(self):
        """Verifica que la consulta por rango de fechas retorna un DataFrame"""
        hoy = date.today()
        inicio = hoy.replace(day=1)
        fin = hoy
        query = text("""
            SELECT fecha_atencion, especialidad, medico, valor_consulta, valor_medicina
            FROM atencion
            WHERE fecha_atencion BETWEEN :start AND :end
        """)
        df = pd.read_sql(query, engine, params={"start": inicio, "end": fin})
        self.assertIsInstance(df, pd.DataFrame)

if __name__ == "__main__":
    unittest.main()
