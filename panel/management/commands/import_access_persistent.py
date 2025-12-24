import os
import hashlib
import json
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from panel.models import PanelAtencion, PanelEspecialidad, PanelServicio
from panel.access_importer import import_from_access, DEFAULT_TABLES

class Command(BaseCommand):
    help = 'Importa filas desde el Access persistente (MEDIA/access/clinic.*) hacia panel_atencion (idempotente)'

    def add_arguments(self, parser):
        parser.add_argument('--file', help='Ruta al archivo Access (por defecto MEDIA/access/clinic.accdb)')
        parser.add_argument('--pwd', help='Contraseña del Access (si aplica)')
        parser.add_argument('--tables', help='Tablas a importar separadas por comas', default=','.join(DEFAULT_TABLES))

    def handle(self, *args, **options):
        file_path = options.get('file')
        pwd = options.get('pwd') or os.environ.get('ACCESS_PERSISTENT_PWD') or getattr(settings, 'ACCESS_PERSISTENT_PWD', '')
        tables = [t.strip() for t in options.get('tables', '').split(',') if t.strip()]

        if not file_path:
            media_access = os.path.join(settings.MEDIA_ROOT, 'access')
            # try common names
            for name in ('clinic.accdb', 'clinic.mdb'):
                p = os.path.join(media_access, name)
                if os.path.exists(p):
                    file_path = p
                    break
            if not file_path:
                self.stderr.write('No se encontró archivo persistente en MEDIA/access. Usa --file para indicar ruta.')
                return

        self.stdout.write(f'Usando archivo: {file_path} (tablas: {tables})')

        summary = import_from_access(file_path, pwd=pwd, tables=tables)
        if summary['errors']:
            for table, err in summary['errors']:
                self.stderr.write(f'Error en tabla {table}: {err}')
        for table, cnt in summary['details'].items():
            self.stdout.write(self.style.SUCCESS(f'Importadas {cnt} filas de {table}'))
        self.stdout.write(self.style.SUCCESS(f"Importación completa. Total importadas: {summary['imported']}"))
