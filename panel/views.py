from django.shortcuts import render, redirect
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

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
    from django.db.models import Sum, Count
    from datetime import datetime
    from .models import Atencion, Cita, Especialidad, Servicio

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
    atenciones_qs = Atencion.objects.filter(fecha__range=(fecha_desde, fecha_hasta))
    total_atenciones = atenciones_qs.count()
    agg = atenciones_qs.aggregate(s_consultas=Sum('valor_consulta'), s_medicinas=Sum('valor_medicinas'))
    valor_consultas = agg['s_consultas'] or 0
    valor_medicinas = agg['s_medicinas'] or 0

    # Citas
    citas_qs = Cita.objects.filter(fecha__range=(fecha_desde, fecha_hasta))
    numero_citas = citas_qs.count()
    cancelaciones = citas_qs.filter(estado=Cita.ESTADO_CANCELADA).count()

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
    }
    return render(request, "index.html", context)


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
    from .models import Especialidad, Servicio, Atencion
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

