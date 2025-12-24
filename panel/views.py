from django.shortcuts import render, redirect
from datetime import date, timedelta, datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count

import io
import decimal

import csv

from .models import (
    Paciente,
    PanelAtencion,
    Cita,
    PanelEspecialidad,
    PanelServicio,
    Estadocita,
    DailyEqctacliSummary,
)  # Importamos tu modelo de SQL Server and related models used by views

# Backwards-compatible aliases used by older code
Atencion = PanelAtencion
Especialidad = PanelEspecialidad
Servicio = PanelServicio

def lista_pacientes(request):
    # Traemos todos los registros de la tabla 'paciente' de HHSCJEC_prueba
    pacientes = Paciente.objects.all()


    # Enviamos los datos al archivo HTML (que crearemos en el siguiente paso)
    return render(request, 'panel/pacientes_list.html', {'pacientes': pacientes})

@login_required(login_url='login')
def index(request):
    # additionally enforce superuser (logout and redirect if not)
    if not request.user.is_superuser:
        logout(request)
        return redirect('login')

    today = date.today()
    fecha_hasta = today.strftime("%d/%m/%Y")
    fecha_desde = (today - timedelta(days=7)).strftime("%d/%m/%Y")

    # parse date range from GET or use last 7 days
    from datetime import datetime

    def parse_date(s, default):
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except Exception:
            return default

    total_atenciones = 0
    valor_consultas = 0
    valor_medicinas = 0
    numero_citas = 0
    cancelaciones = 0
    resumen_especialidades = []
    servicios_top = []

    # get filter range
    desde_str = request.GET.get('desde')
    hasta_str = request.GET.get('hasta')
    if desde_str and hasta_str:
        fecha_desde = parse_date(desde_str, (date.today() - timedelta(days=7)))
        fecha_hasta = parse_date(hasta_str, date.today())
    else:
        fecha_hasta = date.today()
        fecha_desde = date.today() - timedelta(days=7)

    # Atenciones dentro del rango
    from django.db import ProgrammingError, OperationalError
    db_error = None
    try:
        atenciones_qs = Atencion.objects.filter(fecha__range=(fecha_desde, fecha_hasta))
        total_atenciones = atenciones_qs.count()
        agg = atenciones_qs.aggregate(s_consultas=Sum('valor_consulta'), s_medicinas=Sum('valor_medicinas'))
        valor_consultas = agg['s_consultas'] or 0
        valor_medicinas = agg['s_medicinas'] or 0

        # servicios top and resumen por especialidad will be computed below from atenciones_qs
        citas_qs = Cita.objects.filter(fechacita__range=(fecha_desde, fecha_hasta))
        numero_citas = citas_qs.count()
        # Attempt to detect cancelled state using Estadocita description, fallback to common estado values
        cancelaciones = 0
        try:
            cancel_state = Estadocita.objects.filter(descripcion__icontains='cancel').first()
            if cancel_state:
                cancelaciones = citas_qs.filter(idestadocita=cancel_state).count()
            else:
                cancelaciones = citas_qs.filter(estado__in=[2, 3]).count()
        except Exception:
                cancelaciones = citas_qs.filter(estado__in=[2, 3]).count()
    except (ProgrammingError, OperationalError) as e:
        # Database does not have the expected tables or is unreachable; fall back to safe defaults
        db_error = str(e)
        total_atenciones = 0
        valor_consultas = 0
        valor_medicinas = 0
        numero_citas = 0
        cancelaciones = 0
        # Make empty querysets for downstream code
        atenciones_qs = Atencion.objects.none()
        servicios_top = []
        resumen_especialidades = []

    # resumen por especialidad
    if total_atenciones > 0:
        espec_qs = atenciones_qs.values('especialidad__nombre').annotate(cantidad=Count('id')).order_by('-cantidad')
        resumen_especialidades = []
        for e in espec_qs:
            pct = round((e['cantidad'] / total_atenciones) * 100, 1)
            resumen_especialidades.append({'nombre': e['especialidad__nombre'], 'porcentaje': pct})

    # servicios top
    serv_qs = atenciones_qs.values('servicio__nombre').annotate(cantidad=Count('id')).order_by('-cantidad')[:5]
    servicios_top = []
    max_c = max([s['cantidad'] for s in serv_qs], default=1)
    for s in serv_qs:
        pct = round((s['cantidad'] / max_c) * 100, 1)
        servicios_top.append({'nombre': s['servicio__nombre'], 'porcentaje': pct, 'cantidad': s['cantidad']})

    total_recaudado = float(valor_consultas or 0) + float(valor_medicinas or 0)

    # If DB queries failed, log the problem but do not show a persistent warning on the dashboard
    if db_error:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Error leyendo datos reales desde la base de datos: %s", db_error)

    context = {
        "total_atenciones": total_atenciones,
        "valor_consultas": float(valor_consultas),
        "valor_medicinas": float(valor_medicinas),
        "numero_citas": numero_citas,
        "cancelaciones": cancelaciones,
        "total_recaudado": total_recaudado,
        "fecha_desde": fecha_desde.strftime('%d/%m/%Y'),
        "fecha_hasta": fecha_hasta.strftime('%d/%m/%Y'),
        "resumen_especialidades": resumen_especialidades,
        "servicios_top": servicios_top,
        "db_error": db_error,
    }
    return render(request, "index.html", context)


