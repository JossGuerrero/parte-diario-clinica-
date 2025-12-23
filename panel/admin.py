from django.contrib import admin
from .models import Especialidad, Cita, Paciente, Atencionambulatoria, Usuario

admin.site.register(Especialidad)
admin.site.register(Cita)
admin.site.register(Paciente)
admin.site.register(Atencionambulatoria)
admin.site.register(Usuario)