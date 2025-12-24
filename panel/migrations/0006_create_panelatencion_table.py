from django.db import migrations

CREATE_SQL = '''
CREATE TABLE IF NOT EXISTS panel_atencion (
    id integer PRIMARY KEY AUTOINCREMENT,
    fecha date NOT NULL,
    valor_consulta numeric(10,2) NOT NULL DEFAULT 0,
    valor_medicinas numeric(10,2) NOT NULL DEFAULT 0,
    especialidad_id integer,
    servicio_id integer,
    source_table varchar(100),
    source_hash varchar(64),
    raw text,
    institucion varchar(120),
    genero varchar(10),
    edad integer,
    solicitado_a varchar(120)
);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_source_row ON panel_atencion (source_table, source_hash) WHERE source_table IS NOT NULL AND source_hash IS NOT NULL;
'''

DROP_SQL = """
DROP INDEX IF EXISTS uniq_source_row;
DROP TABLE IF EXISTS panel_atencion;
"""

class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0004_add_accessquery'),
    ]

    operations = [
        migrations.RunSQL(CREATE_SQL, DROP_SQL),
    ]
