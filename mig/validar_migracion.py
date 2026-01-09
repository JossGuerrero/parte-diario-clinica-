# validar_migracion.py - VERSIÓN SIMPLIFICADA Y CORREGIDA
import psycopg2

def validar_migracion():
    try:
        conn = psycopg2.connect(
            dbname="partes_diarios",
            user="postgres",
            password="jossue205",
            host="localhost"
        )
        cur = conn.cursor()

        print("=" * 50)
        print("VALIDACIÓN COMPLETA DE MIGRACIÓN")
        print("=" * 50)

        # 1. Verificar tablas y conteos
        print("\n1. TABLAS Y CONTEOS:")
        print("-" * 50)
        
        # Lista de todas las tablas que deberías tener
        tablas = [
            "atencion", "atencion_temporal", "cie10", "codcli_mapping",
            "control_migracion", "institucion", "medico", "migracion_control",
            "paciente", "se_solicita_a", "sync_log", "tipo_consulta"
        ]
        
        for tabla in tablas:
            try:
                # Verificar si la tabla existe
                cur.execute(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '{tabla}')")
                existe = cur.fetchone()[0]
                
                if existe:
                    # Contar registros
                    cur.execute(f"SELECT COUNT(*) FROM {tabla}")
                    conteo = cur.fetchone()[0]
                    conteo = conteo if conteo is not None else 0
                    
                    estado = "✅ OK" if conteo > 0 else "❌ VACÍA"
                    print(f"{tabla:25} | {conteo:6} registros | {estado}")
                else:
                    print(f"{tabla:25} | NO EXISTE | ❌ FALTANTE")
                    
            except Exception as e:
                print(f"{tabla:25} | ERROR: {str(e)[:40]}")

        print("\n" + "=" * 50)
        print("2. RELACIONES ENTRE TABLAS:")
        print("=" * 50)

        # 2. Verificar integridad de relaciones
        verificaciones = [
            ("Atenciones con paciente", "atencion", "paciente_id", "paciente"),
            ("Atenciones con médico", "atencion", "medico_id", "medico"),
            ("Atenciones con CIE10", "atencion", "cie10_id", "cie10"),
            ("Atenciones con tipo consulta", "atencion", "tipo_consulta_id", "tipo_consulta"),
            ("Atenciones con se_solicita_a", "atencion", "se_solicita_a_id", "se_solicita_a"),
            ("Pacientes con institución", "paciente", "institucion_id", "institucion")
        ]

        for nombre, tabla, columna, tabla_ref in verificaciones:
            try:
                # Verificar si ambas tablas existen
                cur.execute(f"""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = '{tabla}'
                    ) AND EXISTS(
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = '{tabla_ref}'
                    )
                """)
                
                if not cur.fetchone()[0]:
                    print(f"{nombre:35} | ❌ Tabla(s) no existe(n)")
                    continue
                
                # Verificar relaciones rotas
                cur.execute(f"""
                    SELECT COUNT(*) 
                    FROM {tabla} a 
                    WHERE a.{columna} IS NOT NULL 
                    AND a.{columna} NOT IN (SELECT id FROM {tabla_ref})
                """)
                
                problemas = cur.fetchone()[0] or 0
                estado = "✅ OK" if problemas == 0 else f"❌ {problemas} problemas"
                print(f"{nombre:35} | {estado}")
                
            except Exception as e:
                print(f"{nombre:35} | ❌ Error: {str(e)[:40]}")

        print("\n" + "=" * 50)
        print("3. DATOS CRÍTICOS FALTANTES:")
        print("=" * 50)

        # 3. Verificar datos faltantes
        try:
            if "paciente" in tablas:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN cedula IS NULL OR cedula = '' THEN 1 END) as sin_cedula,
                        COUNT(CASE WHEN fecha_nacimiento IS NULL THEN 1 END) as sin_fecha_nac,
                        COUNT(CASE WHEN genero IS NULL OR genero = '' THEN 1 END) as sin_genero,
                        COUNT(CASE WHEN institucion_id IS NULL THEN 1 END) as sin_institucion
                    FROM paciente
                """)
                
                total, sin_cedula, sin_fecha_nac, sin_genero, sin_institucion = cur.fetchone()
                
                # Convertir None a 0
                total = total or 0
                sin_cedula = sin_cedula or 0
                sin_fecha_nac = sin_fecha_nac or 0
                sin_genero = sin_genero or 0
                sin_institucion = sin_institucion or 0
                
                if total > 0:
                    print(f"Total pacientes: {total}")
                    print(f"Sin cédula: {sin_cedula} ({sin_cedula/total*100:.1f}%)")
                    print(f"Sin fecha nacimiento: {sin_fecha_nac} ({sin_fecha_nac/total*100:.1f}%)")
                    print(f"Sin género: {sin_genero} ({sin_genero/total*100:.1f}%)")
                    print(f"Sin institución: {sin_institucion} ({sin_institucion/total*100:.1f}%)")
                else:
                    print("⚠️  Tabla paciente vacía")
            else:
                print("❌ Tabla 'paciente' no existe")
                
        except Exception as e:
            print(f"❌ Error al verificar datos: {e}")

        print("\n" + "=" * 50)
        print("4. RESUMEN ATENCIONES:")
        print("=" * 50)

        # 4. Resumen de atenciones
        try:
            if "atencion" in tablas:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN medico_id IS NULL THEN 1 END) as sin_medico,
                        COUNT(CASE WHEN tipo_consulta_id IS NULL THEN 1 END) as sin_tipo,
                        COUNT(CASE WHEN paciente_id IS NULL THEN 1 END) as sin_paciente,
                        COUNT(CASE WHEN cie10_id IS NULL THEN 1 END) as sin_cie10
                    FROM atencion
                """)
                
                resultado = cur.fetchone()
                if resultado:
                    total, sin_medico, sin_tipo, sin_paciente, sin_cie10 = resultado
                    
                    # Convertir None a 0
                    total = total or 0
                    sin_medico = sin_medico or 0
                    sin_tipo = sin_tipo or 0
                    sin_paciente = sin_paciente or 0
                    sin_cie10 = sin_cie10 or 0
                    
                    if total > 0:
                        print(f"Total atenciones: {total}")
                        print(f"Completas: {total - (sin_medico + sin_tipo + sin_paciente + sin_cie10)}")
                        print(f"Incompletas: {sin_medico + sin_tipo + sin_paciente + sin_cie10}")
                        print(f"  • Sin médico: {sin_medico}")
                        print(f"  • Sin tipo consulta: {sin_tipo}")
                        print(f"  • Sin paciente: {sin_paciente}")
                        print(f"  • Sin CIE10: {sin_cie10}")
                else:
                    print("⚠️  No se pudo obtener el resumen")
            else:
                print("❌ Tabla 'atencion' no existe")
                
        except Exception as e:
            print(f"❌ Error al verificar atenciones: {e}")

        cur.close()
        conn.close()
        print("\n" + "=" * 50)
        print("✅ Validación completada")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    validar_migracion()