#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERVICIO AUTOMÁTICO DE MAPEO DE MÉDICOS
Se ejecuta periódicamente para vincular nuevas atenciones con médicos
"""

import pyodbc
import psycopg2
from datetime import datetime
import os
import shutil
import tempfile
import time
import sys

ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"

def log(msg, end="\n"):
    ahora = datetime.now().strftime("%H:%M:%S")
    print(f"[{ahora}] {msg}", end=end, flush=True)

def mapear_medicos():
    """Función que mapea médicos sin medico_id"""
    
    try:
        # Shadow copy
        temp_path = os.path.join(tempfile.gettempdir(), f"shadow_{int(time.time())}.mdb")
        shutil.copy2(ACCESS_FILE, temp_path)
        
        # Conectar
        ac = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={temp_path};PWD={ACCESS_PWD};")
        pc = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)
        
        acc_cur = ac.cursor()
        pg_cur = pc.cursor()
        
        # Contar atenciones sin médico
        pg_cur.execute("SELECT COUNT(*) FROM atencion WHERE medico_id IS NULL")
        sin_mapear = pg_cur.fetchone()[0]
        
        if sin_mapear == 0:
            return False
        
        log(f"📥 {sin_mapear:,} atenciones sin médico")
        
        # ========== LEER MÉDICOS DE ACCESS ==========
        acc_cur.execute("SELECT DISTINCT CODVEN, VENDEDOR FROM EQCTAVDD WHERE CODVEN IS NOT NULL AND VENDEDOR IS NOT NULL")
        medicos_access = {str(cod).strip(): str(nom).strip() for cod, nom in acc_cur.fetchall()}
        
        # ========== OBTENER MÉDICOS DE BD ==========
        pg_cur.execute("SELECT id, nombre FROM medico")
        medicos_bd = {str(nom).strip().upper(): mid for mid, nom in pg_cur.fetchall()}
        
        # ========== CREAR MAPEO ==========
        mapeos = []
        
        for codven, vendedor_access in medicos_access.items():
            vendedor_upper = vendedor_access.upper()
            
            # Búsqueda exacta
            if vendedor_upper in medicos_bd:
                mapeos.append((codven, medicos_bd[vendedor_upper]))
            else:
                # Búsqueda parcial (primeras 2 palabras)
                palabras = vendedor_upper.split()[:2]
                if len(palabras) >= 2:
                    for nombre_bd, mid in medicos_bd.items():
                        if all(palabra in nombre_bd for palabra in palabras):
                            mapeos.append((codven, mid))
                            break
        
        if not mapeos:
            log("⚠️ Sin mapeos disponibles")
            ac.close()
            pc.close()
            try:
                os.remove(temp_path)
            except:
                pass
            return False
        
        # ========== ACTUALIZAR POR CODVEN ==========
        log(f"🔗 Vinculando {len(mapeos)} médicos...", end=" ")
        
        # Actualizar atenciones que tengan CodVen en Access
        for codven, medico_id in mapeos:
            pg_cur.execute("""
                UPDATE atencion a
                SET medico_id = %s
                FROM (
                    SELECT DISTINCT T.IdTs 
                    FROM EqTraSec T
                    WHERE T.CodVen = %s
                ) et
                WHERE a.idts_access = et.IdTs::text
                AND a.medico_id IS NULL
            """, (medico_id, codven))
        
        pc.commit()
        updated = pg_cur.rowcount
        log(f"✓ {updated:,}")
        
        ac.close()
        pc.close()
        try:
            os.remove(temp_path)
        except:
            pass
        
        return updated > 0
        
    except Exception as e:
        log(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN - Modo interactivo o servicio
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("⚙️ SERVICIO AUTOMÁTICO DE MAPEO DE MÉDICOS")
    print("="*80 + "\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # Modo daemon (se ejecuta cada X segundos)
        intervalo = int(sys.argv[2]) if len(sys.argv) > 2 else 300  # 5 minutos por defecto
        
        log(f"🔄 Servicio iniciado (intervalo: {intervalo}s)\n")
        
        while True:
            try:
                log("🔍 Verificando atenciones sin médico...", end=" ")
                resultado = mapear_medicos()
                
                if resultado:
                    log("✅ Actualización completada\n")
                else:
                    log("OK (sin cambios)\n")
                
                time.sleep(intervalo)
                
            except KeyboardInterrupt:
                log("\n\n🛑 Servicio detenido")
                break
            except Exception as e:
                log(f"\n❌ Error: {e}\n")
                time.sleep(60)
    else:
        # Modo ejecución única
        log("🔍 Ejecutando mapeo una sola vez...\n")
        resultado = mapear_medicos()
        
        print("\n" + "="*80)
        if resultado:
            print("✅ MAPEO COMPLETADO")
        else:
            print("ℹ️ NO HAY CAMBIOS")
        print("="*80 + "\n")