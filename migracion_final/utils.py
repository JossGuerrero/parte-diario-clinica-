import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from unidecode import unidecode
from difflib import SequenceMatcher
import json
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

class DataUtils:
    """Utilidades para manipulación de datos"""
    
    @staticmethod
    def normalizar_nombre(nombre: str) -> str:
        """Normalizar nombre para comparación"""
        if not nombre or not isinstance(nombre, str):
            return ""
        
        # Convertir a mayúsculas, quitar espacios
        nombre = nombre.strip().upper()
        
        # Remover acentos y caracteres especiales
        nombre = unidecode(nombre)
        
        # Remover múltiples espacios
        nombre = re.sub(r'\s+', ' ', nombre)
        
        # Remover puntos, comas, etc (pero mantener letras y números)
        nombre = re.sub(r'[^\w\s]', '', nombre)
        
        return nombre
    
    @staticmethod
    def normalizar_cedula(cedula: Any) -> str:
        """Normalizar cédula/RUC"""
        if not cedula:
            return ""
        
        cedula = str(cedula).strip()
        
        # Remover espacios, guiones, puntos
        cedula = re.sub(r'[\s\-\.]', '', cedula)
        
        # Si es un código de Access tipo "0000000003", mantener
        if cedula.isdigit() and len(cedula) <= 20:
            return cedula
        
        # Si parece ser una cédula ecuatoriana (10 dígitos)
        if cedula.isdigit() and len(cedula) == 10:
            return cedula
        
        return cedula
    
    @staticmethod
    def calcular_similitud(str1: str, str2: str) -> float:
        """Calcular similitud entre dos strings (0-1)"""
        if not str1 or not str2:
            return 0.0
        
        # Normalizar ambos
        norm1 = DataUtils.normalizar_nombre(str1)
        norm2 = DataUtils.normalizar_nombre(str2)
        
        # Si son iguales después de normalizar
        if norm1 == norm2:
            return 1.0
        
        # Calcular ratio de similitud
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    @staticmethod
    def extraer_iniciales(nombre: str) -> str:
        """Extraer iniciales del nombre"""
        if not nombre:
            return ""
        
        palabras = DataUtils.normalizar_nombre(nombre).split()
        if len(palabras) >= 2:
            return f"{palabras[0][0]}{palabras[-1][0]}"
        elif palabras:
            return palabras[0][0] if len(palabras[0]) > 0 else ""
        return ""
    
    @staticmethod
    def parsear_fecha_access(fecha_access: Any) -> Optional[datetime]:
        """Parsear fechas de Access que tienen formato extraño"""
        if not fecha_access:
            return None
        
        try:
            # Access usa fechas con 1899-12-30 como base para horas
            if isinstance(fecha_access, datetime):
                # Si la fecha es 1899-12-30, probablemente es solo hora
                if fecha_access.year == 1899 and fecha_access.month == 12 and fecha_access.day == 30:
                    return None
                return fecha_access
            
            # Si es string, intentar parsear
            if isinstance(fecha_access, str):
                # Formatos comunes
                formats = [
                    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
                    "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(fecha_access, fmt)
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parseando fecha {fecha_access}: {e}")
            return None
    
    @staticmethod
    def crear_backup_datos(datos: List[Dict], nombre_archivo: str):
        """Crear backup de datos en JSON"""
        backup_path = Config.BACKUP_DIR / f"{nombre_archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, default=str, ensure_ascii=False)
        
        logger.info(f"Backup creado: {backup_path}")
        return backup_path
    
    @staticmethod
    def cargar_backup(archivo_pattern: str) -> Optional[List[Dict]]:
        """Cargar backup más reciente"""
        backups = list(Config.BACKUP_DIR.glob(f"{archivo_pattern}_*.json"))
        if not backups:
            return None
        
        latest = max(backups, key=lambda x: x.stat().st_mtime)
        
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def generar_reporte_html(reporte_data: Dict, titulo: str = "Reporte de Migración"):
        """Generar reporte HTML detallado"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{titulo}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 15px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; }}
                .success {{ color: green; }}
                .warning {{ color: orange; }}
                .error {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{titulo}</h1>
                <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """
        
        # Resumen ejecutivo
        if "resumen" in reporte_data:
            html += f"""
            <div class="section">
                <h2>📊 Resumen Ejecutivo</h2>
                <table>
                    <tr><th>Métrica</th><th>Valor</th><th>Estado</th></tr>
            """
            for metrica, valor in reporte_data["resumen"].items():
                estado = "✅" if "completado" in metrica.lower() or "éxito" in metrica.lower() else "📊"
                html += f"<tr><td>{metrica}</td><td>{valor}</td><td>{estado}</td></tr>"
            html += "</table></div>"
        
        # Errores
        if "errores" in reporte_data and reporte_data["errores"]:
            html += f"""
            <div class="section">
                <h2 class="error">🚨 Errores ({len(reporte_data['errores'])})</h2>
                <table>
                    <tr><th>Código</th><th>Tipo</th><th>Mensaje</th><th>Detalle</th></tr>
            """
            for error in reporte_data["errores"][:50]:  # Limitar a 50
                html += f"<tr><td>{error.get('codigo', 'N/A')}</td><td>{error.get('tipo', 'Error')}</td><td>{error.get('mensaje', '')}</td><td>{error.get('detalle', '')}</td></tr>"
            html += "</table></div>"
        
        # Advertencias
        if "advertencias" in reporte_data and reporte_data["advertencias"]:
            html += f"""
            <div class="section">
                <h2 class="warning">⚠️ Advertencias ({len(reporte_data['advertencias'])})</h2>
                <ul>
            """
            for warning in reporte_data["advertencias"][:20]:
                html += f"<li>{warning}</li>"
            html += "</ul></div>"
        
        html += "</body></html>"
        
        reporte_path = Config.LOG_DIR / f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(reporte_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Reporte HTML generado: {reporte_path}")
        return reporte_path

# Configurar logging
def setup_logging(nombre_modulo: str):
    """Configurar logging para el módulo"""
    log_file = Config.LOG_DIR / f"{nombre_modulo}_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(nombre_modulo)