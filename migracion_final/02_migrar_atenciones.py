"""
MIGRACIÓN MASIVA DE ATENCIONES
Objetivo: Migrar las 88,027 atenciones faltantes usando el mapeo reconstruido
"""
import pyodbc
import psycopg2
from psycopg2.extras import DictCursor, execute_batch
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
from tqdm import tqdm

from config import Config
from utils import DataUtils, setup_logging

logger = setup_logging("migrar_atenciones")

class MigradorAtenciones:
    """Migra atenciones de Access a PostgreSQL usando mapeo"""
    
    def __init__(self):
        self.access_conn = None
        self.pg_conn = None
        self.access_cursor = None
        self.pg_cursor = None
        self.mapeo = {}  # Diccionario codcli_access -> paciente_id
        self.contadores = {
            'total_atenciones': 0,
            'migradas': 0,
            'fallidas': 0,
            'sin_mapeo': 0,
            'duplicadas': 0
        }
        self.errores = []
        
    def conectar_bases(self):
        """Conectar a ambas bases de datos"""
        logger.info("Conectando a bases de datos...")
        
        # Access
        try:
            conn_str = Config.get_access_connection_string()
            self.access_conn = pyodbc.connect(conn_str)
            self.access_cursor = self.access_conn.cursor()
            logger.info("✅ Conexión Access establecida")
        except Exception as e:
            logger.error(f"❌ Error conectando a Access: {e}")
            raise
        
        # PostgreSQL
        try:
            self.pg_conn = psycopg2.connect(**Config.POSTGRES_CONFIG)
            self.pg_cursor = self.pg_conn.cursor(cursor_factory=DictCursor)
            logger.info("✅ Conexión PostgreSQL establecida")
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            raise
    
    def cargar_mapeo(self):
        """Cargar mapeo desde PostgreSQL"""
        logger.info("Cargando mapeo codcli -> paciente_id...")
        
        self.pg_cursor.execute("SELECT codcli_access, paciente_id FROM codcli_mapping")
        self.mapeo = {row[0]: row[1] for row in self.pg_cursor.fetchall()}
        
        logger.info(f"✅ Mapeo cargado: {len(self.mapeo)} registros")
        
        # Estadísticas de cobertura
        self.pg_cursor.execute("SELECT COUNT(*) FROM paciente")
        total_pacientes = self.pg_cursor.fetchone()[0]
        
        cobertura = (len(self.mapeo) / total_pacientes * 100) if total_pacientes > 0 else 0
        logger.info(f"📊 Cobertura de mapeo: {cobertura:.2f}% ({len(self.mapeo)}/{total_pacientes})")
        
        return self.mapeo
    
    def obtener_atenciones_ya_migradas(self) -> Set[int]:
        """Obtener IDs de atenciones ya migradas"""
        logger.info("Verificando atenciones ya migradas...")
        
        # Usar atencion_temporal si existe
        self.pg_cursor.execute("""
            SELECT id_access FROM atencion_temporal WHERE migrado = true
            UNION
            SELECT CAST(observaciones AS INTEGER) 
            FROM atencion 
            WHERE observaciones ~ '^[0-9]+$' AND LENGTH(observaciones) < 10
        """)
        
        migradas = {row[0] for row in self.pg_cursor.fetchall()}
        
        logger.info(f"✅ Atenciones ya migradas: {len(migradas)}")
        return migradas
    
    def obtener_atenciones_access(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """Obtener atenciones de Access"""
        logger.info(f"Obteniendo atenciones de Access...")
        
        query = """
        SELECT 
            IdTs, CodCli, FechaA, FechaIng, FechaSal, Motivo,
            Grupo, Grupo2, CodVen, descrip, Triage, FechaLlama,
            HoraLlega, AsisteC, Hospitaliza, Fecha, Hora, user,
            User_Mod, Fecha_Mod, Hora_Mod, TIPOS, NumAten, HoraING,
            TipoC, accidente, tipoacci, HORASAL, MotivoI, Inicial,
            Subsecuente, Presuntivo, Definitivo, DefInicial, DefControl,
            Procedimiento, User_PdI, Fecha_PdI, Hora_PdI, User_PdF,
            Fecha_PdF, Hora_PdF, Cie10, CDeriva, RDeriva, RDescDer,
            RTipoDer, RDescrip1, RIdPrestador, SEspecialidad, claHistorias,
            ROtros, RCodigos, tipdoc, numfac, tipdoc_i, numfac_i
        FROM EqTraSec
        WHERE CodCli IS NOT NULL 
        AND TRIM(CodCli) != ''
        AND FechaIng IS NOT NULL
        """
        
        if limit:
            query += f" ORDER BY IdTs OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
        
        self.access_cursor.execute(query)
        columnas = [desc[0] for desc in self.access_cursor.description]
        
        atenciones = []
        for row in tqdm(self.access_cursor.fetchall(), desc="Leyendo atenciones"):
            atencion = dict(zip(columnas, row))
            
            # Normalizar codcli
            codcli = str(atencion['CodCli']).strip()
            atencion['CodCli_norm'] = codcli
            
            atenciones.append(atencion)
        
        logger.info(f"✅ Obtenidas {len(atenciones)} atenciones de Access")
        return atenciones
    
    def mapear_medico_access_a_pg(self, codven_access: str) -> Optional[int]:
        """Mapear código de médico de Access a ID de PostgreSQL"""
        if not codven_access:
            return None
        
        codven_norm = str(codven_access).strip()
        
        # Buscar en tabla médico por nombre similar
        self.pg_cursor.execute("""
            SELECT id FROM medico 
            WHERE UPPER(unaccent(nombre)) LIKE UPPER(unaccent(%s)) || '%'
            OR UPPER(unaccent(especialidad)) LIKE UPPER(unaccent(%s)) || '%'
            LIMIT 1
        """, (codven_norm, codven_norm))
        
        resultado = self.pg_cursor.fetchone()
        return resultado[0] if resultado else None
    
    def mapear_cie10_access_a_pg(self, cie10_access: str) -> Optional[int]:
        """Mapear código CIE10 de Access a ID de PostgreSQL"""
        if not cie10_access:
            return None
        
        cie10_norm = str(cie10_access).strip()
        
        # Buscar exacto
        self.pg_cursor.execute("""
            SELECT id FROM cie10 
            WHERE codigo = %s
            LIMIT 1
        """, (cie10_norm,))
        
        resultado = self.pg_cursor.fetchone()
        if resultado:
            return resultado[0]
        
        # Buscar por similitud
        self.pg_cursor.execute("""
            SELECT id FROM cie10 
            WHERE codigo LIKE %s || '%'
            OR descripcion ILIKE '%' || %s || '%'
            LIMIT 1
        """, (cie10_norm, cie10_norm))
        
        resultado = self.pg_cursor.fetchone()
        return resultado[0] if resultado else None
    
    def calcular_edad_en_fecha(self, fecha_nacimiento: Optional[datetime], fecha_atencion: datetime) -> Optional[int]:
        """Calcular edad en el momento de la atención"""
        if not fecha_nacimiento or not fecha_atencion:
            return None
        
        try:
            edad = fecha_atencion.year - fecha_nacimiento.year
            
            # Ajustar si aún no ha cumplido años
            if (fecha_atencion.month, fecha_atencion.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
                edad -= 1
            
            return edad if edad >= 0 else None
        except Exception:
            return None
    
    def transformar_atencion_access_a_pg(self, atencion_access: Dict) -> Optional[Dict]:
        """Transformar estructura de Access a PostgreSQL"""
        try:
            # 1. Obtener paciente_id del mapeo
            codcli = atencion_access['CodCli_norm']
            paciente_id = self.mapeo.get(codcli)
            
            if not paciente_id:
                self.contadores['sin_mapeo'] += 1
                return None
            
            # 2. Obtener datos del paciente para edad/género
            self.pg_cursor.execute("""
                SELECT fecha_nacimiento, genero 
                FROM paciente 
                WHERE id = %s
            """, (paciente_id,))
            
            paciente_data = self.pg_cursor.fetchone()
            fecha_nacimiento = paciente_data[0] if paciente_data else None
            genero_paciente = paciente_data[1] if paciente_data else None
            
            # 3. Parsear fechas
            fecha_atencion = DataUtils.parsear_fecha_access(atencion_access.get('FechaIng'))
            if not fecha_atencion:
                fecha_atencion = DataUtils.parsear_fecha_access(atencion_access.get('FechaA'))
            
            # 4. Calcular edad
            edad = None
            if fecha_atencion and fecha_nacimiento:
                edad = self.calcular_edad_en_fecha(fecha_nacimiento, fecha_atencion)
            
            # 5. Mapear médico
            medico_id = self.mapear_medico_access_a_pg(atencion_access.get('CodVen'))
            
            # 6. Mapear CIE10
            cie10_id = self.mapear_cie10_access_a_pg(atencion_access.get('Cie10'))
            
            # 7. Determinar tipo de consulta (basado en descrip)
            tipo_consulta_id = None
            descripcion = atencion_access.get('descrip', '')
            if descripcion:
                descrip_norm = DataUtils.normalizar_nombre(descripcion)
                
                self.pg_cursor.execute("""
                    SELECT id FROM tipo_consulta 
                    WHERE UPPER(unaccent(nombre)) LIKE '%' || UPPER(unaccent(%s)) || '%'
                    OR UPPER(unaccent(descripcion)) LIKE '%' || UPPER(unaccent(%s)) || '%'
                    LIMIT 1
                """, (descrip_norm, descrip_norm))
                
                resultado = self.pg_cursor.fetchone()
                tipo_consulta_id = resultado[0] if resultado else None
            
            # 8. Crear objeto de atención para PostgreSQL
            atencion_pg = {
                'fecha_atencion': fecha_atencion.date() if fecha_atencion else None,
                'medico_id': medico_id,
                'tipo_consulta_id': tipo_consulta_id,
                'se_solicita_a_id': None,  # Por determinar
                'paciente_id': paciente_id,
                'cie10_id': cie10_id,
                'edad': edad,
                'genero': genero_paciente or atencion_access.get('TIPOS'),
                'valor_consulta': 0.00,  # Por determinar
                'valor_medicina': 0.00,  # Por determinar
                'observaciones': str(atencion_access.get('IdTs', '')),  # Guardar ID de Access
                # Campos adicionales para auditoría
                '_id_access': atencion_access.get('IdTs'),
                '_codcli_access': codcli,
                '_descrip_access': descripcion,
                '_triage_access': atencion_access.get('Triage'),
                '_fecha_migracion': datetime.now()
            }
            
            return atencion_pg
            
        except Exception as e:
            error_info = {
                'id_access': atencion_access.get('IdTs'),
                'codcli': atencion_access.get('CodCli'),
                'error': str(e),
                'atencion': str(atencion_access)[:200]
            }
            self.errores.append(error_info)
            self.contadores['fallidas'] += 1
            return None
    
    def verificar_duplicidad(self, atencion_pg: Dict) -> bool:
        """Verificar si la atención ya existe en PostgreSQL"""
        try:
            condiciones = []
            params = []
            
            if atencion_pg['fecha_atencion']:
                condiciones.append("fecha_atencion = %s")
                params.append(atencion_pg['fecha_atencion'])
            
            if atencion_pg['paciente_id']:
                condiciones.append("paciente_id = %s")
                params.append(atencion_pg['paciente_id'])
            
            if atencion_pg['medico_id']:
                condiciones.append("medico_id = %s")
                params.append(atencion_pg['medico_id'])
            
            if atencion_pg['observaciones']:
                # Buscar por ID de Access en observaciones
                condiciones.append("observaciones LIKE %s")
                params.append(f"%{atencion_pg['_id_access']}%")
            
            if not condiciones:
                return False
            
            query = f"SELECT COUNT(*) FROM atencion WHERE {' AND '.join(condiciones)}"
            self.pg_cursor.execute(query, params)
            count = self.pg_cursor.fetchone()[0]
            
            return count > 0
            
        except Exception:
            return False
    
    def migrar_lote(self, atenciones_access: List[Dict]) -> Dict:
        """Migrar un lote de atenciones"""
        atenciones_pg = []
        
        for atencion_access in atenciones_access:
            atencion_pg = self.transformar_atencion_access_a_pg(atencion_access)
            
            if not atencion_pg:
                continue
            
            # Verificar duplicidad
            if self.verificar_duplicidad(atencion_pg):
                self.contadores['duplicadas'] += 1
                continue
            
            atenciones_pg.append(atencion_pg)
        
        # Insertar en PostgreSQL
        if atenciones_pg:
            self.insertar_atenciones_pg(atenciones_pg)
        
        return {
            'procesadas': len(atenciones_access),
            'migradas': len(atenciones_pg),
            'errores': len(self.errores[-len(atenciones_access):])
        }
    
    def insertar_atenciones_pg(self, atenciones_pg: List[Dict]):
        """Insertar atenciones en PostgreSQL"""
        try:
            # Preparar datos para inserción
            valores = []
            for atencion in atenciones_pg:
                valores.append((
                    atencion['fecha_atencion'],
                    atencion['medico_id'],
                    atencion['tipo_consulta_id'],
                    atencion['se_solicita_a_id'],
                    atencion['paciente_id'],
                    atencion['cie10_id'],
                    atencion['edad'],
                    atencion['genero'],
                    atencion['valor_consulta'],
                    atencion['valor_medicina'],
                    atencion['observaciones']
                ))
            
            # Insertar en lote
            query = """
            INSERT INTO atencion (
                fecha_atencion, medico_id, tipo_consulta_id, se_solicita_a_id,
                paciente_id, cie10_id, edad, genero, valor_consulta,
                valor_medicina, observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            execute_batch(self.pg_cursor, query, valores)
            
            # Registrar en atencion_temporal
            for atencion in atenciones_pg:
                self.pg_cursor.execute("""
                    INSERT INTO atencion_temporal (id_access, migrado, fecha_migracion)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id_access) DO UPDATE SET
                    migrado = EXCLUDED.migrado,
                    fecha_migracion = EXCLUDED.fecha_migracion
                """, (
                    atencion['_id_access'],
                    True,
                    atencion['_fecha_migracion']
                ))
            
            self.pg_conn.commit()
            self.contadores['migradas'] += len(atenciones_pg)
            
            logger.info(f"✅ Lote insertado: {len(atenciones_pg)} atenciones")
            
        except Exception as e:
            self.pg_conn.rollback()
            logger.error(f"❌ Error insertando lote: {e}")
            raise
    
    def migrar_atenciones_masivamente(self, batch_size: int = 1000, max_atenciones: int = None):
        """Migrar todas las atenciones de Access a PostgreSQL"""
        logger.info("🚀 INICIANDO MIGRACIÓN MASIVA DE ATENCIONES")
        
        # 1. Cargar mapeo
        self.cargar_mapeo()
        
        if not self.mapeo:
            logger.error("❌ No hay mapeo cargado. Ejecuta primero 01_reconstruir_mapeo.py")
            return
        
        # 2. Obtener atenciones ya migradas
        ya_migradas = self.obtener_atenciones_ya_migradas()
        
        # 3. Contar total de atenciones en Access
        self.access_cursor.execute("SELECT COUNT(*) FROM EqTraSec WHERE CodCli IS NOT NULL")
        total_access = self.access_cursor.fetchone()[0]
        
        logger.info(f"📊 Total atenciones en Access: {total_access}")
        logger.info(f"📊 Ya migradas: {len(ya_migradas)}")
        logger.info(f"📊 Pendientes: {total_access - len(ya_migradas)}")
        
        # 4. Migrar por lotes
        offset = 0
        batch_size = min(batch_size, Config.BATCH_SIZE)
        
        if max_atenciones:
            total_a_migrar = min(max_atenciones, total_access - len(ya_migradas))
        else:
            total_a_migrar = total_access - len(ya_migradas)
        
        with tqdm(total=total_a_migrar, desc="Migrando atenciones") as pbar:
            while offset < total_a_migrar:
                # Obtener lote de Access
                atenciones_access = self.obtener_atenciones_access(
                    limit=batch_size, 
                    offset=offset
                )
                
                if not atenciones_access:
                    break
                
                # Filtrar ya migradas
                atenciones_nuevas = [
                    a for a in atenciones_access 
                    if a['IdTs'] not in ya_migradas
                ]
                
                # Migrar lote
                if atenciones_nuevas:
                    resultado = self.migrar_lote(atenciones_nuevas)
                    
                    # Actualizar barra de progreso
                    pbar.update(len(atenciones_access))
                    
                    # Mostrar estadísticas periódicas
                    if offset % (batch_size * 10) == 0:
                        logger.info(
                            f"📊 Progreso: {offset}/{total_a_migrar} | "
                            f"Migradas: {self.contadores['migradas']} | "
                            f"Fallidas: {self.contadores['fallidas']} | "
                            f"Sin mapeo: {self.contadores['sin_mapeo']}"
                        )
                
                offset += batch_size
        
        # 5. Generar reporte final
        self.generar_reporte_final(total_access)
    
    def generar_reporte_final(self, total_access: int):
        """Generar reporte final de migración"""
        logger.info("Generando reporte final...")
        
        estadisticas = {
            'Total atenciones en Access': total_access,
            'Atenciones migradas exitosamente': self.contadores['migradas'],
            'Atenciones fallidas': self.contadores['fallidas'],
            'Atenciones sin mapeo (paciente no encontrado)': self.contadores['sin_mapeo'],
            'Atenciones duplicadas (omitidas)': self.contadores['duplicadas'],
            'Tasa de éxito': f"{(self.contadores['migradas'] / total_access * 100):.2f}%" if total_access > 0 else "N/A",
            'Errores registrados': len(self.errores)
        }
        
        # Guardar estadísticas en log
        reporte_path = Config.LOG_DIR / f"reporte_migracion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(reporte_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("REPORTE FINAL DE MIGRACIÓN DE ATENCIONES\n")
            f.write("="*60 + "\n\n")
            
            for clave, valor in estadisticas.items():
                f.write(f"{clave}: {valor}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("PRIMEROS 10 ERRORES (si hay):\n")
            f.write("="*60 + "\n")
            
            for i, error in enumerate(self.errores[:10]):
                f.write(f"\nError {i+1}:\n")
                for k, v in error.items():
                    f.write(f"  {k}: {v}\n")
        
        # Actualizar sync_log
        self.pg_cursor.execute("""
            INSERT INTO sync_log (
                ultima_sync, origen, tabla_origen,
                registros_nuevos, registros_actualizados,
                error, duracion_segundos, registros_procesados, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.now(),
            'ACCESS',
            'EqTraSec',
            self.contadores['migradas'],
            0,
            '' if not self.errores else str(self.errores[:3]),
            0,  # TODO: Calcular duración
            total_access,
            'success' if self.contadores['migradas'] > 0 else 'partial'
        ))
        
        self.pg_conn.commit()
        
        logger.info(f"✅ Reporte guardado en: {reporte_path}")
        
        print(f"\n{'='*60}")
        print("🎯 MIGRACIÓN DE ATENCIONES COMPLETADA")
        print(f"{'='*60}")
        for clave, valor in estadisticas.items():
            print(f"{clave}: {valor}")
        print(f"\n📊 Ver reporte completo en: {reporte_path}")

def main():
    """Función principal"""
    migrador = MigradorAtenciones()
    
    try:
        # Conectar
        migrador.conectar_bases()
        
        # Migrar atenciones (ajustar parámetros según necesidad)
        # migrador.migrar_atenciones_masivamente(batch_size=500, max_atenciones=10000)  # Para prueba
        migrador.migrar_atenciones_masivamente(batch_size=1000)  # Para migración completa
        
    except Exception as e:
        logger.error(f"Error durante la migración: {e}", exc_info=True)
        print(f"❌ Error: {e}")
    finally:
        if migrador.pg_cursor:
            migrador.pg_cursor.close()
        if migrador.pg_conn:
            migrador.pg_conn.close()
        if migrador.access_cursor:
            migrador.access_cursor.close()
        if migrador.access_conn:
            migrador.access_conn.close()

if __name__ == "__main__":
    main()