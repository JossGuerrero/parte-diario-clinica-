import os
import hashlib
import time
from datetime import datetime, date
import decimal
from django.conf import settings
from .models import PanelAtencion, PanelEspecialidad, PanelServicio

DEFAULT_TABLES = ['Eqtrasec', 'Ctacli', 'Eqctavdd']


def try_connect(db_path, pwd):
    import pyodbc
    conn_options = [
        f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};PWD={pwd};",
        f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};PWD={pwd};Mode=Read;",
        f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};Mode=Read;",
        f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};",
    ]
    last_err = None
    for opt in conn_options:
        for i in range(5):
            try:
                cn = pyodbc.connect(opt, autocommit=True)
                return cn
            except Exception as e:
                last_err = e
                if 'locked' in str(e).lower():
                    time.sleep(0.5)
                    continue
                break
    if last_err:
        raise last_err
    raise Exception('Unable to connect to Access file')


def row_hash(cols, row):
    m = hashlib.sha256()
    for c in cols:
        v = row.get(c)
        m.update((str(v) + '|').encode('utf-8'))
    return m.hexdigest()


def import_from_access(file_path, pwd=None, tables=None):
    """Import from a given Access file. Returns a summary dict with counts and errors."""
    if tables is None:
        tables = DEFAULT_TABLES
    summary = {'imported': 0, 'details': {}, 'errors': []}

    cn = try_connect(file_path, pwd)
    cur = cn.cursor()

    for table in tables:
        try:
            cur.execute(f"SELECT * FROM [{table}]")
        except Exception as e:
            summary['errors'].append((table, str(e)))
            continue
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        imported = 0
        # use a simple transaction scope per table
        from django.db import transaction
        with transaction.atomic():
            for r in rows:
                row = dict(zip(cols, r))
                s_hash = row_hash(cols, row)
                if PanelAtencion.objects.filter(source_table=table, source_hash=s_hash).exists():
                    continue
                # fecha
                fecha = None
                for key in ('fecha', 'date', 'fechaatencion', 'F_Atencion', 'Fecha', 'FechaAtencion'):
                    for rk in row.keys():
                        if rk.lower() == key.lower() and row.get(rk) is not None:
                            v = row.get(rk)
                            if hasattr(v, 'date'):
                                fecha = v.date() if isinstance(v, datetime) else v
                            else:
                                try:
                                    fecha = datetime.strptime(str(v), '%d/%m/%Y').date()
                                except Exception:
                                    try:
                                        fecha = datetime.strptime(str(v), '%Y-%m-%d').date()
                                    except Exception:
                                        fecha = None
                            break
                    if fecha:
                        break
                def to_decimal_from_row(kcandidates):
                    for kc in kcandidates:
                        for k in row.keys():
                            if k.lower() == kc.lower() and row[k] is not None:
                                try:
                                    return decimal.Decimal(str(row[k]))
                                except Exception:
                                    try:
                                        return decimal.Decimal(float(row[k]))
                                    except Exception:
                                        return decimal.Decimal('0')
                    return decimal.Decimal('0')
                valor_consulta = to_decimal_from_row(['VALOR_CONSULTA','valor','valorconsulta','VALOR'])
                valor_medicinas = to_decimal_from_row(['TOT_Medicina','valor_medicina','valor_medicinas','TOT_Medicina','total_medicina'])
                esp_name = None
                serv_name = None
                for k in row.keys():
                    if k.lower() in ('especialidad','especiality','especialidad_nombre','especialidadname') and row[k]:
                        esp_name = str(row[k]).strip()
                    if k.lower() in ('servicio','service','servicio_nombre') and row[k]:
                        serv_name = str(row[k]).strip()
                if not esp_name:
                    esp_name = 'General'
                if not serv_name:
                    serv_name = 'Consulta'
                esp, _ = PanelEspecialidad.objects.get_or_create(nombre=esp_name)
                serv, _ = PanelServicio.objects.get_or_create(nombre=serv_name)
                institucion = None
                for k in ('institucion','institution','convenio'):
                    for rk in row.keys():
                        if rk.lower() == k and row[rk]:
                            institucion = str(row[rk]).strip()
                            break
                    if institucion:
                        break
                genero = None
                for k in ('genero','sexo'):
                    for rk in row.keys():
                        if rk.lower() == k and row[rk]:
                            genero = str(row[rk]).strip()
                            break
                    if genero:
                        break
                edad = None
                for k in ('edad','age'):
                    for rk in row.keys():
                        if rk.lower() == k and row[rk] is not None:
                            try:
                                edad = int(row[rk])
                            except Exception:
                                try:
                                    edad = int(float(row[rk]))
                                except Exception:
                                    edad = None
                            break
                    if edad is not None:
                        break
                solicitado_a = None
                for k in ('sesolicitaa','seSolicitaA','solicitado_por','profesional'):
                    for rk in row.keys():
                        if rk.lower() == k.lower() and row[rk]:
                            solicitado_a = str(row[rk]).strip()
                            break
                    if solicitado_a:
                        break
                pa = PanelAtencion(
                    fecha=fecha or date.today(),
                    valor_consulta=valor_consulta,
                    valor_medicinas=valor_medicinas,
                    especialidad=esp,
                    servicio=serv,
                    source_table=table,
                    source_hash=s_hash,
                    raw={k: (v.isoformat() if hasattr(v,'isoformat') else (str(v) if v is not None else None)) for k, v in row.items()},
                    institucion=institucion,
                    genero=genero,
                    edad=edad,
                    solicitado_a=solicitado_a,
                )
                pa.save()
                imported += 1
        summary['details'][table] = imported
        summary['imported'] += imported
    cn.close()
    return summary
