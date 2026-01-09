# encontrar_relacion_real.py
import pyodbc
import psycopg2

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

def encontrar_relacion():
    try:
        # Conectar
        conn_str = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={CONFIG['access']['file']};PWD={CONFIG['access']['password']}"
        acc_conn = pyodbc.connect(conn_str)
        acc_cur = acc_conn.cursor()
        
        pg_conn = psycopg2.connect(**CONFIG['postgres'])
        pg_cur = pg_conn.cursor()
        
        print("🔍 BUSCANDO RELACIÓN REAL ENTRE ACCESS Y POSTGRESQL")
        print("=" * 80)
        
        # PRIMERO: Buscar por NOMBRE (la forma más segura)
        print("\n1️⃣  BUSCANDO COINCIDENCIAS POR NOMBRE:")
        print("-" * 80)
        
        # Tomar algunos pacientes de Access y buscar por nombre en PostgreSQL
        acc_cur.execute("""
            SELECT TOP 20 
                codcli, 
                TRIM(nomcli) as nombre, 
                cedula
            FROM EqCtaCli 
            WHERE nomcli IS NOT NULL 
            ORDER BY codcli
        """)
        
        coincidencias_nombre = 0
        total_procesados = 0
        
        for codcli, nombre_access, cedula_access in acc_cur.fetchall():
            total_procesados += 1
            
            if not nombre_access:
                continue
            
            # Buscar por nombre en PostgreSQL
            nombre_buscar = nombre_access.strip()
            
            # Intentar varias formas de búsqueda
            pg_cur.execute("""
                SELECT id, cedula, nombre 
                FROM paciente 
                WHERE nombre ILIKE %s 
                LIMIT 3
            """, (f"%{nombre_buscar}%",))
            
            resultados = pg_cur.fetchall()
            
            if resultados:
                coincidencias_nombre += 1
                print(f"\n✅ Código Access: {codcli}, Nombre: '{nombre_buscar}'")
                print(f"   Cédula Access: {cedula_access}")
                print(f"   Coincidencias PostgreSQL:")
                for id_pg, cedula_pg, nombre_pg in resultados:
                    print(f"      • ID: {id_pg}, Cédula: {cedula_pg}, Nombre: {nombre_pg}")
            else:
                # Si no encuentra, mostrar para diagnóstico
                if total_procesados <= 5:  # Solo primeros 5 para no saturar
                    print(f"\n❌ Código Access: {codcli}, Nombre: '{nombre_buscar}'")
                    print(f"   Cédula Access: {cedula_access}")
                    print(f"   NO encontrado en PostgreSQL")
        
        print(f"\n📊 Coincidencias por nombre: {coincidencias_nombre}/{total_procesados}")
        
        # SEGUNDO: Verificar si hay una tabla de mapeo o relación
        print("\n2️⃣  BUSCANDO TABLAS DE MAPEO EN ACCESS:")
        print("-" * 80)
        
        try:
            # Listar tablas que podrían tener mapeo
            acc_cur.execute("""
                SELECT Name 
                FROM MSysObjects 
                WHERE Type=1 AND Flags=0 
                AND (Name LIKE '%map%' OR Name LIKE '%rel%' OR Name LIKE '%cod%')
            """)
            
            tablas_mapeo = acc_cur.fetchall()
            if tablas_mapeo:
                print("Tablas potenciales de mapeo encontradas:")
                for tabla in tablas_mapeo:
                    print(f"   • {tabla[0]}")
            else:
                print("No se encontraron tablas con nombres de mapeo")
        except:
            print("No se pueden listar tablas del sistema")
        
        # TERCERO: Analizar pacientes con más atenciones
        print("\n3️⃣  PACIENTES CON MÁS ATENCIONES EN ACCESS:")
        print("-" * 80)
        
        acc_cur.execute("""
            SELECT TOP 5 
                CodCli, 
                COUNT(*) as atenciones
            FROM EqTraSec 
            WHERE CodCli IS NOT NULL
            GROUP BY CodCli
            ORDER BY atenciones DESC
        """)
        
        for codcli, atenciones in acc_cur.fetchall():
            codcli_str = str(codcli).strip() if codcli else ""
            
            # Buscar información completa del paciente en Access
            acc_cur.execute("""
                SELECT nomcli, cedula 
                FROM EqCtaCli 
                WHERE codcli = ?
            """, (codcli_str,))
            
            paciente_info = acc_cur.fetchone()
            nombre_acc = paciente_info[0] if paciente_info else "N/A"
            cedula_acc = paciente_info[1] if paciente_info else "N/A"
            
            print(f"\n📊 Código: {codcli_str}")
            print(f"   Atenciones: {atenciones}")
            print(f"   Nombre Access: {nombre_acc}")
            print(f"   Cédula Access: {cedula_acc}")
            
            # Buscar en PostgreSQL por nombre
            if nombre_acc:
                pg_cur.execute("""
                    SELECT id, cedula, nombre 
                    FROM paciente 
                    WHERE nombre ILIKE %s
                    LIMIT 2
                """, (f"%{nombre_acc}%",))
                
                resultados_pg = pg_cur.fetchall()
                if resultados_pg:
                    print(f"   🔍 Posibles coincidencias PostgreSQL:")
                    for id_pg, cedula_pg, nombre_pg in resultados_pg:
                        print(f"      • ID: {id_pg}, Cédula: {cedula_pg}")
                else:
                    print(f"   ❌ No encontrado en PostgreSQL")
        
        # CUARTO: Recomendación final
        print("\n" + "=" * 80)
        print("🎯 RECOMENDACIÓN FINAL:")
        print("=" * 80)
        
        if coincidencias_nombre > 0:
            print(f"✅ ENCONTRADAS {coincidencias_nombre} COINCIDENCIAS POR NOMBRE")
            print("\nSOLUCIÓN: Usar el NOMBRE como puente para el mapeo")
            print("   1. Buscar paciente en PostgreSQL por nombre (LIKE)")
            print("   2. Si hay coincidencia única, usar esa relación")
            print("   3. Si hay múltiples, pedir selección manual")
        else:
            print("❌ NO SE ENCONTRARON COINCIDENCIAS CLARAS")
            print("\nSOLUCIÓN:")
            print("   1. Revisar manualmente los datos")
            print("   2. Buscar documentación del sistema Access")
            print("   3. Preguntar al administrador original")
        
        print("\n¿Deseas intentar mapeo automático por nombre? (s/n)")
        
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
    encontrar_relacion()