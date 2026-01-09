import os
from pathlib import Path

class Config:
    # Directorios
    BASE_DIR = Path(__file__).parent
    LOG_DIR = BASE_DIR / "logs"
    BACKUP_DIR = BASE_DIR / "backups"
    
    # Base de datos Access
    ACCESS_DB_PATH = r"C:\Users\jossu\OneDrive\Escritorio\Nueva carpeta (6)\tu_base.accdb"
    ACCESS_DRIVER = "{Microsoft Access Driver (*.mdb, *.accdb)}"
    
    # Base de datos PostgreSQL
    POSTGRES_CONFIG = {
        "host": "localhost",
        "database": "partes_diarios",
        "user": "postgres",
        "password": "tu_password",  # Cambiar
        "port": "5432"
    }
    
    # Configuración de migración
    BATCH_SIZE = 1000  # Registros por lote
    MAX_RETRIES = 3    # Reintentos por error
    TIMEOUT = 30       # Timeout en segundos
    
    # Umbrales de coincidencia
    MIN_NAME_SIMILARITY = 0.8  # 80% similitud para nombres
    MIN_EXACT_MATCH = 0.95     # 95% para match exacto
    
    # Campos críticos de Access
    ACCESS_PACIENTE_FIELDS = [
        "codcli", "nomcli", "cedula", "ruc", "DIRECCION", 
        "telefono", "FechaN", "sexof", "email"
    ]
    
    # Campos críticos de PostgreSQL
    PG_PACIENTE_FIELDS = [
        "id", "nombre", "cedula", "fecha_nacimiento",
        "genero", "telefono", "direccion"
    ]
    
    @classmethod
    def setup_directories(cls):
        """Crear directorios necesarios"""
        directories = [cls.LOG_DIR, cls.BACKUP_DIR]
        for directory in directories:
            directory.mkdir(exist_ok=True)
    
    @classmethod
    def get_access_connection_string(cls):
        """Generar cadena de conexión para Access"""
        return f"DRIVER={cls.ACCESS_DRIVER};DBQ={cls.ACCESS_DB_PATH};"

# Inicializar directorios
Config.setup_directories()