from django.core.management.base import BaseCommand
from django.test import Client
from django.conf import settings
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Export daily eqctacli reports (CSV, XLSX, PDF) to reports/ directory'

    def add_arguments(self, parser):
        parser.add_argument('--desde', type=str, help='YYYY-MM-DD start date')
        parser.add_argument('--hasta', type=str, help='YYYY-MM-DD end date')

    def handle(self, *args, **options):
        desde = options.get('desde')
        hasta = options.get('hasta')
        if not desde:
            # default to today's date
            desde = datetime.today().strftime('%Y-%m-%d')
        if not hasta:
            hasta = desde

        User = settings.AUTH_USER_MODEL
        # create a client and authenticate as a monitor user
        c = Client()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, created = User.objects.get_or_create(username='report_generator')
        if created:
            user.set_password('report_generator')
            user.is_staff = True
            user.save()
        c.force_login(user)

        report_dir = os.path.join(settings.BASE_DIR, 'reports')
        os.makedirs(report_dir, exist_ok=True)

        base_name = f"eqctacli_{desde}_to_{hasta}"

        endpoints = [
            ('csv', f'/panel/api/dashboard/export_csv/?desde={desde}&hasta={hasta}'),
            ('xlsx', f'/panel/api/dashboard/export_xlsx/?desde={desde}&hasta={hasta}'),
            ('pdf', f'/panel/api/dashboard/export_pdf/?desde={desde}&hasta={hasta}'),
        ]

        for ext, url in endpoints:
            resp = c.get(url)
            if resp.status_code != 200:
                self.stdout.write(self.style.ERROR(f'Failed to fetch {url}: {resp.status_code}'))
                continue
            filename = os.path.join(report_dir, f"{base_name}.{ext}")
            with open(filename, 'wb') as f:
                f.write(resp.content)
            self.stdout.write(self.style.SUCCESS(f'Wrote {filename}'))
