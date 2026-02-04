#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 2: MIGRACIÓN DESDE ACCESS
Carga datos desde Access (EqTraSec, EqCtaCli, EQCTAVDD, EqEncPto)
"""

import pyodbc
import psycopg2
from datetime import datetime
import os
import shutil
import tempfile


# === CONFIGURACIÓN ===
ACCESS_FILE = r"C:\Users\jossu\OneDrive\Escritorio\eqsys.mdb"
ACCESS_PWD = "NeoAvanEcu22"
PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "partes_diarios"
PG_USER = "postgres"
PG_PASS = "jossue205"
DRY_RUN = True
  # Cambia a True para solo simular la migración
INTERVALO_MINUTOS = 5

def log(msg, end="\n"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", end=end)

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


import time as _time

def migrar():
    print("\n" + "="*80)
    print(f"🚀 PASO 2: MIGRACIÓN DESDE ACCESS | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    try:
        # Shadow copy
        log("📋 Shadow copy...", end=" ")
        temp_path = os.path.join(tempfile.gettempdir(), f"shadow_{int(__import__('time').time())}.mdb")
        shutil.copy2(ACCESS_FILE, temp_path)
        log("✓\n")

        # Conectar
        log("🔌 Conectando...", end=" ")
        ac = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={temp_path};PWD={ACCESS_PWD};")
        pc = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS) 
        log("✓\n")

        acc_cur = ac.cursor()
        pg_cur = pc.cursor()

        # ========== PRECARGA ========== (igual que antes)
        log("📥 PRECARGANDO...\n")
        log("   Médicos...", end=" ")
        acc_cur.execute("SELECT DISTINCT VENDEDOR FROM EQCTAVDD WHERE VENDEDOR IS NOT NULL")
        medicos = [limpiar(m[0], 150) for m in acc_cur.fetchall() if limpiar(m[0], 150)]
        log(f"✓ {len(medicos)}")
        log("   Pacientes...", end=" ")
        acc_cur.execute("SELECT codcli, nomcli, FechaN, genero FROM EqCtaCli")
        pacientes = [(limpiar(r[0], 20), limpiar(r[1], 150) or f"Pac_{limpiar(r[0], 20)}", r[2], limpiar(r[3], 10)) 
                     for r in acc_cur.fetchall()]
        log(f"✓ {len(pacientes)}")
        log("   Instituciones...", end=" ")
        acc_cur.execute("SELECT DISTINCT Grupo2 FROM EqTraSec WHERE Grupo2 IS NOT NULL")
        instituciones = [limpiar(i[0], 150) for i in acc_cur.fetchall() if limpiar(i[0], 150)]
        log(f"✓ {len(instituciones)}")
        log("   Tipos...", end=" ")
        acc_cur.execute("SELECT DISTINCT SEspecialidad FROM EqTraSec WHERE SEspecialidad IS NOT NULL")
        tipos = [limpiar(t[0], 100) for t in acc_cur.fetchall() if limpiar(t[0], 100)]
        log(f"✓ {len(tipos)}")
        log("   CIE10...", end=" ")
        acc_cur.execute("SELECT DISTINCT Cie10 FROM EqTraSec WHERE Cie10 IS NOT NULL")
        cie10 = [limpiar(c[0], 10) for c in acc_cur.fetchall() if limpiar(c[0], 10)]
        log(f"✓ {len(cie10)}\n")

        if DRY_RUN:
            print(f"\n[DRY RUN] Médicos: {len(medicos)}, Pacientes: {len(pacientes)}, Instituciones: {len(instituciones)}, Tipos: {len(tipos)}, CIE10: {len(cie10)}")

        # ========== INSERTAR MAESTRAS ========== (solo si no es dry run)
        if not DRY_RUN:
            log("📊 INSERTANDO MAESTRAS...\n")
            log("   Médicos...", end=" ")
            for med in medicos:
                pg_cur.execute("INSERT INTO medico (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (med,))
            pc.commit()
            log("✓")
            log("   Pacientes...", end=" ")
            for cod, nom, fnac, gen in pacientes:
                pg_cur.execute(
                    "INSERT INTO paciente (cedula, nombre, fecha_nacimiento, genero) VALUES (%s,%s,%s,%s) ON CONFLICT (cedula) DO NOTHING",
                    (cod, nom, fnac, gen)
                )
            pc.commit()
            log("✓")
            log("   Instituciones...", end=" ")
            for inst in instituciones:
                pg_cur.execute("INSERT INTO institucion (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (inst,))
            pc.commit()
            log("✓")
            log("   Tipos...", end=" ")
            for tipo in tipos:
                pg_cur.execute("INSERT INTO tipo_consulta (nombre) VALUES (%s) ON CONFLICT (nombre) DO NOTHING", (tipo,))
            pc.commit()
            log("✓")
            log("   CIE10...", end=" ")
            for cod in cie10:
                pg_cur.execute("INSERT INTO cie10 (codigo) VALUES (%s) ON CONFLICT (codigo) DO NOTHING", (cod,))
            pc.commit()
            log("✓\n")

        # ========== CARGAR CACHES ========== (igual)
        log("🔄 Cargando IDs en memoria...", end=" ")
        pg_cur.execute("SELECT id, cedula FROM paciente WHERE cedula IS NOT NULL")
        pac_ids = {str(c).strip(): p for p, c in pg_cur.fetchall()}
        pg_cur.execute("SELECT id, nombre FROM medico")
        med_ids = {str(m).strip(): mid for mid, m in pg_cur.fetchall()}
        pg_cur.execute("SELECT id, codigo FROM cie10")
        cie_ids = {str(c).strip(): cid for cid, c in pg_cur.fetchall()}
        pg_cur.execute("SELECT id, nombre FROM institucion")
        inst_ids = {str(i).strip(): iid for iid, i in pg_cur.fetchall()}
        pg_cur.execute("SELECT id, nombre FROM tipo_consulta")
        tip_ids = {str(t).strip(): tid for tid, t in pg_cur.fetchall()}
        log("✓\n")

        # ========== INSERTAR ATENCIONES ========== (solo si no es dry run)
        log("📥 INSERTANDO ATENCIONES...\n")
        acc_cur.execute("""
            SELECT T.IdTs, T.Fecha, C.codcli, C.genero, C.FechaN, T.Cie10, T.Grupo2,
                   T.CodVen, T.SEspecialidad, T.numfac
            FROM EqTraSec T 
            LEFT JOIN EqCtaCli C ON T.CodCli = C.codcli
            ORDER BY T.Fecha DESC
        """)
        atenciones = acc_cur.fetchall()
        log(f"   Total: {len(atenciones):,} atenciones\n")

        if DRY_RUN:
            print(f"[DRY RUN] Se migrarían {len(atenciones):,} atenciones.")
        else:
            batch = []
            cnt = 0
            dinero_total = 0
            inicio = datetime.now()
            for idts, fecha, codcli, genero, fecha_nac, cie10_code, grupo2, vendedor, especialidad, numfac in atenciones:
                if not fecha or not idts:
                    continue
                cc = limpiar(codcli, 20)
                pid = pac_ids.get(cc) if cc else None
                if not pid:
                    continue
                precio = 0  # Sin dinero en esta consulta
                dinero_total += precio
                medico_id = med_ids.get(limpiar(vendedor, 150)) if vendedor else None
                cie10_id = cie_ids.get(cie10_code) if cie10_code else None
                tipo_id = tip_ids.get(limpiar(especialidad, 100)) if especialidad else None
                inst_id = inst_ids.get(limpiar(grupo2, 150)) if grupo2 else None
                medico_codigo = limpiar(vendedor, 50) if vendedor else None
                batch.append((
                    limpiar(idts, 50), fecha, pid, medico_id, cie10_id, tipo_id, inst_id,
                    limpiar(numfac, 50), precio, edad(fecha_nac, fecha) if fecha_nac else 0,
                    limpiar(genero, 10), limpiar(especialidad, 100), precio, precio, medico_codigo
                ))
                cnt += 1
                if len(batch) >= 5000:
                    pg_cur.executemany("""
                        INSERT INTO atencion
                        (idts_access, fecha_atencion, paciente_id, medico_id, cie10_id, tipo_consulta_id,
                         institucion_id, numero_factura, valor_consulta, edad, genero, observaciones,
                         total_consulta, total_general, medico_codigo_access)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (idts_access) DO UPDATE SET
                        valor_consulta=EXCLUDED.valor_consulta, total_general=EXCLUDED.total_general
                    """, batch)
                    pc.commit()
                    batch = []
                    vel = cnt / (datetime.now() - inicio).total_seconds()
                    print(f"\r   ⏳ {cnt:,} | {vel:.0f} reg/s | ${dinero_total:,.2f}     ", end="", flush=True)
            if batch:
                pg_cur.executemany("""
                    INSERT INTO atencion
                    (idts_access, fecha_atencion, paciente_id, medico_id, cie10_id, tipo_consulta_id,
                     institucion_id, numero_factura, valor_consulta, edad, genero, observaciones,
                     total_consulta, total_general, medico_codigo_access)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (idts_access) DO UPDATE SET
                    valor_consulta=EXCLUDED.valor_consulta, total_general=EXCLUDED.total_general
                """, batch)
                pc.commit()
            tiempo = (datetime.now() - inicio).total_seconds()
            print(f"\r   ✓ {cnt:,} en {tiempo:.1f}s\n")

        # ========== VALIDACIÓN ========== (solo si no es dry run)
        if not DRY_RUN:
            log("✅ VALIDACIÓN:\n")
            pg_cur.execute("SELECT COUNT(*) FROM atencion")
            total_at = pg_cur.fetchone()[0]
            log(f"   Atenciones: {total_at:,}")
            pg_cur.execute("SELECT COUNT(*) FROM paciente")
            total_pac = pg_cur.fetchone()[0]
            log(f"   Pacientes: {total_pac:,}")
            pg_cur.execute("SELECT COUNT(*) FROM medico")
            total_med = pg_cur.fetchone()[0]
            log(f"   Médicos: {total_med:,}")
            pg_cur.execute("SELECT SUM(total_general) FROM atencion WHERE total_general > 0")
            din = pg_cur.fetchone()[0] or 0
            log(f"   Dinero: ${din:,.2f}")
            print("\n" + "="*80)
            print("✅ MIGRACIÓN COMPLETADA")
            print("="*80 + "\n")

        ac.close()
        pc.close()
        try:
            os.remove(temp_path)
        except:
            pass

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    ciclo = 1
    while True:
        print(f"\n================ CICLO {ciclo} ==================")
        migrar()
        print(f"[INFO] Esperando {INTERVALO_MINUTOS} minutos para el próximo ciclo...")
        try:
            for i in range(INTERVALO_MINUTOS * 60, 0, -1):
                print(f"\rSiguiente ciclo en {i//60:02d}:{i%60:02d} min", end="", flush=True)
                _time.sleep(1)
            print()
        except KeyboardInterrupt:
            print("\n[INFO] Migración detenida por el usuario.")
            break
        ciclo += 1