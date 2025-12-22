from django.contrib import admin
from .models import Especialidad, Servicio, Atencion, Cita

@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')

@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'especialidad', 'servicio', 'valor_consulta', 'valor_medicinas')
    list_filter = ('especialidad', 'servicio')
    search_fields = ('especialidad__nombre', 'servicio__nombre')

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'estado')
    list_filter = ('estado',)

