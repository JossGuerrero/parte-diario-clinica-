# --- migrar_access_postgres.py LIMPIO Y ROBUSTO ---

import os
import logging
import pyodbc
import pandas as pd
from sqlalchemy import create_engine
import time

# ---------------- CONFIG ----------------
ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_URL = "postgresql+psycopg2://postgres:jossue205@localhost:5432/partes_diario"
PG_TABLE = "atencion"

logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")

# ---------------- QUERY ACCESS (BLINDADA) ----------------
query = (
    "SELECT "
    " t.[IdTs] AS id_atencion,"
    " t.[FechaSal] AS fecha_atencion,"
    " t.[descrip] AS tipo_consulta,"
    " t.[Cie10] AS cie10,"
    " e.[DIAGNO] AS nomcie10,"
    " v.[VENDEDOR] AS medico,"
    " cli.[CodCli] AS codcli,"
    " cli.[SEXO] AS genero,"
    " cli.[FechaN] AS fecha_nacimiento,"
    " q.[tot_fac] AS valorconsulta,"
    " r.[tot_ren] AS totmedicina "
    "FROM ((((EQTRASEC AS t "
    "LEFT JOIN EQCTACLI AS cli ON t.[CodCli] = cli.[CodCli]) "
    "LEFT JOIN EQCTAVDD AS v ON t.[CodVen] = v.[CODVEN]) "
    "LEFT JOIN EQCIE10 AS e ON t.[Cie10] = e.[CIE10]) "
    "LEFT JOIN EQENCPTO AS q ON t.[CodCli] = q.[CodCli]) "
    "LEFT JOIN EQRENREQ AS r ON t.[CodCli] = r.[CodCli] "
)

try:
    print("🚀 Leyendo Access (SOLO LECTURA)...")
    start = time.time()

    conn = pyodbc.connect(
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};"
    )

    df = pd.read_sql(query, conn)
    conn.close()

    print(f"✅ Filas leídas: {len(df)}")

    # ---------------- LIMPIEZA ----------------
    df["fecha_atencion"] = pd.to_datetime(df["fecha_atencion"], errors="coerce")
    df["fecha_nacimiento"] = pd.to_datetime(df["fecha_nacimiento"], errors="coerce")

    df["edad"] = df["fecha_atencion"].dt.year - df["fecha_nacimiento"].dt.year

    # ---------------- POSTGRES ----------------
    engine = create_engine(PG_URL)
    df.to_sql(PG_TABLE, engine, if_exists="replace", index=False)

    print(f"✨ Tabla '{PG_TABLE}' creada correctamente")
    print(f"⏱ Tiempo: {time.time() - start:.2f}s")

except Exception as e:
    logging.error(f"❌ ERROR: {e}", exc_info=True)