#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRACIÓN COMPLETA - RESPETA TODO EL CÓDIGO ORIGINAL
"""

import pyodbc
import psycopg2
import os
import shutil
import tempfile
from datetime import datetime
import time
import sys

ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"
PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"
DRY_RUN = False
INTERVALO_MINUTOS = 5

def log(msg, end="\n", level="INFO"):
    ahora = datetime.now().strftime("%H:%M:%S")
    if level == "STEP":
        print(f"\n{'='*80}")
        print(f"[{ahora}] 🚀 {msg}")
        print(f"{'='*80}")
    elif level == "SUCCESS":
        print(f"[{ahora}] ✅ {msg}", end=end, flush=True)
    elif level == "INFO":
        print(f"[{ahora}] ℹ️  {msg}", end=end, flush=True)
    elif level == "ERROR":
        print(f"[{ahora}] ❌ {msg}", end=end, flush=True)
    else:
        print(f"[{ahora}] {msg}", end=end, flush=True)

def limpiar(texto, max_len=None):
    if not texto:
        return None
    t = str(texto).strip()
    return t[:max_len] if max_len else t

def edad(fn, fa):
    if not fn or not fa:
        return 0
    try:
        return fa.year - fn.year - ((fa.month, fa.day) < (fn.month, fn.day))
    except:
        return 0

def conectar_postgres(reintentos=3, espera=10):
    for intento in range(1, reintentos+1):
        try:
            pc = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)
            return pc, pc.cursor()
        except Exception as e:
            print(f"[ERROR] Fallo conexión Postgres (intento {intento}/{reintentos}): {e}")
            if intento == reintentos:
                raise
            time.sleep(espera)

def conectar_access(reintentos=3, espera=10, temp_path=None):
    for intento in range(1, reintentos+1):
        try:
            ac = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={temp_path};PWD={ACCESS_PWD};")
            return ac, ac.cursor()
        except Exception as e:
            print(f"[ERROR] Fallo conexión Access (intento {intento}/{reintentos}): {e}")
            if intento == reintentos:
                raise
            time.sleep(espera)

def resumen_ciclo(total_at, total_pac, total_med, din, con_medico, t_inicio, errores):
    tiempo_total = (datetime.now() - t_inicio).total_seconds()
    print("\n" + "="*80)
    print("📊 RESUMEN DEL CICLO")
    print("="*80)
    print(f"⏱️  Tiempo: {tiempo_total:.1f}s")
    print(f"📊 Atenciones: {total_at:,}")
    print(f"👥 Pacientes: {total_pac:,}")
    print(f"👨‍⚕️  Médicos: {total_med:,}")
    print(f"💰 Dinero: ${din:,.2f}")
    print(f"🔗 Con Médico: {con_medico:,}")
    if errores > 0:
        print(f"❌ Errores: {errores}")
    print("="*80 + "\n")

def migrar():
    t_inicio = datetime.now()
    errores = 0
    try:
        log("Conectando a bases de datos...", "STEP")
        
        log("📋 Shadow copy de Access...", end=" ")
        temp_path = os.path.join(tempfile.gettempdir(), f"shadow_{int(time.time())}.mdb")
        shutil.copy2(ACCESS_FILE, temp_path)
        log("✓", "SUCCESS")
        
        log("🔌 PostgreSQL...", end=" ")
        pc, pg_cur = conectar_postgres()
        log("✓", "SUCCESS")
        
        log("📂 Access...", end=" ")
        ac, acc_cur = conectar_access(temp_path=temp_path)
        log("✓", "SUCCESS")
        
        log("Creando estructura profesional...", "STEP")
        
        log("📍 institucion...", end=" ")
        try:
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS institucion (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL UNIQUE,
                    codigo VARCHAR(50),
                    activo BOOLEAN DEFAULT true,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_institucion_nombre ON institucion(nombre);
            """)
            pc.commit()
            log("✓", "SUCCESS")
        except:
            log("ya existe", "INFO")
        
        log("👨‍⚕️  medico...", end=" ")
        try:
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS medico (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL UNIQUE,
                    especialidad VARCHAR(100),
                    cedula VARCHAR(20),
                    activo BOOLEAN DEFAULT true,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_medico_nombre ON medico(nombre);
            """)
            pc.commit()
            log("✓", "SUCCESS")
        except:
            log("ya existe", "INFO")
        
        log("👥 paciente...", end=" ")
        try:
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS paciente (
                    id SERIAL PRIMARY KEY,
                    cedula VARCHAR(20) NOT NULL UNIQUE,
                    nombre VARCHAR(150) NOT NULL,
                    fecha_nacimiento DATE,
                    genero VARCHAR(10),
                    activo BOOLEAN DEFAULT true,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_paciente_cedula ON paciente(cedula);
                CREATE INDEX IF NOT EXISTS idx_paciente_nombre ON paciente(nombre);
            """)
            pc.commit()
            log("✓", "SUCCESS")
        except:
            log("ya existe", "INFO")
        
        log("📋 tipo_consulta...", end=" ")
        try:
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS tipo_consulta (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    valor_base NUMERIC(10,2) DEFAULT 0,
                    activo BOOLEAN DEFAULT true
                );
                CREATE INDEX IF NOT EXISTS idx_tipo_consulta_nombre ON tipo_consulta(nombre);
            """)
            pc.commit()
            log("✓", "SUCCESS")
        except:
            log("ya existe", "INFO")
        
        log("🔬 cie10...", end=" ")
        try:
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS cie10 (
                    id SERIAL PRIMARY KEY,
                    codigo VARCHAR(10) NOT NULL UNIQUE,
                    descripcion VARCHAR(255),
                    activo BOOLEAN DEFAULT true
                );
                CREATE INDEX IF NOT EXISTS idx_cie10_codigo ON cie10(codigo);
            """)
            pc.commit()
            log("✓", "SUCCESS")
        except:
            log("ya existe", "INFO")
        
        log("🏥 atencion...", end=" ")
        try:
            pg_cur.execute("""
                CREATE TABLE IF NOT EXISTS atencion (
                    id SERIAL PRIMARY KEY,
                    idts_access VARCHAR(50) NOT NULL UNIQUE,
                    fecha_atencion DATE NOT NULL,
                    paciente_id INTEGER REFERENCES paciente(id) ON DELETE SET NULL,
                    medico_id INTEGER REFERENCES medico(id) ON DELETE SET NULL,
                    cie10_id INTEGER REFERENCES cie10(id) ON DELETE SET NULL,
                    tipo_consulta_id INTEGER REFERENCES tipo_consulta(id) ON DELETE SET NULL,
                    institucion_id INTEGER REFERENCES institucion(id) ON DELETE SET NULL,
                    numero_factura VARCHAR(50),
                    valor_consulta NUMERIC(10,2) DEFAULT 0,
                    edad INTEGER,
                    genero VARCHAR(10),
                    observaciones VARCHAR(500),
                    total_consulta NUMERIC(10,2) DEFAULT 0,
                    total_general NUMERIC(10,2) DEFAULT 0,
                    activo BOOLEAN DEFAULT true,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_atencion_fecha ON atencion(fecha_atencion);
                CREATE INDEX IF NOT EXISTS idx_atencion_paciente ON atencion(paciente_id);
                CREATE INDEX IF NOT EXISTS idx_atencion_medico ON atencion(medico_id);
                CREATE INDEX IF NOT EXISTS idx_atencion_institucion ON atencion(institucion_id);
            """)
            pc.commit()
            log("✓", "SUCCESS")
        except:
            log("ya existe", "INFO")
        
        log("Precargando datos desde Access...", "STEP")
        
        log("📥 Médicos...", end=" ")
        acc_cur.execute("SELECT DISTINCT VENDEDOR FROM EQCTAVDD WHERE VENDEDOR IS NOT NULL")
        medicos = [limpiar(m[0], 150) for m in acc_cur.fetchall() if limpiar(m[0], 150)]
        log(f"✓ {len(medicos)}", "SUCCESS")
        
        log("📥 Pacientes...", end=" ")
        acc_cur.execute("SELECT codcli, nomcli, FechaN, genero FROM EqCtaCli")
        pacientes = [(limpiar(r[0], 20), limpiar(r[1], 150) or f"Pac_{limpiar(r[0], 20)}", r[2], limpiar(r[3], 10)) 
                     for r in acc_cur.fetchall()]
        log(f"✓ {len(pacientes)}", "SUCCESS")
        
        log("📥 Instituciones...", end=" ")
        acc_cur.execute("SELECT DISTINCT Grupo2 FROM EqTraSec WHERE Grupo2 IS NOT NULL")
        instituciones = [limpiar(i[0], 150) for i in acc_cur.fetchall() if limpiar(i[0], 150)]
        log(f"✓ {len(instituciones)}", "SUCCESS")
        
        log("📥 Tipos...", end=" ")
        acc_cur.execute("SELECT DISTINCT SEspecialidad FROM EqTraSec WHERE SEspecialidad IS NOT NULL")
        tipos = [limpiar(t[0], 100) for t in acc_cur.fetchall() if limpiar(t[0], 100)]
        log(f"✓ {len(tipos)}", "SUCCESS")
        
        log("📥 CIE10...", end=" ")
        acc_cur.execute("SELECT DISTINCT Cie10 FROM EqTraSec WHERE Cie10 IS NOT NULL")
        cie10 = [limpiar(c[0], 10) for c in acc_cur.fetchall() if limpiar(c[0], 10)]
        log(f"✓ {len(cie10)}", "SUCCESS")
        
        log("📥 CODVEN → Nombres...", end=" ")
        acc_cur.execute("SELECT DISTINCT CODVEN, VENDEDOR FROM EQCTAVDD WHERE CODVEN IS NOT NULL AND VENDEDOR IS NOT NULL")
        codven_nombres = {str(c).strip(): str(v).strip() for c, v in acc_cur.fetchall()}
        log(f"✓ {len(codven_nombres)}", "SUCCESS")
        
        log("📥 Facturas...", end=" ")
        acc_cur.execute("SELECT numfac, tot_fac FROM EqEncPto WHERE tot_fac > 0")
        facturas = {str(fac).strip(): float(dinero) for fac, dinero in acc_cur.fetchall()}
        log(f"✓ {len(facturas):,}", "SUCCESS")
        
        log("📥 EqTraSec mapping...", end=" ")
        acc_cur.execute("SELECT IdTs, CodVen FROM EqTraSec WHERE CodVen IS NOT NULL ORDER BY IdTs DESC")
        idts_codven = [(str(it).strip(), str(cv).strip()) for it, cv in acc_cur.fetchall()]
        log(f"✓ {len(idts_codven):,}", "SUCCESS")
        
        if DRY_RUN:
            print(f"\n[DRY RUN] Médicos: {len(medicos)}, Pacientes: {len(pacientes)}, Instituciones: {len(instituciones)}, Tipos: {len(tipos)}, CIE10: {len(cie10)}")
            print(f"[DRY RUN] Se migrarían {len(atenciones):,} atenciones y {len(facturas):,} facturas.")
            ac.close()
            pc.close()
            try:
                os.remove(temp_path)
            except:
                pass
            resumen_ciclo(len(atenciones), len(pacientes), len(medicos), 0, 0, t_inicio, errores)
            return
        
        log("Insertando maestras...", "STEP")
        
        log("💾 Médicos...", end=" ")
        for med in medicos:
            pg_cur.execute("INSERT INTO medico (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (med,))
        pc.commit()
        log("✓", "SUCCESS")
        
        log("💾 Pacientes...", end=" ")
        for cod, nom, fnac, gen in pacientes:
            pg_cur.execute("INSERT INTO paciente (cedula, nombre, fecha_nacimiento, genero) VALUES (%s,%s,%s,%s) ON CONFLICT (cedula) DO NOTHING", (cod, nom, fnac, gen))
        pc.commit()
        log("✓", "SUCCESS")
        
        log("💾 Instituciones...", end=" ")
        for inst in instituciones:
            pg_cur.execute("INSERT INTO institucion (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (inst,))
        pc.commit()
        log("✓", "SUCCESS")
        
        log("💾 Tipos...", end=" ")
        for tipo in tipos:
            pg_cur.execute("INSERT INTO tipo_consulta (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (tipo,))
        pc.commit()
        log("✓", "SUCCESS")
        
        log("💾 CIE10...", end=" ")
        for cod in cie10:
            pg_cur.execute("INSERT INTO cie10 (codigo) VALUES (%s) ON CONFLICT (codigo) DO NOTHING", (cod,))
        pc.commit()
        log("✓", "SUCCESS")
        
        log("Cargando IDs en memoria...", "STEP")
        
        log("📦 Pacientes...", end=" ")
        pg_cur.execute("SELECT id, cedula FROM paciente WHERE cedula IS NOT NULL")
        pac_ids = {str(c).strip(): p for p, c in pg_cur.fetchall()}
        log(f"✓ {len(pac_ids)}", "SUCCESS")
        
        log("📦 Médicos...", end=" ")
        pg_cur.execute("SELECT id, nombre FROM medico")
        med_ids = {str(m).strip().upper(): mid for mid, m in pg_cur.fetchall()}
        log(f"✓ {len(med_ids)}", "SUCCESS")
        
        log("📦 CIE10...", end=" ")
        pg_cur.execute("SELECT id, codigo FROM cie10")
        cie_ids = {str(c).strip(): cid for cid, c in pg_cur.fetchall()}
        log(f"✓ {len(cie_ids)}", "SUCCESS")
        
        log("📦 Instituciones...", end=" ")
        pg_cur.execute("SELECT id, nombre FROM institucion")
        inst_ids = {str(i).strip(): iid for iid, i in pg_cur.fetchall()}
        log(f"✓ {len(inst_ids)}", "SUCCESS")
        
        log("📦 Tipos...", end=" ")
        pg_cur.execute("SELECT id, nombre FROM tipo_consulta")
        tip_ids = {str(t).strip(): tid for tid, t in pg_cur.fetchall()}
        log(f"✓ {len(tip_ids)}", "SUCCESS")
        
        log("Insertando 95,675 atenciones...", "STEP")
        
        acc_cur.execute("""
            SELECT T.IdTs, T.Fecha, C.codcli, C.genero, C.FechaN, T.Cie10, T.Grupo2, T.CodVen, T.SEspecialidad, T.numfac
            FROM EqTraSec T LEFT JOIN EqCtaCli C ON T.CodCli = C.codcli
            ORDER BY T.Fecha DESC
        """)
        
        atenciones = acc_cur.fetchall()
        log(f"📥 Total: {len(atenciones):,} atenciones\n")
        
        batch = []
        cnt = 0
        inicio = datetime.now()
        
        for idts, fecha, codcli, genero, fecha_nac, cie10_code, grupo2, vendedor, especialidad, numfac in atenciones:
            if not fecha or not idts:
                continue
            
            cc = limpiar(codcli, 20)
            pid = pac_ids.get(cc) if cc else None
            if not pid:
                continue
            
            medico_id = med_ids.get(limpiar(vendedor, 150).upper()) if vendedor else None
            cie10_id = cie_ids.get(cie10_code) if cie10_code else None
            tipo_id = tip_ids.get(limpiar(especialidad, 100)) if especialidad else None
            inst_id = inst_ids.get(limpiar(grupo2, 150)) if grupo2 else None
            
            batch.append((
                limpiar(idts, 50), fecha, pid, medico_id, cie10_id, tipo_id, inst_id,
                limpiar(numfac, 50), 0, edad(fecha_nac, fecha) if fecha_nac else 0,
                limpiar(genero, 10), limpiar(especialidad, 100), 0, 0
            ))
            
            cnt += 1
            
            if len(batch) >= 5000:
                pg_cur.executemany("""
                    INSERT INTO atencion
                    (idts_access, fecha_atencion, paciente_id, medico_id, cie10_id, tipo_consulta_id,
                     institucion_id, numero_factura, valor_consulta, edad, genero, observaciones,
                     total_consulta, total_general)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (idts_access) DO NOTHING
                """, batch)
                pc.commit()
                batch = []
                vel = cnt / (datetime.now() - inicio).total_seconds()
                print(f"\r   ⏳ {cnt:,} registros | {vel:.0f} reg/s", end="", flush=True)
        
        if batch:
            pg_cur.executemany("""
                INSERT INTO atencion
                (idts_access, fecha_atencion, paciente_id, medico_id, cie10_id, tipo_consulta_id,
                 institucion_id, numero_factura, valor_consulta, edad, genero, observaciones,
                 total_consulta, total_general)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (idts_access) DO NOTHING
            """, batch)
            pc.commit()
        
        tiempo = (datetime.now() - inicio).total_seconds()
        print(f"\n   ✓ {cnt:,} en {tiempo:.1f}s\n")
        
        log("Vinculando dinero desde facturas...", "STEP")
        
        log("💳 Creando datos temporales...", end=" ")
        sql_values = ", ".join([f"('{numfac}',{dinero})" for numfac, dinero in facturas.items()])
        pg_cur.execute(f"""
            CREATE TEMP TABLE temp_facturas (numfac VARCHAR(50), dinero NUMERIC(10,2));
            INSERT INTO temp_facturas VALUES {sql_values};
        """)
        pc.commit()
        log("✓", "SUCCESS")
        
        log("💳 Actualizando atenciones...", end=" ")
        pg_cur.execute("""
            UPDATE atencion a
            SET valor_consulta = tf.dinero, 
                total_consulta = tf.dinero, 
                total_general = tf.dinero
            FROM temp_facturas tf
            WHERE a.numero_factura = tf.numfac 
            AND a.valor_consulta = 0
        """)
        pc.commit()
        updated = pg_cur.rowcount
        log(f"✓ {updated:,} actualizadas", "SUCCESS")
        
        log("Mapeando médicos automáticamente...", "STEP")
        
        log("🔍 Analizando relaciones...", end=" ")
        mapeos = {}
        
        for idts, codven in idts_codven:
            if codven in codven_nombres:
                nombre_medico = codven_nombres[codven].upper()
                
                if nombre_medico in med_ids:
                    mapeos[idts] = med_ids[nombre_medico]
                else:
                    palabras = nombre_medico.split()[:2]
                    if palabras:
                        for nombre_bd, mid in med_ids.items():
                            if all(p in nombre_bd for p in palabras):
                                mapeos[idts] = mid
                                break
        
        log(f"✓ {len(mapeos):,} mapeos", "SUCCESS")
        
        log("💾 Actualizando médicos...", end=" ")
        sql_values = ", ".join([f"('{idts}', {mid})" for idts, mid in mapeos.items()])
        
        pg_cur.execute(f"""
            WITH mapeo AS (
                SELECT * FROM (VALUES {sql_values}) AS t(idts, medico_id)
            )
            UPDATE atencion a
            SET medico_id = m.medico_id
            FROM mapeo m
            WHERE a.idts_access = m.idts
            AND a.medico_id IS NULL
        """)
        pc.commit()
        updated = pg_cur.rowcount
        log(f"✓ {updated:,} actualizadas", "SUCCESS")
        
        log("Validando datos...", "STEP")
        
        pg_cur.execute("SELECT COUNT(*) FROM atencion")
        total_at = pg_cur.fetchone()[0]
        log(f"✓ Atenciones: {total_at:,}", "SUCCESS")
        
        pg_cur.execute("SELECT COUNT(*) FROM paciente")
        total_pac = pg_cur.fetchone()[0]
        log(f"✓ Pacientes: {total_pac:,}", "SUCCESS")
        
        pg_cur.execute("SELECT COUNT(*) FROM medico")
        total_med = pg_cur.fetchone()[0]
        log(f"✓ Médicos: {total_med:,}", "SUCCESS")
        
        pg_cur.execute("SELECT SUM(total_general) FROM atencion WHERE total_general > 0")
        din = pg_cur.fetchone()[0] or 0
        log(f"✓ Dinero: ${din:,.2f}", "SUCCESS")
        
        pg_cur.execute("SELECT COUNT(*) FROM atencion WHERE medico_id IS NOT NULL")
        con_medico = pg_cur.fetchone()[0]
        log(f"✓ Con Médico: {con_medico:,}", "SUCCESS")
        
        ac.close()
        pc.close()
        try:
            os.remove(temp_path)
        except:
            pass
        
        resumen_ciclo(total_at, total_pac, total_med, din, con_medico, t_inicio, errores)
        
    except Exception as e:
        errores = 1
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        resumen_ciclo(0, 0, 0, 0, 0, t_inicio, errores)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🏥 MIGRACIÓN COMPLETA - CLÍNICA HERMANAS HOSPITALARIAS")
    print("="*80)
    
    ciclo = 1
    while True:
        print(f"\n================ CICLO {ciclo} ==================")
        migrar()
        print(f"[INFO] Esperando {INTERVALO_MINUTOS} minutos para el próximo ciclo...")
        try:
            for i in range(INTERVALO_MINUTOS * 60, 0, -1):
                print(f"\rSiguiente ciclo en {i//60:02d}:{i%60:02d} min", end="", flush=True)
                time.sleep(1)
            print()
        except KeyboardInterrupt:
            print("\n[INFO] Migración detenida por el usuario.")
            break
        ciclo += 1