@login_required(login_url='login')
def dashboard(request):
    # simple page shell, heavy lifting in API view
    if not request.user.is_superuser:
        return redirect('login')
    return render(request, 'panel/dashboard.html')


@login_required(login_url='login')
def dashboard_api(request):
    """Returns aggregated data per day as JSON for charting and table."""
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    medico = request.GET.get('medico')
    institucion = request.GET.get('institucion')

    # using top-level imports for models and db functions
    # datetime is available from module-level imports

    # parse dates
    try:
        d_from = datetime.strptime(desde, '%Y-%m-%d').date() if desde else None
        d_to = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else None
    except Exception:
        return JsonResponse({'error': 'Fecha inválida'}, status=400)

    # if a full-day range and Daily summaries exist, use them for speed
    use_summaries = False
    if d_from and d_to:
        qs_sum = DailyEqctacliSummary.objects.filter(date__range=(d_from, d_to))
        if qs_sum.exists() and not medico and not institucion:
            use_summaries = True

    labels = []
    datasets = {'atenciones': [], 'total_consulta': [], 'total_medicina': []}
    rows = []

    if use_summaries:
        sums = qs_sum.order_by('date')
        for s in sums:
            labels.append(s.date.strftime('%Y-%m-%d'))
            datasets['atenciones'].append(s.num_atenciones)
            datasets['total_consulta'].append(float(s.total_consulta))
            datasets['total_medicina'].append(float(s.total_medicina))
            rows.append({'periodo': s.date.strftime('%Y-%m-%d'), 'atenciones': s.num_atenciones, 'total_consulta': float(s.total_consulta), 'total_medicina': float(s.total_medicina)})
        return JsonResponse({'labels': labels, 'datasets': datasets, 'rows': rows})

    # fallback: compute from PanelAtencion applying filters
    qs = PanelAtencion.objects.all()
    if d_from and d_to:
        qs = qs.filter(fecha__range=(d_from, d_to))
    if medico:
        qs = qs.filter(solicitado_a__icontains=medico)
    if institucion:
        qs = qs.filter(institucion__iexact=institucion)

    # group by fecha (day)
    bydate = qs.values('fecha').annotate(atenciones=Count('id'), total_consulta=Sum('valor_consulta'), total_medicina=Sum('valor_medicinas')).order_by('fecha')
    for b in bydate:
        labels.append(b['fecha'].strftime('%Y-%m-%d'))
        datasets['atenciones'].append(b['atenciones'])
        datasets['total_consulta'].append(float(b['total_consulta'] or 0))
        datasets['total_medicina'].append(float(b['total_medicina'] or 0))
        rows.append({'periodo': b['fecha'].strftime('%Y-%m-%d'), 'atenciones': b['atenciones'], 'total_consulta': float(b['total_consulta'] or 0), 'total_medicina': float(b['total_medicina'] or 0)})

    return JsonResponse({'labels': labels, 'datasets': datasets, 'rows': rows})


