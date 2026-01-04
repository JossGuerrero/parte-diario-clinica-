
import os
import pyodbc
import pandas as pd

access_file = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
access_pwd = os.getenv('ACCESS_PWD', 'NeoAvanEcu22')
conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    f'DBQ={access_file};'
    f'PWD={access_pwd};'
)

conn = pyodbc.connect(conn_str)

tablas = ['EQTRASEC', 'EQCTAVDD', 'EQCTACLI', 'EQCIE10']
for tabla in tablas:
    print(f"\n--- Columnas de {tabla} ---")
    cursor = conn.execute(f"SELECT * FROM {tabla} WHERE 1=0")
    cols = [column[0] for column in cursor.description]
    print(cols)

# Pruebas de JOINs mínimos
print("\n--- Pruebas de JOINs mínimos ---")
try:
    print("\nPrueba 1: SELECT t.IDTS FROM EQTRASEC AS t;")
    df = pd.read_sql("SELECT t.IDTS FROM EQTRASEC AS t", conn)
    print(df.head())
except Exception as e:
    print(f"Error: {e}")

try:
    print("\nPrueba 2: SELECT t.IDTS, v.VENDEDOR FROM EQTRASEC AS t LEFT JOIN EQCTAVDD AS v ON t.CODVEN = v.CODVEN;")
    df = pd.read_sql("SELECT t.IDTS, v.VENDEDOR FROM EQTRASEC AS t LEFT JOIN EQCTAVDD AS v ON t.CODVEN = v.CODVEN", conn)
    print(df.head())
except Exception as e:
    print(f"Error: {e}")

try:
    print("\nPrueba 3: SELECT t.IDTS, cli.SEXO FROM EQTRASEC AS t LEFT JOIN EQCTACLI AS cli ON t.CODCLI = cli.CODCLI;")
    df = pd.read_sql("SELECT t.IDTS, cli.SEXO FROM EQTRASEC AS t LEFT JOIN EQCTACLI AS cli ON t.CODCLI = cli.CODCLI", conn)
    print(df.head())
except Exception as e:
    print(f"Error: {e}")

try:
    print("\nPrueba 4: SELECT t.IDTS, c.DIAGNO FROM EQTRASEC AS t LEFT JOIN EQCIE10 AS c ON t.CIE10 = c.CIE10;")
    df = pd.read_sql("SELECT t.IDTS, c.DIAGNO FROM EQTRASEC AS t LEFT JOIN EQCIE10 AS c ON t.CIE10 = c.CIE10", conn)
    print(df.head())
except Exception as e:
    print(f"Error: {e}")

conn.close()