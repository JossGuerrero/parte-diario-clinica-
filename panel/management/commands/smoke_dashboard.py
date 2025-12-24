from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Run smoke checks against dashboard endpoints (JSON, CSV, XLSX, PDF)'

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(username='smoke_monitor')
        if created:
            user.set_password('smoke_monitor')
            user.is_staff = True
            user.save()

        c = Client()
        c.force_login(user)

        endpoints = [
            ('JSON', '/panel/api/dashboard/?desde=2025-12-01&hasta=2025-12-23'),
            ('CSV', '/panel/api/dashboard/export_csv/?desde=2025-12-01&hasta=2025-12-23'),
            ('XLSX', '/panel/api/dashboard/export_xlsx/?desde=2025-12-01&hasta=2025-12-23'),
            ('PDF', '/panel/api/dashboard/export_pdf/?desde=2025-12-01&hasta=2025-12-23'),
        ]

        failed = False
        for name, url in endpoints:
            res = c.get(url)
            if res.status_code != 200:
                self.stdout.write(self.style.ERROR(f'{name} check FAILED: {url} -> {res.status_code}'))
                failed = True
            else:
                self.stdout.write(self.style.SUCCESS(f'{name} OK: {url} -> {res.status_code}'))

        if failed:
            raise SystemExit(2)
