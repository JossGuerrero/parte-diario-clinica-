"""
SISTEMA DE SINCRONIZACIÓN INCREMENTAL
Objetivo: Mantener sincronizadas ambas bases después de la migración inicial
"""
import pyodbc
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import schedule
from enum import Enum

from config import Config
from utils import DataUtils, setup_logging

logger = setup_logging("sincronizacion")

class EstadoSincronizacion(Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    ERROR = "error"
    DUPLICADO = "duplicado"

class SincronizadorIncremental:
    """Sistema de sincronización incremental entre Access y PostgreSQL"""
    
    def __init__(self):
        self.access_conn = None
        self.pg_conn = None
        self.mapeo = {}
        self.ultima_sincronizacion = None
        
    def inicializar(self):
        """Inicializar conexiones y cargar estado"""
        self.conectar_bases()
        self.cargar_mapeo()
        self.cargar_ultima_sincronizacion()
        
    def conectar_bases(self):
        """Conectar a ambas bases de datos"""
        # Access
        conn_str = Config.get_access_connection_string()
        self.access_conn = pyodbc.connect(conn_str)
        
        # PostgreSQL
        self.pg_conn = psycopg2.connect(**Config.POSTGRES_CONFIG)
        
        logger.info("✅ Conexiones establecidas")
    
    def cargar_mapeo(self):
        """Cargar mapeo actual"""
        with self.pg_conn.cursor() as cur:
            cur.execute("SELECT codcli_access, paciente_id FROM codcli_mapping")
            self.mapeo = {row[0]: row[1] for row in cur.fetchall()}
        
        logger.info(f"📋 Mapeo cargado: {len(self.mapeo)} registros")
    
    def cargar_ultima_sincronizacion(self):
        """Cargar fecha de última sincronización"""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                SELECT MAX(ultima_sync) 
                FROM sync_log 
                WHERE tabla_origen = 'EqTraSec' 
                AND status = 'success'
            """)
            resultado = cur.fetchone()
            self.ultima_sincronizacion = resultado[0] if resultado[0] else datetime(1900, 1, 1)
        
        logger.info(f"🕒 Última sincronización: {self.ultima_sincronizacion}")
    
    def obtener_nuevas_atenciones(self) -> List[Dict]:
        """Obtener atenciones nuevas desde la última sincronización"""
        query = f"""
        SELECT IdTs, CodCli, FechaIng, descrip, Triage, CodVen, Cie10
        FROM EqTraSec
        WHERE FechaIng > ?
        AND CodCli IS NOT NULL
        AND TRIM(CodCli) != ''
        ORDER BY FechaIng
        """
        
        with self.access_conn.cursor() as cur:
            cur.execute(query, self.ultima_sincronizacion)
            columnas = [desc[0] for desc in cur.description]
            
            atenciones = []
            for row in cur.fetchall():
                atencion = dict(zip(columnas, row))
                atencion['CodCli_norm'] = str(atencion['CodCli']).strip()
                atenciones.append(atencion)
        
        logger.info(f"📥 Nuevas atenciones encontradas: {len(atenciones)}")
        return atenciones
    
    def sincronizar_nuevas_atenciones(self, atenciones: List[Dict]) -> Dict:
        """Sincronizar nuevas atenciones"""
        estadisticas = {
            'procesadas': len(atenciones),
            'insertadas': 0,
            'actualizadas': 0,
            'errores': 0,
            'sin_mapeo': 0
        }
        
        for atencion in atenciones:
            try:
                resultado = self.procesar_atencion(atencion)
                
                if resultado == EstadoSincronizacion.COMPLETADO:
                    estadisticas['insertadas'] += 1
                elif resultado == EstadoSincronizacion.DUPLICADO:
                    estadisticas['actualizadas'] += 1
                elif resultado == EstadoSincronizacion.ERROR:
                    estadisticas['errores'] += 1
                elif resultado == EstadoSincronizacion.PENDIENTE:
                    estadisticas['sin_mapeo'] += 1
                    
            except Exception as e:
                logger.error(f"Error procesando atención {atencion.get('IdTs')}: {e}")
                estadisticas['errores'] += 1
        
        return estadisticas
    
    def procesar_atencion(self, atencion: Dict) -> EstadoSincronizacion:
        """Procesar una atención individual"""
        # Verificar si ya existe
        if self.verificar_existencia(atencion['IdTs']):
            return EstadoSincronizacion.DUPLICADO
        
        # Obtener paciente_id del mapeo
        codcli = atencion['CodCli_norm']
        paciente_id = self.mapeo.get(codcli)
        
        if not paciente_id:
            return EstadoSincronizacion.PENDIENTE
        
        # Transformar a estructura PostgreSQL
        atencion_pg = self.transformar_atencion(atencion, paciente_id)
        
        if not atencion_pg:
            return EstadoSincronizacion.ERROR
        
        # Insertar en PostgreSQL
        try:
            self.insertar_atencion(atencion_pg)
            self.registrar_sincronizacion(atencion['IdTs'])
            return EstadoSincronizacion.COMPLETADO
            
        except Exception as e:
            logger.error(f"Error insertando atención {atencion['IdTs']}: {e}")
            return EstadoSincronizacion.ERROR
    
    def transformar_atencion(self, atencion_access: Dict, paciente_id: int) -> Optional[Dict]:
        """Transformar atención de Access a PostgreSQL"""
        try:
            # Implementar transformación similar a migrador_atenciones.py
            # (Simplificado para el ejemplo)
            fecha_atencion = DataUtils.parsear_fecha_access(atencion_access.get('FechaIng'))
            
            return {
                'fecha_atencion': fecha_atencion.date() if fecha_atencion else None,
                'paciente_id': paciente_id,
                'observaciones': str(atencion_access.get('IdTs', '')),
                '_id_access': atencion_access['IdTs'],
                '_codcli_access': atencion_access['CodCli_norm']
            }
        except Exception as e:
            logger.error(f"Error transformando atención: {e}")
            return None
    
    def verificar_existencia(self, id_access: int) -> bool:
        """Verificar si la atención ya existe en PostgreSQL"""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM atencion_temporal 
                WHERE id_access = %s AND migrado = true
                UNION
                SELECT 1 FROM atencion 
                WHERE observaciones LIKE %s
            """, (id_access, f"%{id_access}%"))
            
            return cur.fetchone() is not None
    
    def insertar_atencion(self, atencion_pg: Dict):
        """Insertar atención en PostgreSQL"""
        with self.pg_conn.cursor() as cur:
            # Insertar en atencion (simplificado)
            cur.execute("""
                INSERT INTO atencion (
                    fecha_atencion, paciente_id, observaciones
                ) VALUES (%s, %s, %s)
            """, (
                atencion_pg['fecha_atencion'],
                atencion_pg['paciente_id'],
                atencion_pg['observaciones']
            ))
            
            # Registrar en atencion_temporal
            cur.execute("""
                INSERT INTO atencion_temporal (id_access, migrado, fecha_migracion)
                VALUES (%s, %s, %s)
            """, (
                atencion_pg['_id_access'],
                True,
                datetime.now()
            ))
            
            self.pg_conn.commit()
    
    def registrar_sincronizacion(self, id_access: int):
        """Registrar sincronización exitosa"""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO control_migracion (tabla_origen, id_origen, fecha_migracion)
                VALUES (%s, %s, %s)
            """, ('EqTraSec', id_access, datetime.now()))
            
            self.pg_conn.commit()
    
    def ejecutar_sincronizacion(self):
        """Ejecutar ciclo completo de sincronización"""
        logger.info("🔄 Iniciando sincronización incremental...")
        
        try:
            # 1. Obtener nuevas atenciones
            nuevas_atenciones = self.obtener_nuevas_atenciones()
            
            if not nuevas_atenciones:
                logger.info("✅ No hay nuevas atenciones para sincronizar")
                return
            
            # 2. Sincronizar
            estadisticas = self.sincronizar_nuevas_atenciones(nuevas_atenciones)
            
            # 3. Actualizar última sincronización
            self.ultima_sincronizacion = datetime.now()
            
            # 4. Registrar en log
            self.registrar_log_sincronizacion(estadisticas)
            
            logger.info(f"✅ Sincronización completada: {estadisticas}")
            
        except Exception as e:
            logger.error(f"❌ Error en sincronización: {e}")
            self.registrar_error_sincronizacion(str(e))
    
    def registrar_log_sincronizacion(self, estadisticas: Dict):
        """Registrar log de sincronización"""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sync_log (
                    ultima_sync, origen, tabla_origen,
                    registros_nuevos, registros_actualizados,
                    error, duracion_segundos, registros_procesados, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                self.ultima_sincronizacion,
                'ACCESS_INCREMENTAL',
                'EqTraSec',
                estadisticas['insertadas'],
                estadisticas['actualizadas'],
                '',
                0,  # TODO: Calcular duración
                estadisticas['procesadas'],
                'success' if estadisticas['errores'] == 0 else 'partial'
            ))
            
            self.pg_conn.commit()
    
    def registrar_error_sincronizacion(self, error: str):
        """Registrar error de sincronización"""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sync_log (
                    ultima_sync, origen, tabla_origen,
                    error, status
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                datetime.now(),
                'ACCESS_INCREMENTAL',
                'EqTraSec',
                error,
                'error'
            ))
            
            self.pg_conn.commit()
    
    def ejecutar_periodicamente(self, intervalo_minutos: int = 5):
        """Ejecutar sincronización periódicamente"""
        logger.info(f"⏰ Programando sincronización cada {intervalo_minutos} minutos")
        
        schedule.every(intervalo_minutos).minutes.do(self.ejecutar_sincronizacion)
        
        # Ejecutar una vez inmediatamente
        self.ejecutar_sincronizacion()
        
        # Mantener el programa en ejecución
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("👋 Sincronización detenida por el usuario")
        finally:
            self.cerrar_conexiones()
    
    def cerrar_conexiones(self):
        """Cerrar conexiones"""
        if self.access_conn:
            self.access_conn.close()
        if self.pg_conn:
            self.pg_conn.close()
        logger.info("🔌 Conexiones cerradas")

def modo_manual():
    """Ejecutar sincronización en modo manual"""
    sincronizador = SincronizadorIncremental()
    
    try:
        sincronizador.inicializar()
        sincronizador.ejecutar_sincronizacion()
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        sincronizador.cerrar_conexiones()

def modo_automatico():
    """Ejecutar sincronización en modo automático"""
    sincronizador = SincronizadorIncremental()
    
    try:
        sincronizador.inicializar()
        sincronizador.ejecutar_periodicamente(intervalo_minutos=5)
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        sincronizador.cerrar_conexiones()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sistema de sincronización incremental")
    parser.add_argument("--modo", choices=["manual", "auto"], default="manual",
                       help="Modo de ejecución (manual o automático)")
    
    args = parser.parse_args()
    
    if args.modo == "auto":
        modo_automatico()
    else:
        modo_manual()