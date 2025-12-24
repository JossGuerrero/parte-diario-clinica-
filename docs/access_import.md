Automatización de importación desde Access

Resumen
- Se creó un comando Django `python manage.py import_access_persistent` que importa de forma idempotente las tablas: Eqtrasec, Ctacli, Eqctavdd desde el archivo persistente en `MEDIA_ROOT/access/clinic.accdb` (o `clinic.mdb`).

Cómo configurar
1. Coloca el archivo Access en `MEDIA_ROOT/access/clinic.accdb` (o `clinic.mdb`).
2. Si el archivo está protegido por contraseña, exporta la contraseña a la variable de entorno `ACCESS_PERSISTENT_PWD` o pásala con `--pwd` al comando.

Comando de ejemplo

    python manage.py import_access_persistent --tables Eqtrasec,Ctacli,Eqctavdd

Ejecución automática
- En Linux/macOS: crea una entrada cron que ejecute el comando periódicamente.
- En Windows: usa el Task Scheduler para ejecutar `python manage.py import_access_persistent` a intervalos regulares.

Nota sobre bloqueos
- Si el archivo .accdb está abierto en Microsoft Access u otra aplicación, puede producirse "database is locked". Cierra cualquier aplicación que tenga abierto el archivo antes de la importación o programa la tarea en un horario donde el archivo no está en uso.

Vista manual
- En la UI de Import Access hay un botón para ejecutar la importación persistente manualmente (solo superusers).

Seguridad
- La importación es accesible solo para superusers.
- La contraseña no se guarda en claro en la base de datos; para la ejecución automatizada se recomienda usar variables de entorno del sistema.