@login_required(login_url='login')
def dashboard_export_csv(request):
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    medico = request.GET.get('medico')
    institucion = request.GET.get('institucion')

    # PanelAtencion, datetime, Sum and Count are available from module-level imports

    try:
        d_from = datetime.strptime(desde, '%Y-%m-%d').date() if desde else None
        d_to = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else None
    except Exception:
        return HttpResponse('Fecha inválida', status=400)

    qs = PanelAtencion.objects.all()
    if d_from and d_to:
        qs = qs.filter(fecha__range=(d_from, d_to))
    if medico:
        qs = qs.filter(solicitado_a__icontains=medico)
    if institucion:
        qs = qs.filter(institucion__iexact=institucion)

    bydate = (
        qs.values('fecha')
        .annotate(
            atenciones=Count('id'),
            total_consulta=Sum('valor_consulta'),
            total_medicina=Sum('valor_medicinas'),
        )
        .order_by('fecha')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dashboard_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['periodo', 'atenciones', 'total_consulta', 'total_medicina'])
    for b in bydate:
        writer.writerow([
            b['fecha'].strftime('%Y-%m-%d'),
            b['atenciones'],
            float(b['total_consulta'] or 0),
            float(b['total_medicina'] or 0),
        ])
    return response


@login_required(login_url='login')
def dashboard_export_xlsx(request):
    """Export aggregated dashboard rows to an Excel (.xlsx) file."""
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    medico = request.GET.get('medico')
    institucion = request.GET.get('institucion')

    from .models import PanelAtencion
    from datetime import datetime
    from django.db.models import Sum, Count
    import io

    try:
        d_from = datetime.strptime(desde, '%Y-%m-%d').date() if desde else None
        d_to = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else None
    except Exception:
        return HttpResponse('Fecha inválida', status=400)

    qs = PanelAtencion.objects.all()
    if d_from and d_to:
        qs = qs.filter(fecha__range=(d_from, d_to))
    if medico:
        qs = qs.filter(solicitado_a__icontains=medico)
    if institucion:
        qs = qs.filter(institucion__iexact=institucion)

    bydate = qs.values('fecha').annotate(atenciones=Count('id'), total_consulta=Sum('valor_consulta'), total_medicina=Sum('valor_medicinas')).order_by('fecha')

    # Build XLSX using openpyxl if available
    try:
        from openpyxl import Workbook
    except Exception:
        return HttpResponse('openpyxl library not installed', status=500)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Dashboard'

    # header
    ws.append(['periodo', 'atenciones', 'total_consulta', 'total_medicina'])
    for b in bydate:
        ws.append([b['fecha'].strftime('%Y-%m-%d'), b['atenciones'], float(b['total_consulta'] or 0), float(b['total_medicina'] or 0)])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    response = HttpResponse(bio.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="dashboard_export.xlsx"'
    return response


@login_required(login_url='login')
def dashboard_export_pdf(request):
    """Export aggregated dashboard rows to a simple PDF (ReportLab)."""
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    medico = request.GET.get('medico')
    institucion = request.GET.get('institucion')

    from .models import PanelAtencion
    from datetime import datetime
    from django.db.models import Sum, Count
    import io

    try:
        d_from = datetime.strptime(desde, '%Y-%m-%d').date() if desde else None
        d_to = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else None
    except Exception:
        return HttpResponse('Fecha inválida', status=400)

    qs = PanelAtencion.objects.all()
    if d_from and d_to:
        qs = qs.filter(fecha__range=(d_from, d_to))
    if medico:
        qs = qs.filter(solicitado_a__icontains=medico)
    if institucion:
        qs = qs.filter(institucion__iexact=institucion)

    bydate = qs.values('fecha').annotate(atenciones=Count('id'), total_consulta=Sum('valor_consulta'), total_medicina=Sum('valor_medicinas')).order_by('fecha')

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception:
        return HttpResponse('reportlab library not installed', status=500)

    bio = io.BytesIO()
    p = canvas.Canvas(bio, pagesize=letter)
    width, height = letter

    y = height - 40
    p.setFont('Helvetica-Bold', 12)
    p.drawString(40, y, 'Dashboard - Parte Diario')
    y -= 30

    p.setFont('Helvetica-Bold', 10)
    p.drawString(40, y, 'Periodo')
    p.drawString(150, y, 'Atenciones')
    p.drawString(260, y, 'Total Consulta')
    p.drawString(380, y, 'Total Medicina')
    y -= 15
    p.setFont('Helvetica', 10)

    for b in bydate:
        if y < 80:
            p.showPage()
            y = height - 40
        p.drawString(40, y, b['fecha'].strftime('%Y-%m-%d'))
        p.drawString(150, y, str(b['atenciones']))
        p.drawString(260, y, f"{float(b['total_consulta'] or 0):.2f}")
        p.drawString(380, y, f"{float(b['total_medicina'] or 0):.2f}")
        y -= 15

    p.save()
    bio.seek(0)

    response = HttpResponse(bio.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="dashboard_export.pdf"'
    return response


# ---- User management views (CRUD) ----
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, UserForm


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'panel/users_list.html'
    context_object_name = 'users'
    paginate_by = 25


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'panel/user_form.html'
    success_url = reverse_lazy('panel:users_list')


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'panel/user_form.html'
    success_url = reverse_lazy('panel:users_list')


class UserDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'panel/user_confirm_delete.html'
    success_url = reverse_lazy('panel:users_list')


@login_required(login_url='login')
def import_atenciones(request):
    # only superusers allowed
    if not request.user.is_superuser:
        return redirect('login')

    import csv
    from io import TextIOWrapper
    # Using module-level model imports: Especialidad, Servicio, Atencion
    from django.contrib import messages

    if request.method == 'POST' and request.FILES.get('csvfile'):
        csvfile = request.FILES['csvfile']
        try:
            text_file = TextIOWrapper(csvfile.file, encoding='utf-8')
        except Exception:
            text_file = TextIOWrapper(csvfile.file, encoding='latin-1')
        reader = csv.DictReader(text_file)
        created = 0
        for row in reader:
            # expected keys: fecha, especialidad, servicio, valor_consulta, valor_medicinas
            fecha_str = row.get('fecha') or row.get('date')
            # support formats dd/mm/YYYY or YYYY-MM-DD
            from datetime import datetime
            fecha = None
            for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                try:
                    fecha = datetime.strptime(fecha_str, fmt).date()
                    break
                except Exception:
                    continue
            if fecha is None:
                continue
            esp_name = row.get('especialidad') or row.get('especialidad_nombre') or row.get('especiality')
            serv_name = row.get('servicio') or row.get('servicio_nombre') or row.get('service')
            if not esp_name or not serv_name:
                continue
            esp, _ = Especialidad.objects.get_or_create(nombre=esp_name.strip())
            serv, _ = Servicio.objects.get_or_create(nombre=serv_name.strip())
            try:
                valor_consulta = float(row.get('valor_consulta', 0) or 0)
                valor_medicinas = float(row.get('valor_medicinas', 0) or 0)
            except Exception:
                valor_consulta = 0
                valor_medicinas = 0
            Atencion.objects.create(fecha=fecha, especialidad=esp, servicio=serv, valor_consulta=valor_consulta, valor_medicinas=valor_medicinas)
            created += 1
        messages.success(request, f'Importadas {created} atenciones')
        return redirect('panel:index')

    return render(request, 'panel/import_atenciones.html')


# -------- Importar desde Access (.mdb / .accdb) --------
import tempfile
import os
from django.contrib.auth.decorators import user_passes_test

def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_active and u.is_superuser, login_url='login')(view_func)


@superuser_required
def import_access(request):
    """Two-step flow for importing Access files.

    - POST action='inspect': inspect the uploaded file or a persisted file and optionally remember a session password.
    - POST action='import': import rows from a selected table into PanelAtencion. Temporary uploads are cleaned after import.
    """
    try:
        import pyodbc
    except Exception as e:
        return render(request, 'panel/import_access.html', {'pyodbc_missing': True, 'pyodbc_error': str(e)})

    from .models import PanelAtencion, PanelEspecialidad, PanelServicio
    from django.db import transaction
    from django.contrib import messages
    from datetime import date
    import time
    from django.conf import settings
    from django.core import signing

    MEDIA_ACCESS_DIR = os.path.join(settings.MEDIA_ROOT, 'access')
    PERSIST_FILENAME = 'clinic'

    def try_connect_and_list(db_path, pwd):
        """Try multiple connection options and retries, returning only the required tables.
        This is defensive against Access files locked by another process.
        """
        import time
        required = ['eqtrasec', 'ctacli', 'eqctavdd']
        attempts = 5
        sleep_sec = 0.5
        conn_options = []
        # Prefer using supplied password, try read mode, then without password as fallback
        conn_options.append(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};PWD={pwd};")
        conn_options.append(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};PWD={pwd};Mode=Read;")
        conn_options.append(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};Mode=Read;")
        conn_options.append(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};")

        last_err = None
        for opt in conn_options:
            for i in range(attempts):
                try:
                    cn = pyodbc.connect(opt, autocommit=True)
                    cur = cn.cursor()
                    tables = [row.table_name for row in cur.tables(tableType='TABLE') if row.table_name]
                    cn.close()
                    # filter found tables to only the required ones (case-insensitive)
                    lower_to_orig = {t.lower(): t for t in tables}
                    found = [lower_to_orig[r] for r in required if r in lower_to_orig]
                    return found
                except Exception as e:
                    last_err = e
                    # If file is locked, wait and retry
                    if 'locked' in str(e).lower():
                        time.sleep(sleep_sec)
                        continue
                    # Otherwise break to try next connection option
                    break
        # If we exhausted options and have an error, raise it so caller can show a message
        if last_err:
            raise last_err
        return []

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'inspect':
            use_existing = request.POST.get('use_existing') == '1'
            persist = request.POST.get('persist') == '1'
            remember_pwd = request.POST.get('remember_pwd') == '1'
            password = request.POST.get('access_password', '')

            if use_existing:
                stored = request.session.get('access_file_path')
                if not stored or not os.path.exists(stored):
                    messages.error(request, 'No hay un archivo Access persistente cargado.')
                    return redirect('panel:import_access')
                # if no password provided, try to get from session
                if not password:
                    signed = request.session.get('access_pwd_signed')
                    if signed:
                        try:
                            password = signing.loads(signed)
                        except Exception:
                            password = ''
                try:
                    tables = try_connect_and_list(stored, password)
                    if not tables:
                        messages.error(request, 'No se encontraron las tablas requeridas: Eqtrasec, Ctacli, Eqctavdd en el archivo Access persistente.')
                        return redirect('panel:import_access')
                    return render(
                        request,
                        'panel/import_access.html',
                        {
                            'tables': tables,
                            'connected': True,
                            'file_name': request.session.get('access_file_original_name', 'archivo_access.accdb'),
                            'persisted': True,
                        },
                    )
                except Exception as e:
                    messages.error(request, f'No se pudo conectar al archivo Access persistente: {e}')
                    return redirect('panel:import_access')

            # else, we have an uploaded file in this request
            f = request.FILES.get('access_file')
            if not f:
                messages.error(request, 'Seleccione un archivo .mdb o .accdb')
                return redirect('panel:import_access')
            # validate extension
            suffix = os.path.splitext(f.name)[1].lower()
            if suffix not in ('.mdb', '.accdb'):
                messages.error(request, 'Formato no soportado. Use .mdb o .accdb')
                return redirect('panel:import_access')

            if persist:
                os.makedirs(MEDIA_ACCESS_DIR, exist_ok=True)
                dest_path = os.path.join(MEDIA_ACCESS_DIR, PERSIST_FILENAME + suffix)
                with open(dest_path, 'wb') as wf:
                    for chunk in f.chunks():
                        wf.write(chunk)
                # store persistent path and original filename in session
                request.session['access_file_path'] = dest_path
                request.session['access_file_original_name'] = f.name
                request.session.modified = True
            else:
                tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tempfile.gettempdir())
                for chunk in f.chunks():
                    tf.write(chunk)
                tf.close()
                dest_path = tf.name
                # store temp path for cleanup later
                request.session['access_temp_file'] = dest_path
                request.session.modified = True

            # try connect and list tables
            try:
                tables = try_connect_and_list(dest_path, password)
                # if user asked to remember password for this session and we have a password, store signed
                if remember_pwd and password:
                    request.session['access_pwd_signed'] = signing.dumps(password)
                    request.session.modified = True
                if not tables:
                    # cleanup temp file if any
                    try:
                        if not persist and os.path.exists(dest_path):
                            os.unlink(dest_path)
                    except Exception:
                        pass
                    messages.error(request, 'No se encontraron las tablas requeridas: Eqtrasec, Ctacli, Eqctavdd en el archivo Access.')
                    return redirect('panel:import_access')
                return render(request, 'panel/import_access.html', {'tables': tables, 'connected': True, 'file_name': f.name, 'persisted': persist})
            except Exception as e:
                # cleanup temp file if any
                try:
                    if not persist and os.path.exists(dest_path):
                        os.unlink(dest_path)
                except Exception:
                    pass
                messages.error(request, f'No se pudo conectar al archivo Access: {e}')
                return redirect('panel:import_access')

        elif action == 'import':
            table = request.POST.get('table')
            password = request.POST.get('access_password', '')
            # determine which file to use: persistent takes precedence
            persistent_path = request.session.get('access_file_path')
            temp_path = request.session.get('access_temp_file')
            use_path = None
            is_persistent = False
            if persistent_path and os.path.exists(persistent_path):
                use_path = persistent_path
                is_persistent = True
                # if no password provided, try to read from signed session value
                if not password:
                    signed = request.session.get('access_pwd_signed')
                    if signed:
                        try:
                            password = signing.loads(signed)
                        except Exception:
                            password = ''
            elif temp_path and os.path.exists(temp_path):
                use_path = temp_path
            else:
                messages.error(request, 'No hay un archivo Access disponible para importar.')
                return redirect('panel:import_access')

            if not table or not use_path:
                messages.error(request, 'Falta información para importar.')
                return redirect('panel:import_access')

            # ensure only allowed tables can be imported
            allowed_tables = ['eqtrasec', 'ctacli', 'eqctavdd']
            if table.lower() not in allowed_tables:
                messages.error(request, 'Tabla no permitida. Solo se permiten: Eqtrasec, Ctacli, Eqctavdd')
                return redirect('panel:import_access')

            conn_options = [
                f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={use_path};PWD={password};",
                f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={use_path};PWD={password};Mode=Read;",
                f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={use_path};Mode=Read;",
                f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={use_path};",
            ]
            imported = 0
            last_err = None
            cols = None
            rows = None
            for opt in conn_options:
                for attempt in range(5):
                    try:
                        cn = pyodbc.connect(opt, autocommit=True)
                        cur = cn.cursor()
                        cur.execute(f"SELECT * FROM [{table}]")
                        cols = [c[0] for c in cur.description]
                        rows = cur.fetchall()
                        try:
                            cn.close()
                        except Exception:
                            pass
                        break
                    except Exception as e:
                        last_err = e
                        if 'locked' in str(e).lower():
                            time.sleep(0.5)
                            continue
                        else:
                            break
                if rows is not None:
                    break

            if rows is None:
                messages.error(request, f'Error al importar: {last_err}')
                return redirect('panel:import_access')

            try:
                objs = []
                with transaction.atomic():
                    for r in rows:
                        row = dict(zip(cols, r))
                        # map common column names (same mapping as before)
                        fecha = None
                        for key in ('fecha', 'date', 'fechaatencion', 'fecha_at', 'fecha_atencion'):
                            if key in row and row[key] is not None:
                                v = row[key]
                                if isinstance(v, (datetime, date)):
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
                        esp_name = None
                        serv_name = None
                        for key in ('especialidad', 'especiality', 'especialidad_nombre', 'especialidadName'):
                            if key in row and row[key]:
                                esp_name = str(row[key]).strip()
                                break
                        for key in ('servicio','service','servicio_nombre'):
                            if key in row and row[key]:
                                serv_name = str(row[key]).strip()
                                break
                        if not esp_name:
                            esp_name = 'General'
                        if not serv_name:
                            serv_name = 'Consulta'
                        esp, _ = PanelEspecialidad.objects.get_or_create(nombre=esp_name)
                        serv, _ = PanelServicio.objects.get_or_create(nombre=serv_name)

                        def to_decimal(k):
                            for cand in (k, k.lower(), k.upper()):
                                if cand in row and row[cand] is not None:
                                    try:
                                        return decimal.Decimal(str(row[cand]))
                                    except Exception:
                                        try:
                                            return decimal.Decimal(float(row[cand]))
                                        except Exception:
                                            return decimal.Decimal('0')
                            return decimal.Decimal('0')
                        valor_consulta = to_decimal('valor_consulta') or to_decimal('valorconsulta') or to_decimal('valor')
                        valor_medicinas = to_decimal('valor_medicinas') or to_decimal('valormedicinas') or decimal.Decimal('0')

                        obj = PanelAtencion(fecha=fecha or date.today(), especialidad=esp, servicio=serv, valor_consulta=valor_consulta, valor_medicinas=valor_medicinas)
                        objs.append(obj)
                    # bulk create after iterating all rows
                    PanelAtencion.objects.bulk_create(objs)
                    imported = len(objs)
            except Exception as e:
                messages.error(request, f'Error al importar: {e}')
            finally:
                # cleanup temp file and session if it was a temp upload
                try:
                    if not is_persistent and temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                except Exception:
                    pass
                request.session.pop('access_temp_file', None)
            if imported:
                messages.success(request, f'Importadas {imported} filas desde {table}')
            return redirect('panel:import_access')

    # GET
    # detect if we have a persistent file already
    persisted_info = None
    persisted_path = request.session.get('access_file_path')
    if persisted_path and os.path.exists(persisted_path):
        persisted_info = {
            'path': persisted_path,
            'original_name': request.session.get('access_file_original_name', os.path.basename(persisted_path))
        }

    return render(request, 'panel/import_access.html', {'persisted_info': persisted_info})


