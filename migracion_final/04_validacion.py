"""
VALIDACIÓN Y REPORTES DEL SISTEMA
Objetivo: Validar integridad de datos y generar reportes
"""
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from config import Config
from utils import DataUtils, setup_logging

logger = setup_logging("validacion")

class ValidadorDatos:
    """Validador de integridad de datos"""
    
    def __init__(self):
        self.pg_conn = None
        self.pg_cursor = None
        self.resultados_validacion = {}
        
    def conectar(self):
        """Conectar a PostgreSQL"""
        self.pg_conn = psycopg2.connect(**Config.POSTGRES_CONFIG)
        self.pg_cursor = self.pg_conn.cursor(cursor_factory=DictCursor)
        logger.info("✅ Conectado a PostgreSQL para validación")
    
    def validar_integridad_completa(self):
        """Ejecutar todas las validaciones"""
        logger.info("🔍 INICIANDO VALIDACIÓN COMPLETA DEL SISTEMA")
        
        validaciones = [
            ("Pacientes sin atenciones", self.validar_pacientes_sin_atenciones),
            ("Atenciones sin paciente", self.validar_atenciones_sin_paciente),
            ("Atenciones sin médico", self.validar_atenciones_sin_medico),
            ("Mapeo incompleto", self.validar_mapeo_incompleto),
            ("Datos duplicados", self.validar_duplicados),
            ("Consistencia fechas", self.validar_consistencia_fechas),
            ("Referencias rotas", self.validar_referencias_rotas),
            ("Estadísticas básicas", self.validar_estadisticas_basicas),
        ]
        
        for nombre, funcion in validaciones:
            try:
                logger.info(f"Validando: {nombre}")
                resultado = funcion()
                self.resultados_validacion[nombre] = resultado
                estado = "✅" if not resultado.get('problemas') else "⚠️"
                logger.info(f"  {estado} {nombre}: {resultado.get('resumen', '')}")
            except Exception as e:
                logger.error(f"❌ Error validando {nombre}: {e}")
                self.resultados_validacion[nombre] = {
                    'error': str(e),
                    'estado': 'error'
                }
        
        self.generar_reporte_completo()
        return self.resultados_validacion
    
    def validar_pacientes_sin_atenciones(self) -> Dict:
        """Validar pacientes que no tienen atenciones"""
        query = """
        SELECT p.id, p.nombre, p.cedula
        FROM paciente p
        LEFT JOIN atencion a ON p.id = a.paciente_id
        WHERE a.id IS NULL
        AND p.activo = true
        ORDER BY p.id
        """
        
        self.pg_cursor.execute(query)
        pacientes = self.pg_cursor.fetchall()
        
        return {
            'total': len(pacientes),
            'problemas': len(pacientes) > 0,
            'resumen': f"{len(pacientes)} pacientes sin atenciones",
            'detalle': pacientes[:20] if pacientes else [],
            'muestra_completa': len(pacientes) <= 20
        }
    
    def validar_atenciones_sin_paciente(self) -> Dict:
        """Validar atenciones sin paciente válido"""
        query = """
        SELECT a.id, a.fecha_atencion, a.observaciones
        FROM atencion a
        LEFT JOIN paciente p ON a.paciente_id = p.id
        WHERE p.id IS NULL OR p.activo = false
        ORDER BY a.fecha_atencion
        """
        
        self.pg_cursor.execute(query)
        atenciones = self.pg_cursor.fetchall()
        
        return {
            'total': len(atenciones),
            'problemas': len(atenciones) > 0,
            'resumen': f"{len(atenciones)} atenciones sin paciente válido",
            'detalle': atenciones[:20] if atenciones else [],
            'muestra_completa': len(atenciones) <= 20
        }
    
    def validar_mapeo_incompleto(self) -> Dict:
        """Validar pacientes sin mapeo a Access"""
        query = """
        SELECT 
            p.id, p.nombre, p.cedula,
            COUNT(a.id) as total_atenciones
        FROM paciente p
        LEFT JOIN codcli_mapping m ON p.id = m.paciente_id
        LEFT JOIN atencion a ON p.id = a.paciente_id
        WHERE m.codcli_access IS NULL
        AND p.activo = true
        GROUP BY p.id, p.nombre, p.cedula
        HAVING COUNT(a.id) > 0
        ORDER BY total_atenciones DESC
        """
        
        self.pg_cursor.execute(query)
        pacientes = self.pg_cursor.fetchall()
        
        return {
            'total': len(pacientes),
            'problemas': len(pacientes) > 0,
            'resumen': f"{len(pacientes)} pacientes activos sin mapeo a Access",
            'detalle': pacientes[:10] if pacientes else [],
            'muestra_completa': len(pacientes) <= 10
        }
    
    def validar_duplicados(self) -> Dict:
        """Validar datos duplicados"""
        duplicados = {}
        
        # 1. Pacientes duplicados por nombre similar
        query_nombres = """
        SELECT 
            LOWER(unaccent(nombre)) as nombre_norm,
            COUNT(*) as cantidad,
            ARRAY_AGG(id) as ids,
            ARRAY_AGG(cedula) as cedulas
        FROM paciente
        WHERE nombre IS NOT NULL
        AND TRIM(nombre) != ''
        GROUP BY LOWER(unaccent(nombre))
        HAVING COUNT(*) > 1
        ORDER BY cantidad DESC
        LIMIT 20
        """
        
        self.pg_cursor.execute(query_nombres)
        duplicados['por_nombre'] = self.pg_cursor.fetchall()
        
        # 2. Atenciones duplicadas (misma fecha, paciente y médico)
        query_atenciones = """
        SELECT 
            fecha_atencion, paciente_id, medico_id,
            COUNT(*) as cantidad,
            ARRAY_AGG(id) as ids
        FROM atencion
        WHERE fecha_atencion IS NOT NULL
        AND paciente_id IS NOT NULL
        GROUP BY fecha_atencion, paciente_id, medico_id
        HAVING COUNT(*) > 1
        ORDER BY cantidad DESC
        LIMIT 10
        """
        
        self.pg_cursor.execute(query_atenciones)
        duplicados['por_atencion'] = self.pg_cursor.fetchall()
        
        total_duplicados = len(duplicados['por_nombre']) + len(duplicados['por_atencion'])
        
        return {
            'total': total_duplicados,
            'problemas': total_duplicados > 0,
            'resumen': f"{total_duplicados} grupos de duplicados encontrados",
            'detalle': duplicados,
            'muestra_completa': True
        }
    
    def validar_estadisticas_basicas(self) -> Dict:
        """Obtener estadísticas básicas del sistema"""
        estadisticas = {}
        
        consultas = [
            ('total_pacientes', "SELECT COUNT(*) FROM paciente WHERE activo = true"),
            ('total_atenciones', "SELECT COUNT(*) FROM atencion"),
            ('total_medicos', "SELECT COUNT(*) FROM medico WHERE activo = true"),
            ('total_mapeos', "SELECT COUNT(*) FROM codcli_mapping"),
            ('atenciones_ultimo_mes', """
                SELECT COUNT(*) FROM atencion 
                WHERE fecha_atencion >= CURRENT_DATE - INTERVAL '30 days'
            """),
            ('promedio_atenciones_dia', """
                SELECT AVG(daily_count) FROM (
                    SELECT fecha_atencion, COUNT(*) as daily_count
                    FROM atencion
                    WHERE fecha_atencion IS NOT NULL
                    GROUP BY fecha_atencion
                ) daily_counts
            """),
            ('pacientes_con_mas_atenciones', """
                SELECT p.nombre, COUNT(a.id) as atenciones
                FROM paciente p
                JOIN atencion a ON p.id = a.paciente_id
                GROUP BY p.id, p.nombre
                ORDER BY atenciones DESC
                LIMIT 5
            """),
            ('medicos_con_mas_atenciones', """
                SELECT m.nombre, COUNT(a.id) as atenciones
                FROM medico m
                JOIN atencion a ON m.id = a.medico_id
                WHERE m.activo = true
                GROUP BY m.id, m.nombre
                ORDER BY atenciones DESC
                LIMIT 5
            """)
        ]
        
        for nombre, query in consultas:
            try:
                self.pg_cursor.execute(query)
                resultado = self.pg_cursor.fetchone()
                
                if resultado:
                    if isinstance(resultado, dict) and len(resultado) == 1:
                        estadisticas[nombre] = list(resultado.values())[0]
                    else:
                        estadisticas[nombre] = resultado[0] if isinstance(resultado, tuple) else resultado
            except Exception as e:
                logger.warning(f"Error obteniendo estadística {nombre}: {e}")
                estadisticas[nombre] = None
        
        # Calcular cobertura de migración
        if estadisticas.get('total_atenciones') and estadisticas.get('total_pacientes'):
            estadisticas['cobertura_estimada'] = (
                estadisticas['total_atenciones'] / 
                (estadisticas['total_pacientes'] * 3) * 100  # Estimación
            )
        
        return {
            'total': len(estadisticas),
            'problemas': False,
            'resumen': "Estadísticas del sistema",
            'detalle': estadisticas,
            'muestra_completa': True
        }
    
    def generar_reporte_completo(self):
        """Generar reporte completo de validación"""
        logger.info("Generando reporte de validación...")
        
        # 1. Reporte en texto
        reporte_texto = self.generar_reporte_texto()
        
        # 2. Reporte en Excel
        reporte_excel = self.generar_reporte_excel()
        
        # 3. Gráficos (opcional)
        self.generar_graficos()
        
        logger.info(f"✅ Reporte de validación generado:")
        logger.info(f"   📄 Texto: {reporte_texto}")
        logger.info(f"   📊 Excel: {reporte_excel}")
        
        return reporte_texto, reporte_excel
    
    def generar_reporte_texto(self):
        """Generar reporte en formato texto"""
        from datetime import datetime
        
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = Config.LOG_DIR / f"validacion_completa_{fecha}.txt"
        
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("REPORTE DE VALIDACIÓN DEL SISTEMA\n")
            f.write("="*70 + "\n\n")
            f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Resumen ejecutivo
            problemas_totales = sum(
                1 for v in self.resultados_validacion.values() 
                if isinstance(v, dict) and v.get('problemas')
            )
            
            f.write(f"📊 RESUMEN EJECUTIVO\n")
            f.write(f"   Total validaciones: {len(self.resultados_validacion)}\n")
            f.write(f"   Validaciones con problemas: {problemas_totales}\n")
            f.write(f"   Estado general: {'⚠️ REVISIÓN NECESARIA' if problemas_totales > 0 else '✅ ÓPTIMO'}\n\n")
            
            # Detalle por validación
            for nombre, resultado in self.resultados_validacion.items():
                if not isinstance(resultado, dict):
                    continue
                
                estado = "✅" if not resultado.get('problemas') else "⚠️"
                f.write(f"{estado} {nombre}\n")
                f.write(f"   {resultado.get('resumen', 'Sin resumen')}\n")
                
                if resultado.get('detalle'):
                    f.write(f"   Detalle:\n")
                    for item in resultado['detalle']:
                        f.write(f"     - {item}\n")
                
                if resultado.get('error'):
                    f.write(f"   Error: {resultado['error']}\n")
                
                f.write("\n")
        
        return ruta
    
    def generar_reporte_excel(self):
        """Generar reporte en Excel con múltiples hojas"""
        from datetime import datetime
        import pandas as pd
        
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = Config.LOG_DIR / f"validacion_completa_{fecha}.xlsx"
        
        with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
            # Hoja 1: Resumen
            resumen_data = []
            for nombre, resultado in self.resultados_validacion.items():
                if isinstance(resultado, dict):
                    resumen_data.append({
                        'Validación': nombre,
                        'Estado': '✅ OK' if not resultado.get('problemas') else '⚠️ PROBLEMA',
                        'Resumen': resultado.get('resumen', ''),
                        'Total': resultado.get('total', 0),
                        'Error': resultado.get('error', '')
                    })
            
            df_resumen = pd.DataFrame(resumen_data)
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hoja 2: Estadísticas
            if 'Estadísticas básicas' in self.resultados_validacion:
                stats = self.resultados_validacion['Estadísticas básicas'].get('detalle', {})
                if stats:
                    df_stats = pd.DataFrame(list(stats.items()), columns=['Métrica', 'Valor'])
                    df_stats.to_excel(writer, sheet_name='Estadísticas', index=False)
            
            # Hoja 3: Problemas detallados
            problemas_data = []
            for nombre, resultado in self.resultados_validacion.items():
                if isinstance(resultado, dict) and resultado.get('problemas') and resultado.get('detalle'):
                    for item in resultado['detalle']:
                        if isinstance(item, (list, tuple)):
                            problemas_data.append([nombre] + list(item))
                        elif isinstance(item, dict):
                            problemas_data.append([nombre] + list(item.values()))
                        else:
                            problemas_data.append([nombre, str(item)])
            
            if problemas_data:
                # Determinar máximo número de columnas
                max_cols = max(len(row) for row in problemas_data)
                columnas = ['Validación'] + [f'Dato_{i+1}' for i in range(max_cols-1)]
                
                df_problemas = pd.DataFrame(problemas_data, columns=columnas[:max_cols])
                df_problemas.to_excel(writer, sheet_name='Problemas', index=False)
        
        return ruta
    
    def generar_graficos(self):
        """Generar gráficos del sistema"""
        try:
            # Datos para gráficos
            query = """
            SELECT 
                DATE_TRUNC('month', fecha_atencion) as mes,
                COUNT(*) as atenciones
            FROM atencion
            WHERE fecha_atencion IS NOT NULL
            GROUP BY mes
            ORDER BY mes
            """
            
            self.pg_cursor.execute(query)
            datos = self.pg_cursor.fetchall()
            
            if len(datos) < 2:
                return
            
            # Preparar datos
            meses = [d[0].strftime('%Y-%m') for d in datos]
            atenciones = [d[1] for d in datos]
            
            # Crear gráfico
            plt.figure(figsize=(12, 6))
            plt.plot(meses, atenciones, marker='o', linewidth=2)
            plt.title('Evolución de Atenciones por Mes', fontsize=14, fontweight='bold')
            plt.xlabel('Mes', fontsize=12)
            plt.ylabel('Número de Atenciones', fontsize=12)
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Guardar gráfico
            ruta_grafico = Config.LOG_DIR / f"grafico_atenciones_{datetime.now().strftime('%Y%m%d')}.png"
            plt.savefig(ruta_grafico, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📈 Gráfico generado: {ruta_grafico}")
            
        except Exception as e:
            logger.warning(f"No se pudo generar gráfico: {e}")

def main():
    """Función principal de validación"""
    print("\n" + "="*60)
    print("🔍 SISTEMA DE VALIDACIÓN DE DATOS")
    print("="*60)
    
    validador = ValidadorDatos()
    
    try:
        # Conectar
        validador.conectar()
        
        # Ejecutar validación completa
        resultados = validador.validar_integridad_completa()
        
        # Mostrar resumen
        print("\n📊 RESUMEN DE VALIDACIÓN:")
        print("-" * 40)
        
        problemas_totales = 0
        for nombre, resultado in resultados.items():
            if isinstance(resultado, dict):
                estado = "✅" if not resultado.get('problemas') else "⚠️"
                print(f"{estado} {nombre}: {resultado.get('resumen', '')}")
                
                if resultado.get('problemas'):
                    problemas_totales += 1
        
        print("\n" + "="*60)
        if problemas_totales == 0:
            print("🎯 SISTEMA VALIDADO EXITOSAMENTE - SIN PROBLEMAS")
        else:
            print(f"⚠️  SE ENCONTRARON {problemas_totales} ÁREAS QUE REQUIEREN ATENCIÓN")
        print("="*60)
        
        print(f"\n📄 Los reportes detallados están en: {Config.LOG_DIR}")
        
    except Exception as e:
        print(f"❌ Error durante la validación: {e}")
        logger.error(f"Error en validación: {e}", exc_info=True)
    finally:
        if validador.pg_cursor:
            validador.pg_cursor.close()
        if validador.pg_conn:
            validador.pg_conn.close()

if __name__ == "__main__":
    main()