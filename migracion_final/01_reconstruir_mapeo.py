"""
RECONSTRUCCIÓN COMPLETA DE MAPEO ACCESS → POSTGRESQL
Objetivo: Crear mapeo para los 17,383 pacientes de Access
"""
import pyodbc
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
import pandas as pd
from tqdm import tqdm

from config import Config
from utils import DataUtils, setup_logging

logger = setup_logging("reconstruir_mapeo")

class ReconstructorMapeo:
    """Reconstruye el mapeo completo entre Access y PostgreSQL"""
    
    def __init__(self):
        self.access_conn = None
        self.pg_conn = None
        self.access_cursor = None
        self.pg_cursor = None
        self.mapeos = []  # Lista de mapeos encontrados
        self.no_encontrados = []  # Pacientes sin match
        self.duplicados = []  # Casos de duplicidad
        
    def conectar_bases(self):
        """Conectar a ambas bases de datos"""
        logger.info("Conectando a bases de datos...")
        
        # Conectar a Access
        try:
            conn_str = Config.get_access_connection_string()
            self.access_conn = pyodbc.connect(conn_str)
            self.access_cursor = self.access_conn.cursor()
            logger.info("✅ Conexión Access establecida")
        except Exception as e:
            logger.error(f"❌ Error conectando a Access: {e}")
            raise
        
        # Conectar a PostgreSQL
        try:
            self.pg_conn = psycopg2.connect(**Config.POSTGRES_CONFIG)
            self.pg_cursor = self.pg_conn.cursor(cursor_factory=DictCursor)
            logger.info("✅ Conexión PostgreSQL establecida")
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            raise
    
    def desconectar(self):
        """Cerrar conexiones"""
        if self.access_cursor:
            self.access_cursor.close()
        if self.access_conn:
            self.access_conn.close()
        if self.pg_cursor:
            self.pg_cursor.close()
        if self.pg_conn:
            self.pg_conn.close()
        logger.info("Conexiones cerradas")
    
    def obtener_pacientes_access(self) -> List[Dict]:
        """Obtener todos los pacientes de Access"""
        logger.info("Obteniendo pacientes de Access...")
        
        query = f"""
        SELECT {', '.join(Config.ACCESS_PACIENTE_FIELDS)}
        FROM EqCtaCli
        WHERE TRIM(nomcli) != ''
        ORDER BY codcli
        """
        
        self.access_cursor.execute(query)
        columnas = [desc[0] for desc in self.access_cursor.description]
        
        pacientes = []
        for row in tqdm(self.access_cursor.fetchall(), desc="Leyendo Access"):
            paciente = dict(zip(columnas, row))
            
            # Normalizar datos críticos
            paciente['codcli_norm'] = DataUtils.normalizar_cedula(paciente['codcli'])
            paciente['nomcli_norm'] = DataUtils.normalizar_nombre(paciente['nomcli'])
            paciente['cedula_norm'] = DataUtils.normalizar_cedula(paciente.get('cedula'))
            paciente['ruc_norm'] = DataUtils.normalizar_cedula(paciente.get('ruc'))
            
            # Extraer iniciales para matching rápido
            paciente['iniciales'] = DataUtils.extraer_iniciales(paciente['nomcli'])
            
            pacientes.append(paciente)
        
        logger.info(f"✅ Obtenidos {len(pacientes)} pacientes de Access")
        return pacientes
    
    def obtener_pacientes_postgresql(self) -> List[Dict]:
        """Obtener todos los pacientes de PostgreSQL"""
        logger.info("Obteniendo pacientes de PostgreSQL...")
        
        query = f"""
        SELECT {', '.join(Config.PG_PACIENTE_FIELDS)}
        FROM paciente
        ORDER BY id
        """
        
        self.pg_cursor.execute(query)
        pacientes = []
        
        for row in tqdm(self.pg_cursor.fetchall(), desc="Leyendo PostgreSQL"):
            paciente = dict(row)
            
            # Normalizar datos
            paciente['nombre_norm'] = DataUtils.normalizar_nombre(paciente['nombre'])
            paciente['cedula_norm'] = DataUtils.normalizar_cedula(paciente['cedula'])
            
            # Extraer iniciales
            paciente['iniciales'] = DataUtils.extraer_iniciales(paciente['nombre'])
            
            pacientes.append(paciente)
        
        logger.info(f"✅ Obtenidos {len(pacientes)} pacientes de PostgreSQL")
        return pacientes
    
    def encontrar_coincidencias_por_cedula(self, paciente_access: Dict, pacientes_pg: List[Dict]) -> List[Dict]:
        """Buscar coincidencias por cédula/RUC"""
        coincidencias = []
        
        # Opción 1: cédula de Access coincide con cédula de PostgreSQL
        if paciente_access['cedula_norm']:
            for pg in pacientes_pg:
                if pg['cedula_norm'] and pg['cedula_norm'] == paciente_access['cedula_norm']:
                    coincidencias.append({
                        'paciente_pg': pg,
                        'criterio': 'cedula_igual',
                        'confianza': 1.0
                    })
        
        # Opción 2: RUC de Access (10 dígitos) coincide con cédula de PostgreSQL
        if paciente_access['ruc_norm'] and len(paciente_access['ruc_norm']) == 10:
            for pg in pacientes_pg:
                if pg['cedula_norm'] and pg['cedula_norm'] == paciente_access['ruc_norm']:
                    coincidencias.append({
                        'paciente_pg': pg,
                        'criterio': 'ruc_como_cedula',
                        'confianza': 0.95
                    })
        
        # Opción 3: código de Access (si es numérico) coincide con cédula de PostgreSQL
        if paciente_access['codcli_norm'] and paciente_access['codcli_norm'].isdigit():
            for pg in pacientes_pg:
                if pg['cedula_norm'] and pg['cedula_norm'] == paciente_access['codcli_norm']:
                    coincidencias.append({
                        'paciente_pg': pg,
                        'criterio': 'codcli_como_cedula',
                        'confianza': 0.9
                    })
        
        return coincidencias
    
    def encontrar_coincidencias_por_nombre(self, paciente_access: Dict, pacientes_pg: List[Dict]) -> List[Dict]:
        """Buscar coincidencias por nombre"""
        coincidencias = []
        
        # Filtrar por iniciales primero para optimizar
        pacientes_filtrados = [p for p in pacientes_pg 
                             if p['iniciales'] == paciente_access['iniciales']]
        
        if not pacientes_filtrados:
            pacientes_filtrados = pacientes_pg
        
        nombre_access_norm = paciente_access['nomcli_norm']
        
        for pg in pacientes_filtrados:
            nombre_pg_norm = pg['nombre_norm']
            
            # Match exacto después de normalizar
            if nombre_access_norm == nombre_pg_norm:
                coincidencias.append({
                    'paciente_pg': pg,
                    'criterio': 'nombre_exacto',
                    'confianza': 1.0
                })
                continue
            
            # Calcular similitud
            similitud = DataUtils.calcular_similitud(
                paciente_access['nomcli'], 
                pg['nombre']
            )
            
            if similitud >= Config.MIN_NAME_SIMILARITY:
                coincidencias.append({
                    'paciente_pg': pg,
                    'criterio': 'nombre_similar',
                    'confianza': similitud
                })
        
        # Ordenar por confianza descendente
        coincidencias.sort(key=lambda x: x['confianza'], reverse=True)
        return coincidencias
    
    def encontrar_mejor_coincidencia(self, paciente_access: Dict, pacientes_pg: List[Dict]) -> Optional[Dict]:
        """Encontrar la mejor coincidencia para un paciente de Access"""
        # 1. Buscar por cédula (más confiable)
        coincidencias_cedula = self.encontrar_coincidencias_por_cedula(paciente_access, pacientes_pg)
        
        if coincidencias_cedula:
            # Si hay match perfecto por cédula, usarlo
            for match in coincidencias_cedula:
                if match['confianza'] >= 0.95:
                    return match
        
        # 2. Buscar por nombre
        coincidencias_nombre = self.encontrar_coincidencias_por_nombre(paciente_access, pacientes_pg)
        
        if not coincidencias_nombre:
            return None
        
        # 3. Combinar y seleccionar mejor
        todas_coincidencias = coincidencias_cedula + coincidencias_nombre
        
        # Si hay múltiples coincidencias, verificar si son del mismo paciente
        if len(todas_coincidencias) > 1:
            # Agrupar por ID de PostgreSQL
            matches_por_id = {}
            for match in todas_coincidencias:
                pg_id = match['paciente_pg']['id']
                if pg_id not in matches_por_id:
                    matches_por_id[pg_id] = []
                matches_por_id[pg_id].append(match)
            
            # Seleccionar el ID con mayor confianza promedio
            mejor_id = None
            mejor_confianza_promedio = 0
            
            for pg_id, matches in matches_por_id.items():
                confianza_promedio = sum(m['confianza'] for m in matches) / len(matches)
                if confianza_promedio > mejor_confianza_promedio:
                    mejor_confianza_promedio = confianza_promedio
                    mejor_id = pg_id
            
            if mejor_id:
                # Tomar el match con mayor confianza para ese ID
                matches_del_id = matches_por_id[mejor_id]
                matches_del_id.sort(key=lambda x: x['confianza'], reverse=True)
                return matches_del_id[0]
        
        # Si solo hay una, usarla
        todas_coincidencias.sort(key=lambda x: x['confianza'], reverse=True)
        return todas_coincidencias[0] if todas_coincidencias else None
    
    def reconstruir_mapeo_completo(self):
        """Reconstruir mapeo completo"""
        logger.info("🚀 INICIANDO RECONSTRUCCIÓN DE MAPEO COMPLETO")
        
        # 1. Obtener datos
        pacientes_access = self.obtener_pacientes_access()
        pacientes_pg = self.obtener_pacientes_postgresql()
        
        logger.info(f"📊 Total pacientes: Access={len(pacientes_access)}, PostgreSQL={len(pacientes_pg)}")
        
        # 2. Crear índice rápido por iniciales
        pg_por_iniciales = {}
        for pg in pacientes_pg:
            if pg['iniciales'] not in pg_por_iniciales:
                pg_por_iniciales[pg['iniciales']] = []
            pg_por_iniciales[pg['iniciales']].append(pg)
        
        # 3. Procesar cada paciente de Access
        mapeos_encontrados = 0
        
        for i, paciente_access in enumerate(tqdm(pacientes_access, desc="Procesando pacientes")):
            # Filtrar pacientes PostgreSQL por iniciales para optimizar
            iniciales = paciente_access['iniciales']
            pacientes_pg_filtrados = pg_por_iniciales.get(iniciales, pacientes_pg)
            
            # Buscar mejor coincidencia
            mejor_match = self.encontrar_mejor_coincidencia(paciente_access, pacientes_pg_filtrados)
            
            if mejor_match:
                mapeos_encontrados += 1
                
                mapeo = {
                    'codcli_access': paciente_access['codcli'],
                    'codcli_norm': paciente_access['codcli_norm'],
                    'nombre_access': paciente_access['nomcli'],
                    'nombre_access_norm': paciente_access['nomcli_norm'],
                    'cedula_access': paciente_access.get('cedula'),
                    'ruc_access': paciente_access.get('ruc'),
                    'id_postgres': mejor_match['paciente_pg']['id'],
                    'nombre_postgres': mejor_match['paciente_pg']['nombre'],
                    'cedula_postgres': mejor_match['paciente_pg']['cedula'],
                    'criterio': mejor_match['criterio'],
                    'confianza': mejor_match['confianza'],
                    'fecha_mapeo': datetime.now()
                }
                
                self.mapeos.append(mapeo)
                
                # Verificar duplicidad
                if mejor_match['confianza'] < 0.8:
                    self.duplicados.append({
                        'paciente_access': paciente_access,
                        'match': mejor_match,
                        'razon': f'Confianza baja: {mejor_match["confianza"]:.2f}'
                    })
            else:
                self.no_encontrados.append(paciente_access)
        
        # 4. Guardar resultados
        self.guardar_resultados()
        
        logger.info(f"✅ Mapeo completado: {mapeos_encontrados}/{len(pacientes_access)} encontrados")
        logger.info(f"⚠️  No encontrados: {len(self.no_encontrados)}")
        logger.info(f"⚠️  Posibles duplicados: {len(self.duplicados)}")
        
        return self.mapeos
    
    def guardar_resultados(self):
        """Guardar resultados en base de datos y archivos"""
        # 1. Crear backup de mapeo actual
        logger.info("Creando backup del mapeo actual...")
        
        # Leer mapeo actual
        self.pg_cursor.execute("SELECT codcli_access, paciente_id FROM codcli_mapping")
        mapeo_actual = {row[0]: row[1] for row in self.pg_cursor.fetchall()}
        
        DataUtils.crear_backup_datos(
            [{'codcli_access': k, 'paciente_id': v} for k, v in mapeo_actual.items()],
            "mapeo_backup"
        )
        
        # 2. Actualizar tabla codcli_mapping
        logger.info("Actualizando tabla codcli_mapping...")
        
        # Limpiar tabla (opcional, comentar si quieres preservar)
        # self.pg_cursor.execute("TRUNCATE TABLE codcli_mapping")
        
        # Insertar nuevos mapeos
        insertados = 0
        actualizados = 0
        
        for mapeo in self.mapeos:
            # Verificar si ya existe
            self.pg_cursor.execute(
                "SELECT paciente_id FROM codcli_mapping WHERE codcli_access = %s",
                (mapeo['codcli_access'],)
            )
            existe = self.pg_cursor.fetchone()
            
            if existe:
                # Actualizar
                self.pg_cursor.execute(
                    """
                    UPDATE codcli_mapping 
                    SET paciente_id = %s, fecha_mapeo = %s
                    WHERE codcli_access = %s
                    """,
                    (mapeo['id_postgres'], mapeo['fecha_mapeo'], mapeo['codcli_access'])
                )
                actualizados += 1
            else:
                # Insertar nuevo
                self.pg_cursor.execute(
                    """
                    INSERT INTO codcli_mapping (codcli_access, paciente_id, fecha_mapeo)
                    VALUES (%s, %s, %s)
                    """,
                    (mapeo['codcli_access'], mapeo['id_postgres'], mapeo['fecha_mapeo'])
                )
                insertados += 1
        
        self.pg_conn.commit()
        
        # 3. Guardar archivos de reporte
        self.generar_reportes()
        
        logger.info(f"✅ Base de datos actualizada: {insertados} insertados, {actualizados} actualizados")
    
    def generar_reportes(self):
        """Generar reportes detallados"""
        import pandas as pd
        
        # Reporte de mapeos
        df_mapeos = pd.DataFrame(self.mapeos)
        reporte_path = Config.LOG_DIR / f"mapeo_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        with pd.ExcelWriter(reporte_path, engine='openpyxl') as writer:
            df_mapeos.to_excel(writer, sheet_name='Mapeos', index=False)
            
            # Reporte de no encontrados
            if self.no_encontrados:
                df_no_encontrados = pd.DataFrame(self.no_encontrados)
                df_no_encontrados.to_excel(writer, sheet_name='No_Encontrados', index=False)
            
            # Reporte de duplicados
            if self.duplicados:
                df_duplicados = pd.DataFrame([
                    {
                        'codcli_access': d['paciente_access']['codcli'],
                        'nombre_access': d['paciente_access']['nomcli'],
                        'id_postgres': d['match']['paciente_pg']['id'],
                        'nombre_postgres': d['match']['paciente_pg']['nombre'],
                        'confianza': d['match']['confianza'],
                        'razon': d['razon']
                    }
                    for d in self.duplicados
                ])
                df_duplicados.to_excel(writer, sheet_name='Duplicados', index=False)
            
            # Estadísticas
            stats = {
                'Total pacientes Access': len(self.mapeos) + len(self.no_encontrados),
                'Mapeos encontrados': len(self.mapeos),
                'No encontrados': len(self.no_encontrados),
                'Tasa de éxito': f"{(len(self.mapeos) / (len(self.mapeos) + len(self.no_encontrados)) * 100):.2f}%",
                'Posibles duplicados': len(self.duplicados),
                'Confianza promedio': f"{sum(m['confianza'] for m in self.mapeos) / len(self.mapeos):.2f}" if self.mapeos else "N/A"
            }
            
            df_stats = pd.DataFrame(list(stats.items()), columns=['Métrica', 'Valor'])
            df_stats.to_excel(writer, sheet_name='Estadísticas', index=False)
        
        logger.info(f"✅ Reporte generado: {reporte_path}")
        
        # Reporte HTML
        reporte_data = {
            'resumen': stats,
            'errores': [],
            'advertencias': [
                f"{len(self.no_encontrados)} pacientes no encontrados",
                f"{len(self.duplicados)} posibles duplicados con confianza < 80%"
            ] if self.no_encontrados or self.duplicados else []
        }
        
        DataUtils.generar_reporte_html(reporte_data, "Reporte de Reconstrucción de Mapeo")

def main():
    """Función principal"""
    reconstructor = ReconstructorMapeo()
    
    try:
        # Conectar
        reconstructor.conectar_bases()
        
        # Reconstruir mapeo
        mapeos = reconstructor.reconstruir_mapeo_completo()
        
        print(f"\n{'='*60}")
        print("🎯 RECONSTRUCCIÓN DE MAPEO COMPLETADA")
        print(f"{'='*60}")
        print(f"✅ Mapeos encontrados: {len(mapeos)}")
        print(f"⚠️  No encontrados: {len(reconstructor.no_encontrados)}")
        print(f"⚠️  Duplicados a revisar: {len(reconstructor.duplicados)}")
        
        if reconstructor.no_encontrados:
            print(f"\n📋 Primeros 5 no encontrados:")
            for i, p in enumerate(reconstructor.no_encontrados[:5]):
                print(f"  {i+1}. {p['codcli']} - {p['nomcli']}")
        
        print(f"\n📊 Ver reportes en: {Config.LOG_DIR}")
        
    except Exception as e:
        logger.error(f"Error durante la reconstrucción: {e}", exc_info=True)
        print(f"❌ Error: {e}")
    finally:
        reconstructor.desconectar()

if __name__ == "__main__":
    main()