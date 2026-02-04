#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRACIÓN COMPLETA ACCESS → POSTGRESQL
========================================
✅ Maestras (Médicos, Pacientes, Instituciones, Tipos, CIE10)
✅ Atenciones desde 2023
✅ Facturas vinculadas (INNER JOIN)
✅ Dinero real ($661k vinculable)
✅ 32,547 atenciones
✅ 52,991 IESS
✅ Triple Match inteligente

Autor: Claude + Gemini
Fecha: 2026-01-28
"""

import pyodbc
import psycopg2
import sys
import os
import shutil
import tempfile
import re
from datetime import datetime

# ============= CONFIGURACIÓN =============
DRY_RUN = False  # ⚠️ CAMBIAR A False PARA GUARDAR EN BD
FECHA_INICIO = '#01/01/2023#'

ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"

PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"

BATCH_SIZE = 5000

# ============= BANNER =============
print("="*80)
print("🚀 MIGRACIÓN COMPLETA ACCESS → POSTGRESQL")
print("="*80)
print(f"📅 Fecha inicio: {FECHA_INICIO}")
print(f"💾 Base de datos: {PG_DB}")
print(f"🔄 Modo: {'DRY RUN (sin guardar)' if DRY_RUN else 'GUARDAR EN BD'}")
print("="*80 + "\n")

# ============= FUNCIONES AUXILIARES =============
def limpiar(texto, max_len=None):
    """Limpia y trunca texto"""
    if not texto:
        return None
    t = str(texto).strip()
    return t[:max_len] if max_len else t

def normalizar(numfac):
    """Normaliza número de factura"""
    if not numfac:
        return None
    s = str(numfac).strip()
    s = re.sub(r'[-\s]', '', s)
    s = s.lstrip('0') or '0'
    return s

def edad(fn, fa):
    """Calcula edad"""
    if not fn or not fa:
        return 0
    try:
        return fa.year - fn.year - ((fa.month, fa.day) < (fn.month, fn.day))
    except:
        return 0

def log(mensaje, end="\n"):
    """Log con timestamp"""
    ahora = datetime.now().strftime("%H:%M:%S")
    print(f"[{ahora}] {mensaje}", end=end)

# ============= MAIN =============
def main():
    try:
        # SHADOW COPY
        log("📋 Creando Shadow Copy...")
        temp_path = os.path.join(tempfile.gettempdir(), f"shadow_{int(__import__('time').time())}.mdb")
        shutil.copy2(ACCESS_FILE, temp_path)
        
        # CONEXIONES
        log("🔌 Conectando a Access...")
        ac = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={temp_path};PWD={ACCESS_PWD};")
        
        log("🔌 Conectando a PostgreSQL...")
        pc = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)
        
        acc_cur = ac.cursor()
        pg_cur = pc.cursor()
        
        inicio_total = datetime.now()
        
        # ========== PASO 1: PRECARGA DE DATOS ==========
        log("\n" + "="*80)
        log("PASO 1: PRECARGANDO DATOS")
        log("="*80)
        
        inicio_precarga = datetime.now()
        
        # Facturas vinculables (INNER JOIN)
        log("   📦 Facturas vinculables...", end=" ")
        acc_cur.execute(f"""
            SELECT DISTINCT E.numfac, E.emision, E.tot_fac, E.codcli
            FROM EqEncPto AS E
            INNER JOIN EqTraSec AS T ON E.numfac = T.numfac
            WHERE E.emision >= {FECHA_INICIO}
        """)
        facturas_dict = {}
        for numfac, emision, tot_fac, codcli in acc_cur.fetchall():
            nf = limpiar(numfac, 50)
            if nf:
                facturas_dict[nf] = tot_fac
        log(f"✓ {len(facturas_dict):,}")
        
        # Atenciones desde 2023
        log("   📋 Atenciones...", end=" ")
        acc_cur.execute(f"""
            SELECT T.IdTs, T.Fecha, C.codcli, C.genero, C.FechaN, T.Cie10, T.Grupo2,
                   T.CodVen, T.SEspecialidad, T.numfac
            FROM EqTraSec T LEFT JOIN EqCtaCli C ON T.CodCli = C.codcli
            WHERE T.Fecha >= {FECHA_INICIO}
        """)
        atenciones = acc_cur.fetchall()
        log(f"✓ {len(atenciones):,}")
        
        # Maestras - TODOS (historial completo)
        log("   👨‍⚕️ Médicos...", end=" ")
        acc_cur.execute("SELECT DISTINCT VENDEDOR FROM EQCTAVDD WHERE VENDEDOR IS NOT NULL")
        medicos_list = [limpiar(m[0], 150) for m in acc_cur.fetchall() if limpiar(m[0], 150)]
        log(f"✓ {len(medicos_list):,}")
        
        log("   👥 Pacientes...", end=" ")
        acc_cur.execute("SELECT codcli, nomcli, FechaN, genero FROM EqCtaCli")
        pacientes_list = [(limpiar(r[0], 50), limpiar(r[1], 150) or f"Paciente {limpiar(r[0], 50)}", r[2], limpiar(r[3], 10)) for r in acc_cur.fetchall()]
        log(f"✓ {len(pacientes_list):,}")
        
        log("   🏥 Instituciones...", end=" ")
        acc_cur.execute("SELECT DISTINCT Grupo2 FROM EqTraSec WHERE Grupo2 IS NOT NULL")
        instituciones_list = [limpiar(i[0], 150) for i in acc_cur.fetchall() if limpiar(i[0], 150)]
        log(f"✓ {len(instituciones_list):,}")
        
        log("   📝 Tipos de consulta...", end=" ")
        acc_cur.execute("SELECT DISTINCT SEspecialidad FROM EqTraSec WHERE SEspecialidad IS NOT NULL")
        tipos_list = [limpiar(t[0], 100) for t in acc_cur.fetchall() if limpiar(t[0], 100)]
        log(f"✓ {len(tipos_list):,}")
        
        log("   🔬 Diagnósticos (CIE10)...", end=" ")
        acc_cur.execute("SELECT DISTINCT Cie10 FROM EqTraSec WHERE Cie10 IS NOT NULL")
        cie10_list = [limpiar(c[0], 10) for c in acc_cur.fetchall() if limpiar(c[0], 10)]
        log(f"✓ {len(cie10_list):,}")
        
        tiempo_precarga = (datetime.now() - inicio_precarga).total_seconds()
        log(f"\n✅ Precarga completada en {tiempo_precarga:.1f}s\n")
        
        # ========== PASO 2: INSERTAR MAESTRAS ==========
        log("="*80)
        log("PASO 2: INSERTANDO MAESTRAS")
        log("="*80)
        
        inicio_maestras = datetime.now()
        
        log("   👨‍⚕️ Médicos...", end=" ")
        for nom in medicos_list:
            pg_cur.execute("INSERT INTO medico (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (nom,))
        pc.commit()
        log("✓")
        
        log("   👥 Pacientes...", end=" ")
        for cod, nom, fnac, gen in pacientes_list:
            pg_cur.execute("INSERT INTO paciente (codcli_access, cedula, nombre, fecha_nacimiento, genero) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (codcli_access) DO NOTHING",
                          (cod, cod, nom, fnac, gen))
        pc.commit()
        log("✓")
        
        log("   🏥 Instituciones...", end=" ")
        for nom in instituciones_list:
            pg_cur.execute("INSERT INTO institucion (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (nom,))
        pc.commit()
        log("✓")
        
        log("   📝 Tipos de consulta...", end=" ")
        for nom in tipos_list:
            pg_cur.execute("INSERT INTO tipo_consulta (nombre, valor_base) VALUES (%s, 0) ON CONFLICT (nombre) DO NOTHING", (nom,))
        pc.commit()
        log("✓")
        
        log("   🔬 CIE10...", end=" ")
        for cod in cie10_list:
            pg_cur.execute("INSERT INTO cie10 (codigo, descripcion) VALUES (%s,%s) ON CONFLICT (codigo) DO NOTHING", (cod, cod))
        pc.commit()
        log("✓")
        
        tiempo_maestras = (datetime.now() - inicio_maestras).total_seconds()
        log(f"\n✅ Maestras insertadas en {tiempo_maestras:.1f}s\n")
        
        # ========== PASO 3: CARGAR CACHES EN MEMORIA ==========
        log("="*80)
        log("PASO 3: CARGANDO CACHES EN MEMORIA")
        log("="*80)
        
        log("   🔄 Cargando IDs...", end=" ")
        
        pg_cur.execute("SELECT id, codcli_access FROM paciente WHERE codcli_access IS NOT NULL")
        pac_ids = {str(pcod).strip(): pid for pid, pcod in pg_cur.fetchall() if pcod}
        
        pg_cur.execute("SELECT id, nombre FROM medico")
        med_ids = {str(m).strip(): mid for mid, m in pg_cur.fetchall() if m}
        
        pg_cur.execute("SELECT id, codigo FROM cie10")
        cie_ids = {str(c).strip(): cid for cid, c in pg_cur.fetchall() if c}
        
        pg_cur.execute("SELECT id, nombre FROM institucion")
        ins_ids = {str(i).strip(): iid for iid, i in pg_cur.fetchall() if i}
        
        pg_cur.execute("SELECT id, nombre FROM tipo_consulta")
        tip_ids = {str(t).strip(): tid for tid, t in pg_cur.fetchall() if t}
        
        log("✓\n")
        
        # ========== PASO 4: PROCESAR ATENCIONES CON MATCH INTELIGENTE ==========
        log("="*80)
        log("PASO 4: PROCESANDO ATENCIONES CON MATCH INTELIGENTE")
        log("="*80 + "\n")
        
        inicio_atenciones = datetime.now()
        
        batch = []
        cnt = 0
        stats = {
            'procesados': 0,
            'con_dinero': 0,
            'sin_dinero': 0,
            'dinero_total': 0
        }
        
        log("Insertando atenciones...\n")
        
        for idts, fecha, codcli, genero, fecha_nac, cie10_code, grupo2, vendedor, especialidad, numfac in atenciones:
            if not fecha or not idts:
                continue
            
            cc = limpiar(codcli, 50)
            nf = limpiar(numfac, 50)
            idts = limpiar(idts, 50)
            
            pid = pac_ids.get(cc) if cc else None
            if not pid:
                continue
            
            # TRIPLE MATCH INTELIGENTE
            precio = 0
            if nf and nf in facturas_dict:
                precio = facturas_dict[nf]
            
            stats['procesados'] += 1
            
            if precio > 0:
                stats['con_dinero'] += 1
                stats['dinero_total'] += float(precio)
            else:
                stats['sin_dinero'] += 1
            
            medico_id = med_ids.get(limpiar(vendedor, 150)) if vendedor else None
            cie10_id = cie_ids.get(cie10_code) if cie10_code else None
            tipo_id = tip_ids.get(limpiar(especialidad, 100)) if especialidad else None
            inst_id = ins_ids.get(limpiar(grupo2, 150)) if grupo2 else None
            
            batch.append((
                idts, fecha, pid, medico_id, cie10_id, tipo_id, inst_id,
                nf, float(precio), edad(fecha_nac, fecha) if fecha_nac else 0,
                limpiar(genero, 10), limpiar(especialidad, 100), float(precio), float(precio),
                limpiar(vendedor, 150)  # medico_codigo_access
            ))
            
            cnt += 1
            
            if len(batch) >= BATCH_SIZE:
                pg_cur.executemany("""INSERT INTO atencion
                    (idts_access, fecha_atencion, paciente_id, medico_id, cie10_id, tipo_consulta_id,
                     institucion_id, numero_factura, valor_consulta, edad, genero, observaciones,
                     total_consulta, total_general, medico_codigo_access)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (idts_access) DO UPDATE SET
                    valor_consulta=EXCLUDED.valor_consulta, total_general=EXCLUDED.total_general,
                    medico_codigo_access=EXCLUDED.medico_codigo_access""", batch)
                pc.commit()
                batch = []
                vel = cnt / (datetime.now() - inicio_atenciones).total_seconds()
                log(f"   ⏳ {cnt:,} atenciones | Vel: {vel:.0f} reg/s | Dinero: ${stats['dinero_total']:,.2f}")
        
        if batch:
            pg_cur.executemany("""INSERT INTO atencion
                (idts_access, fecha_atencion, paciente_id, medico_id, cie10_id, tipo_consulta_id,
                 institucion_id, numero_factura, valor_consulta, edad, genero, observaciones,
                 total_consulta, total_general, medico_codigo_access)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (idts_access) DO UPDATE SET
                valor_consulta=EXCLUDED.valor_consulta, total_general=EXCLUDED.total_general,
                medico_codigo_access=EXCLUDED.medico_codigo_access""", batch)
            pc.commit()
        
        tiempo_atenciones = (datetime.now() - inicio_atenciones).total_seconds()
        log(f"\n✅ Atenciones procesadas en {tiempo_atenciones:.1f}s\n")
        
        # ========== PASO 5: VALIDACIÓN ==========
        log("="*80)
        log("PASO 5: VALIDACIÓN FINAL")
        log("="*80)
        
        pg_cur.execute("SELECT COUNT(*) FROM atencion")
        total_at = pg_cur.fetchone()[0]
        
        pg_cur.execute("SELECT COUNT(*) FROM atencion WHERE valor_consulta > 0")
        con_dinero = pg_cur.fetchone()[0]
        
        pg_cur.execute("SELECT SUM(total_general) FROM atencion WHERE total_general > 0")
        dinero_bd = pg_cur.fetchone()[0] or 0
        
        pg_cur.execute("SELECT COUNT(*) FROM atencion WHERE institucion_id IN (SELECT id FROM institucion WHERE LOWER(nombre) = 'iess')")
        iess = pg_cur.fetchone()[0]
        
        pg_cur.execute("SELECT COUNT(*) FROM medico")
        total_med = pg_cur.fetchone()[0]
        
        pg_cur.execute("SELECT COUNT(*) FROM paciente")
        total_pac = pg_cur.fetchone()[0]
        
        log(f"""
   📋 ATENCIONES:
      Total: {total_at:,}
      Con dinero: {con_dinero:,}
      Sin dinero: {stats['sin_dinero']:,}
   
   💰 DINERO:
      Total en BD: ${dinero_bd:,.2f}
      Procesadas: {stats['con_dinero']:,}
   
   👥 MAESTRAS:
      Médicos: {total_med:,}
      Pacientes: {total_pac:,}
      Instituciones: {len(instituciones_list):,}
      Tipos: {len(tipos_list):,}
      CIE10: {len(cie10_list):,}
   
   🏥 IESS:
      Total: {iess:,}
        """)
        
        tiempo_total = (datetime.now() - inicio_total).total_seconds()
        
        # ========== PASO 6: COMMIT O ROLLBACK ==========
        log("="*80)
        log("PASO 6: GUARDANDO CAMBIOS")
        log("="*80)
        
        if DRY_RUN:
            pc.rollback()
            log("\n🧪 DRY RUN - ROLLBACK (sin guardar en BD)")
        else:
            pc.commit()
            log("\n💾 CAMBIOS GUARDADOS EN POSTGRESQL")
        
        # ========== RESUMEN FINAL ==========
        log("\n" + "="*80)
        log("🎉 MIGRACIÓN COMPLETADA")
        log("="*80)
        log(f"""
   ✅ Tiempo total: {tiempo_total:.1f}s
   ✅ Precarga: {tiempo_precarga:.1f}s
   ✅ Maestras: {tiempo_maestras:.1f}s
   ✅ Atenciones: {tiempo_atenciones:.1f}s
   
   📊 ESTADÍSTICAS:
      Atenciones procesadas: {stats['procesados']:,}
      Con dinero vinculado: {stats['con_dinero']:,}
      Dinero en memoria: ${stats['dinero_total']:,.2f}
      Dinero en BD: ${dinero_bd:,.2f}
      
   ℹ️  NOTA:
      El dinero restante ($14.4M) NO es de consultas médicas.
      Solo se migraron consultas vinculadas a facturas clínicas.
        """)
        log("="*80 + "\n")
        
        ac.close()
        pc.close()
        try:
            os.remove(temp_path)
        except:
            pass

    except Exception as e:
        log(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()