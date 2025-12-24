from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
from datetime import datetime, date
from decimal import Decimal
from panel.models import PanelAtencion, DailyEqctacliSummary

class Command(BaseCommand):
    help = 'Calcula y actualiza los resúmenes diarios (DailyEqctacliSummary) a partir de panel_atencion'

    def add_arguments(self, parser):
        parser.add_argument('--date', help='Fecha única YYYY-MM-DD')
        parser.add_argument('--from', dest='from_date', help='Fecha inicio YYYY-MM-DD')
        parser.add_argument('--to', dest='to_date', help='Fecha fin YYYY-MM-DD')

    def handle(self, *args, **options):
        # Determine date range
        if options.get('date'):
            try:
                d = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except Exception as e:
                self.stderr.write('Fecha inválida: %s' % e)
                return
            dates = [d]
        else:
            f = options.get('from_date')
            t = options.get('to_date')
            if f and t:
                try:
                    fdate = datetime.strptime(f, '%Y-%m-%d').date()
                    tdate = datetime.strptime(t, '%Y-%m-%d').date()
                except Exception as e:
                    self.stderr.write('Fechas inválidas: %s' % e)
                    return
                q = PanelAtencion.objects.filter(fecha__range=(fdate, tdate)).values_list('fecha', flat=True).distinct()
                dates = sorted(list(set(q)))
            else:
                # default: last 7 days
                today = date.today()
                q = PanelAtencion.objects.filter(fecha__range=(today.replace(day=1), today)).values_list('fecha', flat=True).distinct()
                dates = sorted(list(set(q)))

        if not dates:
            self.stdout.write('No hay fechas para procesar')
            return

        for d in dates:
            qs = PanelAtencion.objects.filter(fecha=d)
            agg = qs.aggregate(
                total_consulta=Sum('valor_consulta'),
                total_medicina=Sum('valor_medicinas'),
                num_atenciones=Count('id')
            )
            total_consulta = agg['total_consulta'] or Decimal('0')
            total_medicina = agg['total_medicina'] or Decimal('0')
            num_atenciones = agg['num_atenciones'] or 0

            # compute num_citas by checking raw.F_Cita presence matching date
            num_citas = 0
            for row in qs:
                raw = row.raw or {}
                fc = raw.get('F_Cita') or raw.get('F_cita') or raw.get('F_CITA') or raw.get('F_Cita ')
                if fc:
                    try:
                        # try common formats
                        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S'):
                            try:
                                parsed = datetime.strptime(str(fc), fmt).date()
                                break
                            except Exception:
                                parsed = None
                                continue
                        if parsed and parsed == d:
                            num_citas += 1
                    except Exception:
                        continue

            DailyEqctacliSummary.objects.update_or_create(
                date=d,
                defaults={
                    'num_atenciones': num_atenciones,
                    'total_consulta': total_consulta,
                    'total_medicina': total_medicina,
                    'num_citas': num_citas,
                }
            )
            self.stdout.write(self.style.SUCCESS(f'Updated summary for {d}: atenciones={num_atenciones} consultas={total_consulta} medicinas={total_medicina} citas={num_citas}'))
