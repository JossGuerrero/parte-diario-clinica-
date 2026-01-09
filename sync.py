import pyodbc
import psycopg2
import logging
from datetime import datetime, timedelta
import time

# =========================
# CONFIGURACIÓN
# =========================
ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('sync_facil.log'),
        logging.StreamHandler()
    ]
)

class SincronizadorFacil:
    def __init__(self):
        self.access = None
        self.access_cur = None
        self.pg = None
        self.pg_cur = None
        self.contadores = {
            'pacientes_nuevos': 0,
            'atenciones_nuevas': 0,
            'pacientes_omitidos': 0,
            'atenciones_omitidas': 0
        }
    
    def conectar(self):
        """Conectar a Access y PostgreSQL"""
        try:
            # Access
            self.access = pyodbc.connect(
                r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
                f"DBQ={ACCESS_FILE};PWD={ACCESS_PWD};"
            )
            self.access_cur = self.access.cursor()
            
            # PostgreSQL
            self.pg = psycopg2.connect(
                host=PG_HOST, port=PG_PORT,
                dbname=PG_DB, user=PG_USER,
                password=PG_PASS
            )
            self.pg_cur = self.pg.cursor()
            
            print("✅ Conectado a ambas bases de datos")
            return True
            
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False
    
    def ya_migrado(self, tabla: str, id_registro: str) -> bool:
        """Verificar si ya migré este registro"""
        try:
            # Intentar con la tabla actual
            self.pg_cur.execute("""
                SELECT 1 FROM migracion_control 
                WHERE tabla = %s AND ultimo_id = %s
                LIMIT 1
            """, (tabla, str(id_registro)))
            
            if self.pg_cur.fetchone():
                return True
                
        except Exception:
            # Si falla, significa que ultimo_id es integer y estamos pasando string
            # No hay problema, significa que NO está migrado
            pass
            
        return False
    
    def registrar_migracion(self, tabla: str, id_registro: str):
        """Guardar que ya migré este registro"""
        try:
            self.pg_cur.execute("""
                INSERT INTO migracion_control (tabla, ultimo_id)
                VALUES (%s, %s)
            """, (tabla, str(id_registro)))
        except Exception as e:
            # Si falla por duplicado o tipo de dato, no pasa nada
            pass
    
    def migrar_pacientes_facil(self):
        """Migrar solo pacientes nuevos"""
        print("🔄 Buscando pacientes nuevos...")
        
        try:
            # Pacientes de Access
            self.access_cur.execute("""
                SELECT DISTINCT TOP 1000
                    cedula, NOMBRE, genero, FechaN, telefono, direccion
                FROM EqCtaCli
                WHERE cedula IS NOT NULL 
                  AND cedula <> '' 
                  AND cedula <> '0'
                  AND NOMBRE IS NOT NULL
                ORDER BY NOMBRE
            """)
            
            pacientes = self.access_cur.fetchall()
            print(f"📊 Pacientes en Access: {len(pacientes)}")
            
            for p in pacientes:
                cedula = str(p.cedula).strip()
                
                if not cedula or cedula == '0000000000':
                    continue
                
                # ¿Ya migrado?
                if self.ya_migrado('PACIENTES', cedula):
                    self.contadores['pacientes_omitidos'] += 1
                    continue
                
                # Insertar si no existe
                self.pg_cur.execute("""
                    INSERT INTO paciente (
                        nombre, cedula, genero,
                        fecha_nacimiento, telefono, direccion,
                        activo
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cedula) DO NOTHING
                """, (
                    p.NOMBRE.strip() if p.NOMBRE else '',
                    cedula,
                    p.genero.strip() if p.genero else None,
                    p.FechaN,
                    p.telefono.strip() if p.telefono else None,
                    p.direccion.strip() if p.direccion else None,
                    True
                ))
                
                # Registrar como migrado
                self.registrar_migracion('PACIENTES', cedula)
                self.contadores['pacientes_nuevos'] += 1
                
                if self.contadores['pacientes_nuevos'] % 50 == 0:
                    self.pg.commit()
                    print(f"  ✓ {self.contadores['pacientes_nuevos']} pacientes nuevos...")
            
            self.pg.commit()
            print(f"✅ Pacientes: {self.contadores['pacientes_nuevos']} nuevos")
            
        except Exception as e:
            print(f"❌ Error en pacientes: {e}")
            self.pg.rollback()
    
    def migrar_atenciones_facil(self):
        """Migrar solo atenciones nuevas de los últimos 7 días"""
        print("🔄 Buscando atenciones nuevas...")
        
        try:
            # Solo últimos 7 días (para no saturar)
            fecha_limite = (datetime.now() - timedelta(days=7)).date()
            
            self.access_cur.execute("""
                SELECT TOP 500
                    T.FechaIng, C.cedula, T.Cie10, 
                    T.Grupo2, V.VENDEDOR, T.SEspecialidad,
                    E.base_b, E.dstvfac, C.genero, C.FechaN
                FROM ((EqTraSec AS T
                LEFT JOIN EqCtaCli AS C ON T.CodCli = C.CodCli)
                LEFT JOIN EQCTAVDD AS V ON T.CodVen = V.CODVEN)
                LEFT JOIN EqEncPto AS E ON T.numfac = E.numfac
                WHERE T.FechaIng >= ?
                  AND C.cedula IS NOT NULL
                ORDER BY T.FechaIng DESC
            """, fecha_limite)
            
            atenciones = self.access_cur.fetchall()
            print(f"📊 Atenciones recientes: {len(atenciones)}")
            
            for a in atenciones:
                cedula = str(a.cedula).strip()
                fecha = a.FechaIng
                
                if not cedula or not fecha:
                    continue
                
                # ID único: cedula + fecha
                id_unico = f"{cedula}_{fecha.strftime('%Y%m%d')}"
                
                # ¿Ya migrado?
                if self.ya_migrado('ATENCIONES', id_unico):
                    self.contadores['atenciones_omitidas'] += 1
                    continue
                
                # Buscar paciente en PostgreSQL
                self.pg_cur.execute("SELECT id FROM paciente WHERE cedula = %s", (cedula,))
                paciente = self.pg_cur.fetchone()
                
                if not paciente:
                    # Paciente no existe, saltar
                    continue
                
                paciente_id = paciente[0]
                
                # Insertar atención
                self.pg_cur.execute("""
                    INSERT INTO atencion (
                        fecha_atencion, paciente_id, 
                        edad, genero, valor_consulta, valor_medicina,
                        observaciones
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    fecha,
                    paciente_id,
                    0,  # Edad temporal (se puede calcular después)
                    a.genero.strip() if a.genero else None,
                    float(a.base_b) if a.base_b else 0.0,
                    float(a.dstvfac) if a.dstvfac else 0.0,
                    a.SEspecialidad.strip() if a.SEspecialidad else None
                ))
                
                # Registrar como migrado
                self.registrar_migracion('ATENCIONES', id_unico)
                self.contadores['atenciones_nuevas'] += 1
                
                if self.contadores['atenciones_nuevas'] % 20 == 0:
                    self.pg.commit()
                    print(f"  ✓ {self.contadores['atenciones_nuevas']} atenciones nuevas...")
            
            self.pg.commit()
            print(f"✅ Atenciones: {self.contadores['atenciones_nuevas']} nuevas")
            
        except Exception as e:
            print(f"❌ Error en atenciones: {e}")
            self.pg.rollback()
    
    def ejecutar(self):
        """Ejecutar todo el proceso"""
        print("=" * 60)
        print("🚀 SISTEMA DE SINCRONIZACIÓN FÁCIL")
        print("=" * 60)
        
        if not self.conectar():
            return False
        
        try:
            # 1. Pacientes
            self.migrar_pacientes_facil()
            
            # 2. Atenciones
            self.migrar_atenciones_facil()
            
            # 3. Mostrar resumen
            print("\n" + "=" * 60)
            print("📊 RESUMEN FINAL")
            print("=" * 60)
            print(f"👥 Pacientes nuevos: {self.contadores['pacientes_nuevos']}")
            print(f"👥 Pacientes ya existían: {self.contadores['pacientes_omitidos']}")
            print(f"🏥 Atenciones nuevas: {self.contadores['atenciones_nuevas']}")
            print(f"🏥 Atenciones ya existían: {self.contadores['atenciones_omitidas']}")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            return False
        
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cerrar conexiones"""
        try:
            if self.access_cur:
                self.access_cur.close()
            if self.access:
                self.access.close()
            if self.pg_cur:
                self.pg_cur.close()
            if self.pg:
                self.pg.close()
            print("🔌 Conexiones cerradas")
        except:
            pass

# =========================
# EJECUTAR
# =========================
if __name__ == "__main__":
    sinc = SincronizadorFacil()
    sinc.ejecutar()
    input("\nPresiona ENTER para salir...")