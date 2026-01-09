# investigacion_problema.py
import pyodbc
import psycopg2
import re

CONFIG = {
    "access": {
        "file": r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb",
        "password": "NeoAvanEcu22"
    },
    "postgres": {
        "dbname": "partes_diarios",
        "user": "postgres",
        "password": "jossue205",
        "host": "localhost",
        "port": "5432"
    }
}

def investigar():
    try:
        # Conectar
        conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={CONFIG['access']['file']};PWD={CONFIG['access']['password']}"
        acc_conn = pyodbc.connect(conn_str)
        acc_cur = acc_conn.cursor()
        
        pg_conn = psycopg2.connect(**CONFIG['postgres'])
        pg_cur = pg_conn.cursor()
        
        print("🔍 INVESTIGACIÓN PROFUNDA DEL PROBLEMA")
        print("=" * 80)
        
        # 1. MOSTRAR EJEMPLOS REALES DE ACCESS
        print("\n📋 EJEMPLOS REALES DE ACCESS (EqCtaCli):")
        print("   " + "-" * 80)
        acc_cur.execute("""
            SELECT TOP 10 
                codcli, 
                cedula,
                nomcli,
                LEN(codcli) as len_codcli,
                LEN(cedula) as len_cedula
            FROM EqCtaCli 
            WHERE codcli IS NOT NULL
        """)
        
        print(f"{'Código':<15} | {'Cédula':<15} | {'Long Cód':<8} | {'Long Céd':<8} | {'Nombre'}")
        print("-" * 80)
        for row in acc_cur.fetchall():
            codcli, cedula, nombre, len_c, len_ced = row
            print(f"{str(codcli):<15} | {str(cedula):<15} | {len_c:<8} | {len_ced:<8} | {nombre[:20]}")
        
        # 2. MOSTRAR EJEMPLOS DE POSTGRESQL
        print("\n📋 EJEMPLOS REALES DE POSTGRESQL (paciente):")
        print("   " + "-" * 80)
        pg_cur.execute("""
            SELECT cedula, nombre, LENGTH(cedula) as len_cedula
            FROM paciente 
            WHERE cedula IS NOT NULL 
            LIMIT 10
        """)
        
        print(f"{'Cédula':<20} | {'Longitud':<8} | {'Nombre'}")
        print("-" * 80)
        for row in pg_cur.fetchall():
            cedula, nombre, longitud = row
            print(f"{str(cedula):<20} | {longitud:<8} | {nombre[:30]}")
        
        # 3. BUSCAR ALGUNAS COINCIDENCIAS MANUALMENTE
        print("\n🔍 BUSCANDO COINCIDENCIAS MANUALES:")
        print("   " + "-" * 80)
        
        # Tomar algunos códigos de Access y buscar en PostgreSQL
        acc_cur.execute("SELECT TOP 5 codcli, cedula FROM EqCtaCli WHERE codcli IS NOT NULL")
        test_cases = acc_cur.fetchall()
        
        for codcli, cedula_access in test_cases:
            codcli_str = str(codcli).strip() if codcli else ""
            cedula_acc = str(cedula_access).strip() if cedula_access else ""
            
            print(f"\n   Búsqueda para código Access: '{codcli_str}' (cédula Access: '{cedula_acc}')")
            
            # Estrategia 1: Buscar exacto por cédula de Access
            if cedula_acc:
                pg_cur.execute("SELECT cedula, nombre FROM paciente WHERE cedula = %s", (cedula_acc,))
                resultados = pg_cur.fetchall()
                if resultados:
                    for cedula_pg, nombre in resultados:
                        print(f"      ✅ POR CÉDULA EXACTA: '{cedula_pg}' - {nombre}")
            
            # Estrategia 2: Buscar código como cédula
            if codcli_str:
                pg_cur.execute("SELECT cedula, nombre FROM paciente WHERE cedula = %s", (codcli_str,))
                resultados = pg_cur.fetchall()
                if resultados:
                    for cedula_pg, nombre in resultados:
                        print(f"      ✅ POR CÓDIGO EXACTO: '{cedula_pg}' - {nombre}")
                else:
                    # Estrategia 3: Buscar código dentro de cédula
                    pg_cur.execute("SELECT cedula, nombre FROM paciente WHERE cedula LIKE %s", (f"%{codcli_str}%",))
                    resultados = pg_cur.fetchall()
                    if resultados:
                        for cedula_pg, nombre in resultados:
                            print(f"      ⚠️  POR CÓDIGO PARCIAL: '{cedula_pg}' contiene '{codcli_str}' - {nombre}")
                    else:
                        print(f"      ❌ NO ENCONTRADO")
        
        # 4. ANALIZAR FORMATOS DE CÉDULA
        print("\n📊 ANÁLISIS DE FORMATOS DE CÉDULA:")
        print("   " + "-" * 80)
        
        # En Access
        print("\n   ACCESS - Patrones comunes en cedula:")
        acc_cur.execute("SELECT TOP 10 cedula FROM EqCtaCli WHERE cedula IS NOT NULL")
        for row in acc_cur.fetchall():
            cedula = str(row[0]).strip()
            if cedula:
                # Extraer solo números
                numeros = re.findall(r'\d+', cedula)
                if numeros:
                    print(f"      '{cedula}' → Números: {''.join(numeros)}")
        
        # En PostgreSQL
        print("\n   POSTGRESQL - Patrones comunes:")
        pg_cur.execute("""
            SELECT cedula 
            FROM paciente 
            WHERE cedula IS NOT NULL 
            AND LENGTH(cedula) <= 15
            LIMIT 10
        """)
        for row in pg_cur.fetchall():
            cedula = str(row[0])
            if cedula:
                print(f"      '{cedula}' → Longitud: {len(cedula)}")
        
        # 5. CONTAR ATENCIONES POR PACIENTE
        print("\n📊 ATENCIONES EN ACCESS POR CÓDIGO:")
        print("   " + "-" * 80)
        
        # Ver códigos con más atenciones
        acc_cur.execute("""
            SELECT TOP 10 CodCli, COUNT(*) as atenciones
            FROM EqTraSec 
            WHERE CodCli IS NOT NULL
            GROUP BY CodCli
            ORDER BY atenciones DESC
        """)
        
        print(f"{'Código':<15} | {'Atenciones':<10}")
        print("-" * 80)
        for codcli, count in acc_cur.fetchall():
            codcli_str = str(codcli).strip() if codcli else ""
            print(f"{codcli_str:<15} | {count:<10}")
            
            # Buscar este código en PostgreSQL
            if codcli_str:
                pg_cur.execute("SELECT cedula, nombre FROM paciente WHERE cedula = %s", (codcli_str,))
                resultado = pg_cur.fetchone()
                if resultado:
                    print(f"      ✅ Encontrado en PostgreSQL: {resultado[0]} - {resultado[1]}")
                else:
                    print(f"      ❌ NO encontrado")
        
        # 6. SUGERIR SOLUCIÓN
        print("\n🎯 DIAGNÓSTICO FINAL Y SOLUCIÓN:")
        print("=" * 80)
        print("PROBLEMA: Los códigos en Access no coinciden con cédulas en PostgreSQL")
        print("\nPOSIBLES CAUSAS:")
        print("   1. Access usa códigos internos (codcli) que NO son cédulas")
        print("   2. PostgreSQL tiene pacientes importados de otra fuente")
        print("   3. Hay un mapeo manual o transformación que no estamos aplicando")
        print("\nSOLUCIÓN INMEDIATA:")
        print("   Opción A: Encontrar tabla de mapeo en Access (si existe)")
        print("   Opción B: Buscar relación entre codcli y cédula dentro de EqCtaCli")
        print("   Opción C: Crear mapeo manual basado en nombre + otros datos")
        
        # Cerrar conexiones
        acc_cur.close()
        acc_conn.close()
        pg_cur.close()
        pg_conn.close()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigar()