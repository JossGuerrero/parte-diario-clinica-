# migracion_inicial_corregida.py
import pyodbc
import psycopg2
import logging
import re
from datetime import datetime

# ================= CONFIGURACIÓN =================
ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"
# ================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class MigradorProduccion:
    def __init__(self):
        # Conexión Access
        self.acc_conn = pyodbc.connect(
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};"
        )
        self.acc_cur = self.acc_conn.cursor()
        
        # Conexión PostgreSQL
        self.pg_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT,
            dbname=PG_DB, user=PG_USER, password=PG_PASS
        )
        self.pg_cur = self.pg_conn.cursor()
    
    def normalizar_cedula(self, cedula):
        """Extraer solo números de la cédula, máximo 10 dígitos"""
        if not cedula:
            return None
        # Convertir a string y extraer números
        numeros = re.sub(r'\D', '', str(cedula))
        # Tomar hasta 10 dígitos
        return numeros[:10] if numeros else None
    
    def crear_control_tables(self):
        """Crear tablas de control si no existen"""
        try:
            # Tabla de control principal
            self.pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS migracion_control (
                    id SERIAL PRIMARY KEY,
                    tabla_origen VARCHAR(50) NOT NULL,
                    id_origen VARCHAR(100) NOT NULL,
                    fecha_migracion TIMESTAMP DEFAULT NOW(),
                    UNIQUE(tabla_origen, id_origen)
                )
            """)
            
            # Índices para mejor performance
            self.pg_cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_control_tabla_id 
                ON migracion_control(tabla_origen, id_origen)
            """)
            
            self.pg_conn.commit()
            logging.info("Tablas de control creadas/verificadas")
            
        except Exception as e:
            logging.error(f"Error creando tablas de control: {e}")
            raise
    
    def migrar_pacientes_corregido(self):
        """MIGRACIÓN CORREGIDA DE PACIENTES - SIN FILTROS"""
        logging.info("=" * 60)
        logging.info("MIGRANDO TODOS LOS PACIENTES DESDE ACCESS")
        logging.info("=" * 60)
        
        try:
            # 1. Contar pacientes en Access
            self.acc_cur.execute("SELECT COUNT(DISTINCT CODCLI) FROM EQCTACLI WHERE CODCLI IS NOT NULL")
            total_access = self.acc_cur.fetchone()[0] or 0
            logging.info(f"Pacientes únicos en Access (CODCLI distintos): {total_access}")
            
            # 2. Obtener todos los pacientes de Access
            self.acc_cur.execute("""
                SELECT 
                    CODCLI,
                    NOMCLI,
                    CEDULA,
                    FECHAN,
                    GENERO,
                    TELEFONO,
                    DIRECCION
                FROM EQCTACLI
                WHERE CODCLI IS NOT NULL
            """)
            
            pacientes_access = self.acc_cur.fetchall()
            logging.info(f"Total registros en EQCTACLI: {len(pacientes_access)}")
            
            insertados = 0
            actualizados = 0
            errores = 0
            
            for row in pacientes_access:
                try:
                    codcli, nombre, cedula, fecha_n, genero, telefono, direccion = row
                    
                    # Normalizar cédula (CODCLI es la cédula)
                    cedula_norm = self.normalizar_cedula(codcli)
                    cedula_original = str(codcli).strip() if codcli else None
                    
                    # Si no se puede normalizar, usar el original
                    if not cedula_norm and cedula_original:
                        cedula_norm = cedula_original
                    
                    # Verificar si ya existe por CODCLI (cedula)
                    self.pg_cur.execute("""
                        SELECT id FROM paciente 
                        WHERE cedula = %s OR cedula_norm = %s
                    """, (cedula_original, cedula_norm))
                    
                    existe = self.pg_cur.fetchone()
                    
                    if existe:
                        # Ya existe, podríamos actualizar si hay cambios
                        # Por ahora solo contamos
                        actualizados += 1
                    else:
                        # Insertar nuevo paciente
                        self.pg_cur.execute("""
                            INSERT INTO paciente (
                                cedula,
                                cedula_norm,
                                nombre,
                                fecha_nacimiento,
                                genero,
                                telefono,
                                direccion,
                                activo
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                        """, (
                            cedula_original,
                            cedula_norm,
                            str(nombre).strip() if nombre else None,
                            fecha_n,
                            str(genero).strip() if genero else None,
                            str(telefono).strip() if telefono else None,
                            str(direccion).strip() if direccion else None
                        ))
                        insertados += 1
                    
                    # Registrar en control (aunque sea duplicado, para saber que existe)
                    if cedula_original:
                        self.pg_cur.execute("""
                            INSERT INTO migracion_control (tabla_origen, id_origen)
                            VALUES ('EQCTACLI', %s)
                            ON CONFLICT (tabla_origen, id_origen) DO NOTHING
                        """, (cedula_original,))
                    
                    # Commit cada 500 registros
                    if (insertados + actualizados) % 500 == 0:
                        self.pg_conn.commit()
                        logging.info(f"Procesados: {insertados + actualizados}")
                        
                except Exception as e:
                    errores += 1
                    logging.warning(f"Error procesando paciente {codcli}: {e}")
                    continue
            
            self.pg_conn.commit()
            logging.info("=" * 60)
            logging.info(f"RESUMEN PACIENTES:")
            logging.info(f"Insertados nuevos: {insertados}")
            logging.info(f"Ya existían: {actualizados}")
            logging.info(f"Errores: {errores}")
            logging.info(f"Total procesados: {insertados + actualizados + errores}")
            
            return insertados
            
        except Exception as e:
            logging.error(f"Error en migración de pacientes: {e}")
            self.pg_conn.rollback()
            return 0
    
    def migrar_atenciones_corregido(self):
        """MIGRACIÓN CORREGIDA DE ATENCIONES - SIN FILTROS"""
        logging.info("\n" + "=" * 60)
        logging.info("MIGRANDO TODAS LAS ATENCIONES DESDE ACCESS")
        logging.info("=" * 60)
        
        try:
            # 1. Contar atenciones en Access
            self.acc_cur.execute("SELECT COUNT(*) FROM EqTraSec WHERE FechaIng IS NOT NULL")
            total_access = self.acc_cur.fetchone()[0] or 0
            logging.info(f"Total atenciones en Access: {total_access}")
            
            # 2. Obtener TODAS las atenciones de Access
            query = """
                SELECT 
                    T.FechaIng,
                    T.CodCli,
                    T.Cie10,
                    T.Grupo2,
                    T.SEspecialidad,
                    E.base_b,
                    E.dstvfac,
                    C.genero,
                    C.FechaN,
                    V.VENDEDOR
                FROM ((EqTraSec AS T
                LEFT JOIN EqCtaCli AS C ON T.CodCli = C.CodCli)
                LEFT JOIN EQCTAVDD AS V ON T.CodVen = V.CODVEN)
                LEFT JOIN EqEncPto AS E ON T.numfac = E.numfac
                WHERE T.FechaIng IS NOT NULL
            """
            
            self.acc_cur.execute(query)
            atenciones_access = self.acc_cur.fetchall()
            logging.info(f"Registros obtenidos de Access: {len(atenciones_access)}")
            
            insertadas = 0
            errores = 0
            sin_paciente = 0
            
            for idx, row in enumerate(atenciones_access, 1):
                try:
                    (f_atencion, codcli, cie10, grupo2, especialidad, 
                     base_b, dstvfac, genero, fecha_n, vendedor) = row
                    
                    # 1. Buscar paciente por CODCLI (cedula)
                    paciente_id = None
                    if codcli:
                        cedula_norm = self.normalizar_cedula(codcli)
                        cedula_original = str(codcli).strip()
                        
                        # Buscar por cédula normalizada o original
                        self.pg_cur.execute("""
                            SELECT id FROM paciente 
                            WHERE cedula = %s OR cedula_norm = %s
                            LIMIT 1
                        """, (cedula_original, cedula_norm))
                        
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            paciente_id = resultado[0]
                    
                    # 2. Si no existe paciente, crear uno básico
                    if not paciente_id and codcli:
                        # Crear paciente con datos mínimos
                        nombre = "PACIENTE NO REGISTRADO"
                        cedula_original = str(codcli).strip()
                        cedula_norm = self.normalizar_cedula(codcli)
                        
                        self.pg_cur.execute("""
                            INSERT INTO paciente (
                                cedula, cedula_norm, nombre, activo
                            ) VALUES (%s, %s, %s, TRUE)
                            RETURNING id
                        """, (cedula_original, cedula_norm, nombre))
                        
                        paciente_id = self.pg_cur.fetchone()[0]
                        sin_paciente += 1
                        logging.debug(f"Paciente creado automáticamente: ID={paciente_id}, CODCLI={codcli}")
                    
                    # 3. Si todavía no hay paciente, saltar esta atención
                    if not paciente_id:
                        errores += 1
                        continue
                    
                    # 4. Buscar CIE10
                    cie10_id = None
                    if cie10:
                        cie10_codigo = str(cie10).strip()
                        self.pg_cur.execute("SELECT id FROM cie10 WHERE codigo = %s", (cie10_codigo,))
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            cie10_id = resultado[0]
                    
                    # 5. Buscar tipo consulta (Grupo2)
                    tipo_consulta_id = None
                    if grupo2:
                        grupo_nombre = str(grupo2).strip()
                        self.pg_cur.execute("SELECT id FROM tipo_consulta WHERE nombre = %s", (grupo_nombre,))
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            tipo_consulta_id = resultado[0]
                    
                    # 6. Buscar médico (VENDEDOR)
                    medico_id = None
                    se_solicita_id = None
                    if vendedor:
                        vendedor_nombre = str(vendedor).strip()
                        # Buscar en médicos
                        self.pg_cur.execute("SELECT id FROM medico WHERE nombre = %s", (vendedor_nombre,))
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            medico_id = resultado[0]
                        
                        # Buscar en se_solicita_a
                        self.pg_cur.execute("SELECT id FROM se_solicita_a WHERE nombre = %s", (vendedor_nombre,))
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            se_solicita_id = resultado[0]
                    
                    # 7. Calcular edad si hay fecha de nacimiento
                    edad = None
                    if fecha_n and f_atencion:
                        try:
                            edad = f_atencion.year - fecha_n.year
                            if (f_atencion.month, f_atencion.day) < (fecha_n.month, fecha_n.day):
                                edad -= 1
                        except:
                            pass
                    
                    # 8. Insertar atención
                    self.pg_cur.execute("""
                        INSERT INTO atencion (
                            fecha_atencion,
                            paciente_id,
                            cie10_id,
                            tipo_consulta_id,
                            medico_id,
                            se_solicita_a_id,
                            edad,
                            genero,
                            valor_consulta,
                            valor_medicina,
                            observaciones
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        f_atencion,
                        paciente_id,
                        cie10_id,
                        tipo_consulta_id,
                        medico_id,
                        se_solicita_id,
                        edad,
                        str(genero).strip() if genero else None,
                        float(base_b) if base_b else 0.0,
                        float(dstvfac) if dstvfac else 0.0,
                        str(especialidad).strip() if especialidad else None
                    ))
                    
                    insertadas += 1
                    
                    # 9. Registrar en control (usamos un hash de la atención)
                    if codcli and f_atencion:
                        control_id = f"{codcli}_{f_atencion.strftime('%Y%m%d')}"
                        self.pg_cur.execute("""
                            INSERT INTO migracion_control (tabla_origen, id_origen)
                            VALUES ('EqTraSec', %s)
                            ON CONFLICT (tabla_origen, id_origen) DO NOTHING
                        """, (control_id,))
                    
                    # 10. Progress
                    if idx % 1000 == 0:
                        self.pg_conn.commit()
                        logging.info(f"Procesadas {idx}/{len(atenciones_access)} atenciones")
                        
                except Exception as e:
                    errores += 1
                    if errores < 10:  # Mostrar solo primeros errores
                        logging.warning(f"Error en atención {idx}: {e}")
                    continue
            
            self.pg_conn.commit()
            
            logging.info("=" * 60)
            logging.info(f"RESUMEN ATENCIONES:")
            logging.info(f"Total procesadas: {len(atenciones_access)}")
            logging.info(f"Insertadas exitosamente: {insertadas}")
            logging.info(f"Pacientes creados automáticamente: {sin_paciente}")
            logging.info(f"Errores: {errores}")
            
            return insertadas
            
        except Exception as e:
            logging.error(f"Error en migración de atenciones: {e}")
            self.pg_conn.rollback()
            return 0
    
    def verificar_migracion(self):
        """Verificar que los conteos sean consistentes"""
        logging.info("\n" + "=" * 60)
        logging.info("VERIFICACIÓN FINAL DE MIGRACIÓN")
        logging.info("=" * 60)
        
        try:
            # 1. Pacientes
            self.acc_cur.execute("SELECT COUNT(DISTINCT CODCLI) FROM EQCTACLI WHERE CODCLI IS NOT NULL")
            pacientes_access = self.acc_cur.fetchone()[0] or 0
            
            self.pg_cur.execute("SELECT COUNT(*) FROM paciente")
            pacientes_pg = self.pg_cur.fetchone()[0] or 0
            
            # 2. Atenciones
            self.acc_cur.execute("SELECT COUNT(*) FROM EqTraSec WHERE FechaIng IS NOT NULL")
            atenciones_access = self.acc_cur.fetchone()[0] or 0
            
            self.pg_cur.execute("SELECT COUNT(*) FROM atencion")
            atenciones_pg = self.pg_cur.fetchone()[0] or 0
            
            # 3. Cálculo de diferencias
            diff_pacientes = pacientes_access - pacientes_pg
            diff_atenciones = atenciones_access - atenciones_pg
            
            porcentaje_pacientes = (diff_pacientes / max(pacientes_access, 1)) * 100
            porcentaje_atenciones = (diff_atenciones / max(atenciones_access, 1)) * 100
            
            logging.info(f"PACIENTES:")
            logging.info(f"  Access: {pacientes_access:,}")
            logging.info(f"  PostgreSQL: {pacientes_pg:,}")
            logging.info(f"  Diferencia: {diff_pacientes:,} ({porcentaje_pacientes:.1f}%)")
            
            logging.info(f"\nATENCIONES:")
            logging.info(f"  Access: {atenciones_access:,}")
            logging.info(f"  PostgreSQL: {atenciones_pg:,}")
            logging.info(f"  Diferencia: {diff_atenciones:,} ({porcentaje_atenciones:.1f}%)")
            
            # 4. Evaluación
            logging.info("\n" + "=" * 60)
            logging.info("EVALUACIÓN:")
            
            if abs(porcentaje_pacientes) < 1 and abs(porcentaje_atenciones) < 1:
                logging.info("✅ MIGRACIÓN EXITOSA - Diferencias menores al 1%")
            elif abs(porcentaje_pacientes) < 5 and abs(porcentaje_atenciones) < 5:
                logging.info("⚠️  MIGRACIÓN ACEPTABLE - Diferencias menores al 5%")
            else:
                logging.info("❌ MIGRACIÓN CON PROBLEMAS - Diferencias mayores al 5%")
                logging.info("   Revisar los logs para identificar problemas")
            
            return {
                'pacientes_access': pacientes_access,
                'pacientes_pg': pacientes_pg,
                'atenciones_access': atenciones_access,
                'atenciones_pg': atenciones_pg,
                'diff_pacientes': diff_pacientes,
                'diff_atenciones': diff_atenciones
            }
            
        except Exception as e:
            logging.error(f"Error en verificación: {e}")
            return {}
    
    def ejecutar_migracion_completa(self):
        """Ejecutar toda la migración"""
        try:
            # 1. Crear tablas de control
            self.crear_control_tables()
            
            # 2. Migrar pacientes
            pacientes_migrados = self.migrar_pacientes_corregido()
            
            # 3. Migrar atenciones
            atenciones_migradas = self.migrar_atenciones_corregido()
            
            # 4. Verificar
            resultado = self.verificar_migracion()
            
            return {
                'pacientes_migrados': pacientes_migrados,
                'atenciones_migradas': atenciones_migradas,
                'verificacion': resultado
            }
            
        except Exception as e:
            logging.error(f"Error en migración completa: {e}")
            return {}
    
    def __del__(self):
        """Cerrar conexiones"""
        try:
            if hasattr(self, 'acc_cur'):
                self.acc_cur.close()
            if hasattr(self, 'acc_conn'):
                self.acc_conn.close()
            if hasattr(self, 'pg_cur'):
                self.pg_cur.close()
            if hasattr(self, 'pg_conn'):
                self.pg_conn.close()
        except:
            pass

def main():
    print("=" * 70)
    print("MIGRACIÓN CORREGIDA PARA PRODUCCIÓN")
    print("=" * 70)
    print("Este script:")
    print("1. Migra TODOS los pacientes (sin filtros)")
    print("2. Migra TODAS las atenciones (sin filtros)")
    print("3. Crea pacientes automáticamente si no existen")
    print("4. Registra todo en tablas de control")
    print("5. Verifica integridad final")
    print("=" * 70)
    
    confirmar = input("¿Ejecutar migración completa? (s/n): ").strip().lower()
    
    if confirmar != 's':
        print("Cancelado.")
        return
    
    migrador = MigradorProduccion()
    
    try:
        resultado = migrador.ejecutar_migracion_completa()
        
        print("\n" + "=" * 70)
        print("RESUMEN EJECUTIVO:")
        print("=" * 70)
        
        if resultado:
            print(f"Pacientes migrados: {resultado.get('pacientes_migrados', 0):,}")
            print(f"Atenciones migradas: {resultado.get('atenciones_migradas', 0):,}")
            
            verificacion = resultado.get('verificacion', {})
            if verificacion:
                print(f"\nVERIFICACIÓN:")
                print(f"Pacientes Access: {verificacion.get('pacientes_access', 0):,}")
                print(f"Pacientes PostgreSQL: {verificacion.get('pacientes_pg', 0):,}")
                print(f"Diferencia: {verificacion.get('diff_pacientes', 0):,}")
                print(f"\nAtenciones Access: {verificacion.get('atenciones_access', 0):,}")
                print(f"Atenciones PostgreSQL: {verificacion.get('atenciones_pg', 0):,}")
                print(f"Diferencia: {verificacion.get('diff_atenciones', 0):,}")
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
    finally:
        print("\n" + "=" * 70)
        print("PROCESO FINALIZADO")
        print("=" * 70)

if __name__ == "__main__":
    main()