@superuser_required
def run_import_access(request):
    """Manual trigger (superuser) to run the persistent import using environment password or provided password via POST."""
    from .access_importer import import_from_access
    import os
    from django.conf import settings
    if request.method == 'POST':
        pwd = request.POST.get('access_password') or os.environ.get('ACCESS_PERSISTENT_PWD') or getattr(settings, 'ACCESS_PERSISTENT_PWD', '')
        media_access = os.path.join(settings.MEDIA_ROOT, 'access')
        for name in ('clinic.accdb', 'clinic.mdb'):
            p = os.path.join(media_access, name)
            if os.path.exists(p):
                file_path = p
                break
        else:
            messages.error(request, 'No se encontró archivo persistente en MEDIA/access. Sube el archivo e intenta de nuevo.')
            return redirect('panel:import_access')
        summary = import_from_access(file_path, pwd=pwd)
        if summary.get('errors'):
            for t, e in summary['errors']:
                messages.error(request, f'Error en tabla {t}: {e}')
        for t, cnt in summary.get('details', {}).items():
            messages.success(request, f'Importadas {cnt} filas de {t}')
        messages.success(request, f"Importación completa. Total importadas: {summary.get('imported',0)}")
    return redirect('panel:import_access')


# Simple logout view that accepts GET and POST and redirects to login
from django.contrib.auth import logout as auth_logout

