# explorar_access.py
import pyodbc
import pandas as pd

def explorar_access():
    try:
        # Conectar a Access
        conn_str = (
            r"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
            r"DBQ={0};PWD={1};"
        ).format(
            r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb",
            "NeoAvanEcu22"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("🔍 EXPLORANDO ESTRUCTURA DE ACCESS")
        print("=" * 60)
        
        # 1. Listar todas las tablas
        print("\n📋 TABLAS EN ACCESS:")
        try:
            cursor.execute("""
                SELECT Name FROM MSysObjects 
                WHERE Type=1 AND Flags=0 
                ORDER BY Name
            """)
            tablas = cursor.fetchall()
            for tabla in tablas[:20]:  # Mostrar primeras 20
                print(f"  • {tabla[0]}")
        except:
            print("  No se pueden listar tablas del sistema")
        
        # 2. Explorar EqCtaCli (Pacientes)
        print("\n👥 ESTRUCTURA DE EqCtaCli (PACIENTES):")
        try:
            cursor.execute("SELECT TOP 1 * FROM EqCtaCli")
            columnas = [desc[0] for desc in cursor.description]
            print(f"  Campos: {columnas}")
            
            # Mostrar algunos datos
            cursor.execute("SELECT TOP 3 * FROM EqCtaCli")
            for i, row in enumerate(cursor.fetchall(), 1):
                print(f"  Ejemplo {i}: {row}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 3. Explorar EqTraSec (Atenciones)
        print("\n🏥 ESTRUCTURA DE EqTraSec (ATENCIONES):")
        try:
            cursor.execute("SELECT TOP 1 * FROM EqTraSec")
            columnas = [desc[0] for desc in cursor.description]
            print(f"  Campos: {columnas}")
            
            # Mostrar algunos datos
            cursor.execute("SELECT TOP 3 * FROM EqTraSec")
            for i, row in enumerate(cursor.fetchall(), 1):
                print(f"  Ejemplo {i}: {row}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 4. Explorar EQCTAVDD (Médicos)
        print("\n👨‍⚕️ ESTRUCTURA DE EQCTAVDD (MÉDICOS):")
        try:
            cursor.execute("SELECT TOP 1 * FROM EQCTAVDD")
            columnas = [desc[0] for desc in cursor.description]
            print(f"  Campos: {columnas}")
            
            # Mostrar algunos datos
            cursor.execute("SELECT TOP 3 * FROM EQCTAVDD")
            for i, row in enumerate(cursor.fetchall(), 1):
                print(f"  Ejemplo {i}: {row}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # 5. Contar registros
        print("\n📊 CONTEO DE REGISTROS:")
        try:
            cursor.execute("SELECT COUNT(*) FROM EqCtaCli")
            count_pac = cursor.fetchone()[0]
            print(f"  EqCtaCli (Pacientes): {count_pac:,}")
            
            cursor.execute("SELECT COUNT(*) FROM EqTraSec")
            count_ate = cursor.fetchone()[0]
            print(f"  EqTraSec (Atenciones): {count_ate:,}")
            
            cursor.execute("SELECT COUNT(*) FROM EQCTAVDD")
            count_med = cursor.fetchone()[0]
            print(f"  EQCTAVDD (Médicos): {count_med:,}")
        except Exception as e:
            print(f"  Error contando: {e}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ EXPLORACIÓN COMPLETADA")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    explorar_access()