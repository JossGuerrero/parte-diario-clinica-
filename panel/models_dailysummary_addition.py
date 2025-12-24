# Helper: this file contains the DailyEqctacliSummary model to be merged into panel/models.py
from django.db import models

class DailyEqctacliSummary(models.Model):
    date = models.DateField(unique=True)
    num_atenciones = models.IntegerField(default=0)
    total_consulta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_medicina = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    num_citas = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_eqctacli_summary'
        verbose_name = 'Resumen diario Eqctacli'
        verbose_name_plural = 'Resúmenes diarios Eqctacli'