from django.shortcuts import render, redirect
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from django.shortcuts import render
from .models import Paciente  # Importamos tu modelo de SQL Server

def lista_pacientes(request):
    # Traemos todos los registros de la tabla 'paciente' de HHSCJEC_prueba
    pacientes = Paciente.objects.all() 
    
    # Enviamos los datos al archivo HTML (que crearemos en el siguiente paso)
    return render(request, 'panel/pacientes_list.html', {'pacientes': pacientes})

@login_required(login_url='login')
def index(request):
    if not request.user.is_superuser:
        logout(request)
        return redirect('login')

    from django.db.models import Count
    from datetime import date, timedelta, datetime
    from .models import Atencionambulatoria, Cita

    # 1. Configuración de fechas
    today = date.today()
    desde_str = request.GET.get('desde')
    hasta_str = request.GET.get('hasta')

    def parse_date(s, default):
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except:
            return default

    fecha_desde = parse_date(desde_str, today - timedelta(days=7))
    fecha_hasta = parse_date(hasta_str, today)

    # 2. Consultas con nombres reales de tu SQL Server
    # Cambiamos 'fechaAtencion' por 'fechaatencion' (Django suele poner todo en minúsculas)
    atenciones_qs = Atencionambulatoria.objects.filter(fechaatencion__range=(fecha_desde, fecha_hasta))
    total_atenciones = atenciones_qs.count()

    # Filtro de Citas usando 'fechacita'
    citas_qs = Cita.objects.filter(fechacita__range=(fecha_desde, fecha_hasta))
    numero_citas = citas_qs.count()
    
    # Filtro de cancelaciones usando 'idestadocita' (ajusta el ID según tu BD)
    cancelaciones = citas_qs.filter(idestadocita_id=3).count()

    # 3. Valores financieros (Se dejan en 0 porque no existen en Atencionambulatoria)
    context = {
        "total_atenciones": total_atenciones,
        "valor_consultas": 0.0,
        "valor_medicinas": 0.0,
        "numero_citas": numero_citas,
        "cancelaciones": cancelaciones,
        "total_recaudado": 0.0,
        "fecha_desde": fecha_desde.strftime('%d/%m/%Y'),
        "fecha_hasta": fecha_hasta.strftime('%d/%m/%Y'),
        "resumen_especialidades": [], 
        "servicios_top": [],
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

