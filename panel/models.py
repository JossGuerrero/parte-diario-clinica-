from django.db import models

class Especialidad(models.Model):
    nombre = models.CharField(max_length=120)

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    nombre = models.CharField(max_length=120)

    def __str__(self):
        return self.nombre


class Atencion(models.Model):
    fecha = models.DateField()
    especialidad = models.ForeignKey(Especialidad, on_delete=models.PROTECT)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT)
    valor_consulta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_medicinas = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Atención {self.id} - {self.fecha} - {self.especialidad}"


class Cita(models.Model):
    ESTADO_PROGRAMADA = 'programada'
    ESTADO_CONFIRMADA = 'confirmada'
    ESTADO_CANCELADA = 'cancelada'
    ESTADO_CHOICES = [
        (ESTADO_PROGRAMADA, 'Programada'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PROGRAMADA)

    def __str__(self):
        return f"Cita {self.id} - {self.fecha} - {self.estado}"

