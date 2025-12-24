from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0007_merge_20251223_1630'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyEqctacliSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('num_atenciones', models.IntegerField(default=0)),
                ('total_consulta', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_medicina', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('num_citas', models.IntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'daily_eqctacli_summary',
                'verbose_name': 'Resumen diario Eqctacli',
                'verbose_name_plural': 'Resúmenes diarios Eqctacli',
            },
        ),
    ]
