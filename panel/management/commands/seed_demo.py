# Disabled seed command - removed to avoid accidental population of demo data.
# If you need demo data for development, re-create this file from version control or run migrations and add data manually.

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Seed command disabled by request.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('seed_demo is disabled. Recreate if needed.'))