# migracion_compatible_access.py
import pyodbc
import psycopg2
import logging
from datetime import datetime
import sys

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

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

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('migracion_compatible.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

class MigracionCompatible:
    def __init__(self):
        self.acc_conn = None
        self.acc_cur = None
        self.pg_conn = None
        self.pg_cur = None
        
    def conectar(self):
        """Conectar a ambas bases"""
        try:
            # Access
            conn_str = (
                r"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};"
                r"DBQ={0};PWD={1};"
            ).format(CONFIG['access']['file'], CONFIG['access']['password'])
            self.acc_conn = pyodbc.connect(conn_str)
            self.acc_cur = self.acc_conn.cursor()
            
            # PostgreSQL
            self.pg_conn = psycopg2.connect(**CONFIG['postgres'])
            self.pg_cur = self.pg_cur = self.pg_conn.cursor()
            
            return True
        except Exception as e:
            logger.error(f"❌ Error conexión: {e}")
            return False
    
    def limpiar_texto(self, texto):
        """Limpiar texto en Python"""
        if texto is None:
            return ""
        return str(texto).strip()
    
    def diagnosticar(self):
        """Diagnóstico compatible con Access"""
        logger.info("🔍 DIAGNÓSTICO COMPATIBLE")
        logger.info("=" * 50)
        
        try:
            # 1. Contar atenciones en Access (forma compatible)
            self.acc_cur.execute("SELECT COUNT(*) FROM EqTraSec")
            acc_count = self.acc_cur.fetchone()[0]
            
            # 2. Contar atenciones en PostgreSQL
            self.pg_cur.execute("SELECT COUNT(*) FROM atencion")
            pg_count = self.pg_cur.fetchone()[0]
            
            # 3. Ver ejemplo de datos
            logger.info(f"📊 Atenciones Access: {acc_count:,}")
            logger.info(f"📊 Atenciones PostgreSQL: {pg_count:,}")
            logger.info(f"📊 Faltantes estimados: {acc_count - pg_count:,}")
            
            return acc_count, pg_count
            
        except Exception as e:
            logger.error(f"Error diagnóstico: {e}")
            return 0, 0
    
    def crear_mapeo_compatible(self):
        """Crear mapeo usando consultas compatibles con Access"""
        logger.info("🗺️ CREANDO MAPEO COMPATIBLE")
        
        try:
            # 1. Limpiar mapeo anterior
            self.pg_cur.execute("DELETE FROM codcli_mapping")
            self.pg_conn.commit()
            
            # 2. Obtener pacientes de Access (sin funciones complejas)
            query = """
                SELECT codcli, cedula 
                FROM EqCtaCli 
                WHERE codcli IS NOT NULL
            """
            
            self.acc_cur.execute(query)
            pacientes = self.acc_cur.fetchall()
            logger.info(f"📋 Registros en EqCtaCli: {len(pacientes):,}")
            
            # 3. Procesar en Python
            mapeados = 0
            no_mapeados = 0
            
            for codcli, cedula in pacientes:
                try:
                    # Limpiar en Python
                    codcli_limpio = self.limpiar_texto(codcli)
                    cedula_limpia = self.limpiar_texto(cedula)
                    
                    if not codcli_limpio:
                        continue
                    
                    paciente_id = None
                    
                    # Buscar por cédula limpia
                    if cedula_limpia:
                        self.pg_cur.execute("SELECT id FROM paciente WHERE cedula = %s", (cedula_limpia,))
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            paciente_id = resultado[0]
                    
                    # Si no, buscar por codcli como cédula
                    if not paciente_id:
                        self.pg_cur.execute("SELECT id FROM paciente WHERE cedula = %s", (codcli_limpio,))
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            paciente_id = resultado[0]
                    
                    # Si encontró, guardar mapeo
                    if paciente_id:
                        self.pg_cur.execute("""
                            INSERT INTO codcli_mapping (codcli_access, paciente_id)
                            VALUES (%s, %s)
                            ON CONFLICT (codcli_access) DO NOTHING
                        """, (codcli_limpio, paciente_id))
                        mapeados += 1
                    else:
                        no_mapeados += 1
                    
                    # Commit cada 1000
                    if (mapeados + no_mapeados) % 1000 == 0:
                        self.pg_conn.commit()
                        
                except Exception as e:
                    no_mapeados += 1
            
            self.pg_conn.commit()
            
            logger.info(f"✅ Mapeo completado:")
            logger.info(f"   • Pacientes mapeados: {mapeados:,}")
            logger.info(f"   • Sin coincidencia: {no_mapeados:,}")
            
            # 4. Verificar eficacia del mapeo
            # Obtener códigos únicos de atenciones
            self.acc_cur.execute("SELECT CodCli FROM EqTraSec WHERE CodCli IS NOT NULL")
            codigos_atenciones = set()
            for row in self.acc_cur.fetchall():
                if row[0]:
                    codigos_atenciones.add(self.limpiar_texto(row[0]))
            
            # Obtener códigos mapeados
            self.pg_cur.execute("SELECT codcli_access FROM codcli_mapping")
            codigos_mapeados = {row[0] for row in self.pg_cur.fetchall()}
            
            # Intersección
            codigos_con_atencion = codigos_atenciones & codigos_mapeados
            
            logger.info(f"📊 Códigos únicos en atenciones: {len(codigos_atenciones):,}")
            logger.info(f"📊 Códigos mapeados: {len(codigos_mapeados):,}")
            logger.info(f"📊 Códigos mapeados con atenciones: {len(codigos_con_atencion):,}")
            
            if codigos_atenciones:
                porcentaje = len(codigos_con_atencion) / len(codigos_atenciones) * 100
                logger.info(f"📈 Porcentaje cubierto: {porcentaje:.1f}%")
            
            return mapeados
            
        except Exception as e:
            logger.error(f"❌ Error en mapeo: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def migrar_atenciones_directo(self):
        """Migrar atenciones de forma directa y compatible"""
        logger.info("🚀 MIGRANDO ATENCIONES (Método Directo)")
        
        try:
            # 1. Obtener mapeo
            self.pg_cur.execute("SELECT codcli_access, paciente_id FROM codcli_mapping")
            mapeo = {row[0]: row[1] for row in self.pg_cur.fetchall()}
            
            if not mapeo:
                logger.error("❌ No hay mapeo. Ejecuta primero el mapeo.")
                return 0, 0
            
            # 2. Obtener atenciones (consulta compatible)
            query = """
                SELECT IdTs, CodCli, FechaIng, descrip
                FROM EqTraSec 
                WHERE CodCli IS NOT NULL AND FechaIng IS NOT NULL
                ORDER BY IdTs
            """
            
            self.acc_cur.execute(query)
            atenciones = self.acc_cur.fetchall()
            total = len(atenciones)
            
            logger.info(f"📊 Total atenciones a procesar: {total:,}")
            
            # 3. Contar atenciones existentes
            self.pg_cur.execute("SELECT COUNT(*) FROM atencion")
            count_inicial = self.pg_cur.fetchone()[0]
            logger.info(f"📊 Atenciones ya en PostgreSQL: {count_inicial:,}")
            
            # 4. Migrar por lotes
            lote_size = 1000
            migradas = 0
            errores = 0
            duplicados = 0
            
            for i in range(0, total, lote_size):
                batch = atenciones[i:i + lote_size]
                batch_migradas, batch_errores, batch_duplicados = self._procesar_batch(batch, mapeo)
                
                migradas += batch_migradas
                errores += batch_errores
                duplicados += batch_duplicados
                
                self.pg_conn.commit()
                
                progreso = min(i + lote_size, total)
                logger.info(f"📦 Lote {i//lote_size + 1}: {progreso:,}/{total:,} ({progreso/total*100:.1f}%)")
            
            # 5. Resultados
            logger.info("=" * 60)
            logger.info(f"🎉 MIGRACIÓN COMPLETADA")
            logger.info(f"   Total procesadas: {total:,}")
            logger.info(f"   Migradas nuevas: {migradas:,}")
            logger.info(f"   Duplicados omitidos: {duplicados:,}")
            logger.info(f"   Errores: {errores:,}")
            logger.info("=" * 60)
            
            # 6. Conteo final
            self.pg_cur.execute("SELECT COUNT(*) FROM atencion")
            count_final = self.pg_cur.fetchone()[0]
            logger.info(f"📊 Atenciones en PostgreSQL después: {count_final:,}")
            logger.info(f"📊 Incremento real: {count_final - count_inicial:,}")
            
            return migradas, errores
            
        except Exception as e:
            logger.error(f"💥 ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 0, 0
    
    def _procesar_batch(self, batch, mapeo):
        """Procesar un batch de atenciones"""
        migradas = 0
        errores = 0
        duplicados = 0
        
        for idts, codcli, fecha, descrip in batch:
            try:
                # Limpiar código
                codcli_limpio = self.limpiar_texto(codcli)
                if not codcli_limpio:
                    errores += 1
                    continue
                
                # Buscar paciente
                paciente_id = mapeo.get(codcli_limpio)
                if not paciente_id:
                    errores += 1
                    continue
                
                # Verificar si ya existe
                self.pg_cur.execute("""
                    SELECT id FROM atencion 
                    WHERE paciente_id = %s AND fecha_atencion = %s
                    LIMIT 1
                """, (paciente_id, fecha))
                
                if self.pg_cur.fetchone():
                    duplicados += 1
                    continue
                
                # Obtener tipo_consulta
                tipo_consulta_id = None
                if descrip:
                    descrip_limpio = self.limpiar_texto(descrip)[:100]
                    if descrip_limpio:
                        self.pg_cur.execute("SELECT id FROM tipo_consulta WHERE nombre = %s", (descrip_limpio,))
                        resultado = self.pg_cur.fetchone()
                        if resultado:
                            tipo_consulta_id = resultado[0]
                
                # Insertar
                self.pg_cur.execute("""
                    INSERT INTO atencion 
                    (fecha_atencion, paciente_id, tipo_consulta_id, valor_consulta, valor_medicina)
                    VALUES (%s, %s, %s, %s, %s)
                """, (fecha, paciente_id, tipo_consulta_id, 0.0, 0.0))
                
                migradas += 1
                
            except Exception as e:
                errores += 1
                if errores <= 10:
                    logger.debug(f"  Error ID {idts}: {e}")
        
        return migradas, errores, duplicados
    
    def verificar_estado(self):
        """Verificar estado actual"""
        try:
            # Access
            self.acc_cur.execute("SELECT COUNT(*) FROM EqTraSec")
            acc_total = self.acc_cur.fetchone()[0]
            
            # PostgreSQL
            self.pg_cur.execute("SELECT COUNT(*) FROM atencion")
            pg_total = self.pg_cur.fetchone()[0]
            
            # Mapeo
            self.pg_cur.execute("SELECT COUNT(*) FROM codcli_mapping")
            mapeados = self.pg_cur.fetchone()[0]
            
            logger.info("=" * 60)
            logger.info("📊 ESTADO ACTUAL")
            logger.info("=" * 60)
            logger.info(f"ACCESS:")
            logger.info(f"  • Atenciones totales: {acc_total:,}")
            logger.info("")
            logger.info(f"POSTGRESQL:")
            logger.info(f"  • Atenciones totales: {pg_total:,}")
            logger.info(f"  • Pacientes mapeados: {mapeados:,}")
            logger.info("")
            logger.info(f"ESTADO MIGRACIÓN:")
            logger.info(f"  • Faltantes: {acc_total - pg_total:,}")
            if acc_total > 0:
                logger.info(f"  • % Completado: {(pg_total/acc_total*100):.1f}%")
            logger.info("=" * 60)
            
            return acc_total - pg_total
            
        except Exception as e:
            logger.error(f"Error verificando: {e}")
            return 0
    
    def ejecutar_migracion_completa(self):
        """Ejecutar migración completa"""
        logger.info("=" * 60)
        logger.info("MIGRACIÓN COMPLETA - COMPATIBLE CON ACCESS")
        logger.info("=" * 60)
        
        try:
            if not self.conectar():
                return
            
            # Paso 1: Diagnosticar
            logger.info("\n1️⃣  DIAGNÓSTICO")
            acc_total, pg_total = self.diagnosticar()
            
            if acc_total <= pg_total:
                logger.info("✅ Ya están todas migradas")
                return
            
            faltantes = acc_total - pg_total
            logger.info(f"⚠️  Atenciones faltantes: {faltantes:,}")
            
            respuesta = input(f"\n¿Continuar con mapeo de pacientes? (s/n): ").lower()
            if respuesta != 's':
                logger.info("Operación cancelada")
                return
            
            # Paso 2: Mapeo
            logger.info("\n2️⃣  MAPEO DE PACIENTES")
            mapeados = self.crear_mapeo_compatible()
            
            if mapeados == 0:
                logger.error("❌ No se creó mapeo. Revisa los logs.")
                return
            
            # Paso 3: Confirmar migración
            respuesta = input(f"\n¿Migrar {faltantes:,} atenciones faltantes? (s/n): ").lower()
            if respuesta != 's':
                logger.info("Migración cancelada")
                return
            
            # Paso 4: Migrar
            logger.info("\n3️⃣  MIGRANDO ATENCIONES")
            logger.info("   Esto puede tardar varios minutos...")
            logger.info("   Por favor no interrumpir.")
            
            migradas, errores = self.migrar_atenciones_directo()
            
            # Paso 5: Resultados
            logger.info("\n4️⃣  RESULTADOS FINALES")
            self.verificar_estado()
            
            if migradas > 0:
                logger.info(f"✅ ¡Se migraron {migradas:,} atenciones!")
            else:
                logger.info("⚠️  No se migraron atenciones nuevas")
            
            logger.info("\n🎉 PROCESO TERMINADO")
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cerrar conexiones"""
        try:
            if self.acc_cur:
                self.acc_cur.close()
            if self.acc_conn:
                self.acc_conn.close()
            if self.pg_cur:
                self.pg_cur.close()
            if self.pg_conn:
                self.pg_conn.close()
        except:
            pass

# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    migracion = MigracionCompatible()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "diagnostico":
            migracion.conectar()
            migracion.diagnosticar()
            migracion.verificar_estado()
            migracion.cerrar()
        elif sys.argv[1] == "mapeo":
            migracion.conectar()
            migracion.crear_mapeo_compatible()
            migracion.cerrar()
        elif sys.argv[1] == "migrar":
            migracion.conectar()
            migracion.migrar_atenciones_directo()
            migracion.verificar_estado()
            migracion.cerrar()
        elif sys.argv[1] == "verificar":
            migracion.conectar()
            migracion.verificar_estado()
            migracion.cerrar()
        elif sys.argv[1] == "test":
            migracion.conectar()
            migracion.cerrar()
            logger.info("✅ Conexión exitosa")
    else:
        migracion.ejecutar_migracion_completa()