@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Log out the current user and redirect to the login page."""
    auth_logout(request)
    return redirect('login')


@superuser_required
def export_access(request):
    """Feature temporarily disabled: only import is allowed for now."""
    from django.contrib import messages
    messages.info(request, 'Funcionalidad deshabilitada: por ahora solo está permitida la importación de Access.')
    return redirect('panel:import_access')


@superuser_required
def access_queries(request):
    """Temporarily disabled: only import is allowed at the moment."""
    messages.info(request, 'Funcionalidad deshabilitada: por ahora solo está permitida la importación de Access.')
    return redirect('panel:import_access')


@superuser_required
def report_view(request):
    """Render the pasantias report Markdown file inside the app (read-only)."""
    doc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs', 'reporte_pasantias.md'))
    try:
        with open(doc_path, 'r', encoding='utf-8') as fh:
            content = fh.read()
    except Exception as e:
        messages.error(request, f'No se pudo leer el documento: {e}')
        return redirect('panel:index')
    # show as preformatted text (simple and reliable)
    return render(request, 'panel/report.html', {'content': content})


def home_redirect(request):
    """Redirect root URL:
    - unauthenticated users -> login
    - authenticated superusers -> dashboard index
    - authenticated non-superusers -> logout + login page with error (avoid redirect loops)
    """
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('panel:index')
        # authenticated but not superuser: log out and show an error
        messages.error(request, "Solo los superusuarios pueden acceder a esta aplicación.")
        logout(request)
        return redirect('login')
    return redirect('login')

