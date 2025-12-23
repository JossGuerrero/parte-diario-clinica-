# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models

class Apoyodiagnostico(models.Model):
    identificacion = models.CharField(db_column='Identificacion', max_length=13)  # Field name made lowercase.
    tipodiagnostico = models.CharField(db_column='TipoDiagnostico', max_length=50)  # Field name made lowercase.
    nombreexamen = models.CharField(db_column='NombreExamen', max_length=50)  # Field name made lowercase.
    ruta = models.CharField(db_column='Ruta', max_length=200)  # Field name made lowercase.
    fechaexamen = models.DateTimeField(db_column='FechaExamen')  # Field name made lowercase.
    origen = models.CharField(db_column='Origen', max_length=50)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ApoyoDiagnostico'


class Cita(models.Model):
    idcita = models.AutoField(db_column='idCita', primary_key=True)  # Field name made lowercase.
    idespecialidad = models.ForeignKey('Especialidad', models.DO_NOTHING, db_column='idEspecialidad')  # Field name made lowercase.
    idprofesional = models.ForeignKey('Profesional', models.DO_NOTHING, db_column='idProfesional')  # Field name made lowercase.
    fechacita = models.DateField(db_column='fechaCita')  # Field name made lowercase.
    horainicio = models.DateTimeField(db_column='HoraInicio')  # Field name made lowercase.
    horafin = models.DateTimeField(db_column='HoraFin')  # Field name made lowercase.
    idhorario = models.ForeignKey('Horario', models.DO_NOTHING, db_column='idHorario')  # Field name made lowercase.
    idestadocita = models.ForeignKey('Estadocita', models.DO_NOTHING, db_column='idEstadoCita')  # Field name made lowercase.
    idpaciente = models.ForeignKey('Paciente', models.DO_NOTHING, db_column='idPaciente', blank=True, null=True)  # Field name made lowercase.
    idcitatipo = models.ForeignKey('Citatipo', models.DO_NOTHING, db_column='idCitaTipo', blank=True, null=True)  # Field name made lowercase.
    idconvenio = models.ForeignKey('Convenio', models.DO_NOTHING, db_column='idConvenio', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField()
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion')  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Cita'

    def __str__(self):
        return f"Cita #{self.idcita} | Fecha: {self.fechacita} | Paciente ID: {self.idpaciente_id}"

class Meta:
        managed = False
        db_table = 'cita' # O el nombre que tenga en tu SQL Server
        verbose_name_plural = "Citas"

class Citaproceso(models.Model):
    idcita = models.IntegerField(db_column='idCita')  # Field name made lowercase.
    idestadocita = models.IntegerField(db_column='idEstadoCita')  # Field name made lowercase.
    idpaciente = models.IntegerField(db_column='idPaciente')  # Field name made lowercase.
    idcitatipo = models.IntegerField(db_column='idCitaTipo')  # Field name made lowercase.
    idconvenio = models.IntegerField(db_column='idConvenio')  # Field name made lowercase.
    observacion = models.CharField(db_column='Observacion', max_length=100, blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'CitaProceso'


class Citatipo(models.Model):
    idcitatipo = models.AutoField(db_column='idCitaTipo', primary_key=True)  # Field name made lowercase.
    orden = models.IntegerField()
    codigo = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=30)
    estado = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = 'CitaTipo'


class Citatipoespecialidad(models.Model):
    idcitatipo = models.ForeignKey(Citatipo, models.DO_NOTHING, db_column='idCitaTipo')  # Field name made lowercase.
    idespecialidad = models.ForeignKey('Especialidad', models.DO_NOTHING, db_column='idEspecialidad')  # Field name made lowercase.
    nocitas = models.IntegerField(db_column='noCitas')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'CitaTipoEspecialidad'


class Pacienteagenda(models.Model):
    idpaciente = models.AutoField(db_column='idPaciente', primary_key=True)  # Field name made lowercase.
    idusuario = models.IntegerField(db_column='idUsuario', blank=True, null=True)  # Field name made lowercase.
    nombres = models.CharField(db_column='Nombres', max_length=60)  # Field name made lowercase.
    apellidos = models.CharField(db_column='Apellidos', max_length=60)  # Field name made lowercase.
    fechanacimiento = models.DateField(db_column='FechaNacimiento')  # Field name made lowercase.
    cedula = models.CharField(db_column='Cedula', unique=True, max_length=13)  # Field name made lowercase.
    genero = models.SmallIntegerField(db_column='Genero')  # Field name made lowercase.
    correo = models.CharField(db_column='Correo', max_length=80, blank=True, null=True)  # Field name made lowercase.
    activo = models.BooleanField(db_column='Activo')  # Field name made lowercase.
    fechacrea = models.DateTimeField(db_column='FechaCrea')  # Field name made lowercase.
    usuariocrea = models.CharField(db_column='UsuarioCrea', max_length=60)  # Field name made lowercase.
    fechamodifica = models.DateTimeField(db_column='FechaModifica')  # Field name made lowercase.
    usuariomodifica = models.CharField(db_column='UsuarioModifica', max_length=60)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'PacienteAgenda'


class Rol(models.Model):
    idrol = models.AutoField(db_column='idRol', primary_key=True)  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=20)  # Field name made lowercase.
    orden = models.IntegerField(db_column='Orden')  # Field name made lowercase.
    activo = models.BooleanField(db_column='Activo')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Rol'


class Usuario(models.Model):
    idusuario = models.AutoField(db_column='idUsuario', primary_key=True)  # Field name made lowercase.
    nombres = models.CharField(db_column='Nombres', max_length=60, blank=True, null=True)  # Field name made lowercase.
    apellidos = models.CharField(db_column='Apellidos', max_length=60, blank=True, null=True)  # Field name made lowercase.
    login = models.CharField(db_column='Login', max_length=60)  # Field name made lowercase.
    contrasenia = models.CharField(db_column='Contrasenia', max_length=60)  # Field name made lowercase.
    cedula = models.CharField(db_column='Cedula', unique=True, max_length=13)  # Field name made lowercase.
    correo = models.CharField(db_column='Correo', max_length=80)  # Field name made lowercase.
    activo = models.BooleanField(db_column='Activo')  # Field name made lowercase.
    idrol = models.ForeignKey(Rol, models.DO_NOTHING, db_column='idRol', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Usuario'


class Atencionambulatoria(models.Model):
    idatencionambulatoria = models.AutoField(db_column='idAtencionAmbulatoria', primary_key=True)  # Field name made lowercase.
    idordenatencion = models.ForeignKey('Ordenatencion', models.DO_NOTHING, db_column='idOrdenAtencion', blank=True, null=True)  # Field name made lowercase.
    idtriage = models.ForeignKey('Triage', models.DO_NOTHING, db_column='idTriage', blank=True, null=True)  # Field name made lowercase.
    idespecialidad = models.ForeignKey('Especialidad', models.DO_NOTHING, db_column='idEspecialidad', blank=True, null=True)  # Field name made lowercase.
    idprofesional = models.ForeignKey('Profesional', models.DO_NOTHING, db_column='idProfesional', blank=True, null=True)  # Field name made lowercase.
    fechaatencion = models.DateTimeField(db_column='fechaAtencion', blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = 'atencionAmbulatoria'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class Convenio(models.Model):
    idconvenio = models.AutoField(db_column='idConvenio', primary_key=True)  # Field name made lowercase.
    codigo = models.CharField(max_length=10, blank=True, null=True)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    fechainicio = models.DateField(db_column='fechaInicio', blank=True, null=True)  # Field name made lowercase.
    fechafin = models.DateField(db_column='fechaFin', blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'convenio'


class Convenioespecialidad(models.Model):
    idconvenioespecialidad = models.AutoField(db_column='idConvenioEspecialidad', primary_key=True)  # Field name made lowercase.
    idconvenio = models.ForeignKey(Convenio, models.DO_NOTHING, db_column='idConvenio', blank=True, null=True)  # Field name made lowercase.
    idespecialidad = models.ForeignKey('Especialidad', models.DO_NOTHING, db_column='idEspecialidad', blank=True, null=True)  # Field name made lowercase.
    codigo = models.CharField(max_length=20, blank=True, null=True)
    descripcion = models.CharField(max_length=300, blank=True, null=True)
    fechainicio = models.DateField(db_column='fechaInicio', blank=True, null=True)  # Field name made lowercase.
    fechafin = models.DateField(db_column='fechaFin', blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'convenioEspecialidad'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class Documento(models.Model):
    iddocumento = models.AutoField(db_column='idDocumento', primary_key=True)  # Field name made lowercase.
    codigo = models.CharField(max_length=20, blank=True, null=True)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'documento'


class Documentoconvenio(models.Model):
    iddocumentoconvenio = models.AutoField(db_column='idDocumentoConvenio', primary_key=True)  # Field name made lowercase.
    idconvenio = models.ForeignKey(Convenio, models.DO_NOTHING, db_column='idConvenio', blank=True, null=True)  # Field name made lowercase.
    idservicio = models.ForeignKey('Servicio', models.DO_NOTHING, db_column='idServicio', blank=True, null=True)  # Field name made lowercase.
    iddocumento = models.ForeignKey(Documento, models.DO_NOTHING, db_column='idDocumento', blank=True, null=True)  # Field name made lowercase.
    fechainicio = models.DateField(db_column='fechaInicio', blank=True, null=True)  # Field name made lowercase.
    fechafin = models.DateField(db_column='fechaFin', blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'documentoConvenio'


class Especialidad(models.Model):
    idespecialidad = models.AutoField(db_column='idEspecialidad', primary_key=True)  # Field name made lowercase.
    codigo = models.CharField(max_length=20, blank=True, null=True)
    descripcion = models.CharField(max_length=50, blank=True, null=True)
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'especialidad'


class Estadocita(models.Model):
    idestadocita = models.AutoField(db_column='idEstadoCita', primary_key=True)  # Field name made lowercase.
    orden = models.SmallIntegerField(db_column='Orden')  # Field name made lowercase.
    codigo = models.CharField(db_column='Codigo', max_length=50, blank=True, null=True)  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=50, blank=True, null=True)  # Field name made lowercase.
    estado = models.IntegerField(db_column='Estado')  # Field name made lowercase.
    idestadopadre = models.IntegerField(db_column='idEstadoPadre', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'estadoCita'


class Horario(models.Model):
    idhorario = models.AutoField(db_column='idHorario', primary_key=True)  # Field name made lowercase.
    idprofesional = models.ForeignKey('Profesional', models.DO_NOTHING, db_column='idProfesional', blank=True, null=True)  # Field name made lowercase.
    diasemana = models.IntegerField(db_column='diaSemana')  # Field name made lowercase.
    h1inicio = models.DateTimeField(db_column='h1Inicio')  # Field name made lowercase.
    h1fin = models.DateTimeField(db_column='h1Fin')  # Field name made lowercase.
    h2inicio = models.DateTimeField(db_column='h2Inicio')  # Field name made lowercase.
    h2fin = models.DateTimeField(db_column='h2Fin')  # Field name made lowercase.
    estado = models.IntegerField()
    tiempo = models.IntegerField(blank=True, null=True)
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion')  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'horario'


class Ordenatencion(models.Model):
    idordenatencion = models.AutoField(db_column='idOrdenAtencion', primary_key=True)  # Field name made lowercase.
    idpaciente = models.ForeignKey('Paciente', models.DO_NOTHING, db_column='idPaciente', blank=True, null=True)  # Field name made lowercase.
    idconvenio = models.ForeignKey(Convenio, models.DO_NOTHING, db_column='idConvenio', blank=True, null=True)  # Field name made lowercase.
    idservicio = models.ForeignKey('Servicio', models.DO_NOTHING, db_column='idServicio', blank=True, null=True)  # Field name made lowercase.
    fechainicio = models.DateField(db_column='fechaInicio', blank=True, null=True)  # Field name made lowercase.
    fechafin = models.DateField(db_column='fechaFin', blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordenAtencion'


class Ordenatenciondocumento(models.Model):
    idordenatenciondocumento = models.AutoField(db_column='idOrdenAtencionDocumento', primary_key=True)  # Field name made lowercase.
    idordenatencion = models.ForeignKey(Ordenatencion, models.DO_NOTHING, db_column='idOrdenAtencion', blank=True, null=True)  # Field name made lowercase.
    iddocumento = models.ForeignKey(Documento, models.DO_NOTHING, db_column='idDocumento', blank=True, null=True)  # Field name made lowercase.
    path = models.CharField(max_length=2000, blank=True, null=True)
    fechainicio = models.DateField(db_column='fechaInicio', blank=True, null=True)  # Field name made lowercase.
    fechafin = models.DateField(db_column='fechaFin', blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ordenAtencionDocumento'


class Paciente(models.Model):
    idpaciente = models.AutoField(db_column='idPaciente', primary_key=True)  # Field name made lowercase.
    identificacion = models.CharField(max_length=18, blank=True, null=True)
    tipoidentificacion = models.CharField(db_column='tipoIdentificacion', max_length=18, blank=True, null=True)  # Field name made lowercase.
    nombrepaciente = models.CharField(db_column='nombrePaciente', max_length=200, blank=True, null=True)  # Field name made lowercase.
    apellidopaterno = models.CharField(db_column='apellidoPaterno', max_length=50, blank=True, null=True)  # Field name made lowercase.
    apellidomaterno = models.CharField(db_column='apellidoMaterno', max_length=50, blank=True, null=True)  # Field name made lowercase.
    nombre1 = models.CharField(max_length=60, blank=True, null=True)
    nombre2 = models.CharField(max_length=60, blank=True, null=True)
    observacion = models.CharField(max_length=300, blank=True, null=True)
    direccion = models.CharField(max_length=150, blank=True, null=True)
    telefonoconvencional = models.CharField(db_column='telefonoConvencional', max_length=30, blank=True, null=True)  # Field name made lowercase.
    telefonocelular = models.CharField(db_column='telefonoCelular', max_length=30, blank=True, null=True)  # Field name made lowercase.
    estadoregistro = models.SmallIntegerField(db_column='estadoRegistro', blank=True, null=True)  # Field name made lowercase.
    ciudad = models.CharField(max_length=30, blank=True, null=True)
    email = models.CharField(max_length=50, blank=True, null=True)
    historiaclinica = models.CharField(db_column='historiaClinica', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechanacimiento = models.DateField(db_column='fechaNacimiento', blank=True, null=True)  # Field name made lowercase.
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    rutaimagen = models.CharField(db_column='rutaImagen', max_length=200, blank=True, null=True)  # Field name made lowercase.
    provincia = models.CharField(max_length=20, blank=True, null=True)
    canton = models.CharField(max_length=20, blank=True, null=True)
    parroquia = models.CharField(max_length=20, blank=True, null=True)
    barrio = models.CharField(max_length=20, blank=True, null=True)
    zona = models.CharField(max_length=3, blank=True, null=True)
    lugarnacimiento = models.CharField(db_column='lugarNacimiento', max_length=25, blank=True, null=True)  # Field name made lowercase.
    nacionalidad = models.CharField(max_length=20, blank=True, null=True)
    grupocultural = models.CharField(db_column='grupoCultural', max_length=15, blank=True, null=True)  # Field name made lowercase.
    genero = models.CharField(max_length=3, blank=True, null=True)
    estadocivil = models.CharField(db_column='estadoCivil', max_length=10, blank=True, null=True)  # Field name made lowercase.
    origencontacto = models.CharField(db_column='origenContacto', max_length=50)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'paciente'


class Pacientecontacto(models.Model):
    idpacientecontacto = models.AutoField(db_column='idPacienteContacto', primary_key=True)  # Field name made lowercase.
    idpaciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='idPaciente')  # Field name made lowercase.
    nombre = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=13, blank=True, null=True)
    email = models.CharField(max_length=25, blank=True, null=True)
    parentesco = models.CharField(max_length=15, blank=True, null=True)
    observacion = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pacienteContacto'


class Pacientedetalle(models.Model):
    idpacientedetalle = models.AutoField(db_column='idPacienteDetalle', primary_key=True)  # Field name made lowercase.
    idpaciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='idPaciente', blank=True, null=True)  # Field name made lowercase.
    discapacidad = models.SmallIntegerField(blank=True, null=True)
    tipodiscapacidad = models.CharField(db_column='tipoDiscapacidad', max_length=50, blank=True, null=True)  # Field name made lowercase.
    identificaciondiscapacidad = models.CharField(db_column='identificacionDiscapacidad', max_length=15, blank=True, null=True)  # Field name made lowercase.
    porcentajediscapacidad = models.SmallIntegerField(db_column='porcentajeDiscapacidad', blank=True, null=True)  # Field name made lowercase.
    otroseguro = models.SmallIntegerField(db_column='otroSeguro', blank=True, null=True)  # Field name made lowercase.
    descripcionotroseguro = models.CharField(db_column='descripcionOtroSeguro', max_length=15, blank=True, null=True)  # Field name made lowercase.
    nivelinstruccion = models.CharField(db_column='nivelInstruccion', max_length=20, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'pacienteDetalle'


class Pacientediagnostico(models.Model):
    idpacientediagnostico = models.AutoField(db_column='idPacienteDiagnostico', primary_key=True)  # Field name made lowercase.
    idpaciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='idPaciente', blank=True, null=True)  # Field name made lowercase.
    idcie10 = models.IntegerField(db_column='idCie10', blank=True, null=True)  # Field name made lowercase.
    fechainicio = models.DateField(db_column='fechaInicio', blank=True, null=True)  # Field name made lowercase.
    fechafin = models.DateField(db_column='fechaFin', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'pacienteDiagnostico'


class Pacientefacturacion(models.Model):
    idpacientefacturacion = models.AutoField(db_column='idPacienteFacturacion', primary_key=True)  # Field name made lowercase.
    idpaciente = models.ForeignKey(Paciente, models.DO_NOTHING, db_column='idPaciente')  # Field name made lowercase.
    identificacion = models.CharField(max_length=18, blank=True, null=True)
    tipoidentificacion = models.CharField(db_column='tipoIdentificacion', max_length=18, blank=True, null=True)  # Field name made lowercase.
    nombre = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=13, blank=True, null=True)
    email = models.CharField(max_length=25, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pacienteFacturacion'


class PanelAtencion(models.Model):
    id = models.BigAutoField(primary_key=True)
    fecha = models.DateField()
    valor_consulta = models.DecimalField(max_digits=10, decimal_places=2)
    valor_medicinas = models.DecimalField(max_digits=10, decimal_places=2)
    especialidad = models.ForeignKey('PanelEspecialidad', models.DO_NOTHING)
    servicio = models.ForeignKey('PanelServicio', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'panel_atencion'


class PanelCita(models.Model):
    id = models.BigAutoField(primary_key=True)
    fecha = models.DateField()
    estado = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'panel_cita'


class PanelEspecialidad(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = 'panel_especialidad'


class PanelServicio(models.Model):
    id = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = 'panel_servicio'


class Profesional(models.Model):
    idprofesional = models.AutoField(db_column='idProfesional', primary_key=True)  # Field name made lowercase.
    idespecialidad = models.ForeignKey(Especialidad, models.DO_NOTHING, db_column='idEspecialidad', blank=True, null=True)  # Field name made lowercase.
    nombres = models.CharField(max_length=50, blank=True, null=True)
    apellidos = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.CharField(max_length=50, blank=True, null=True)
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'profesional'


class Servicio(models.Model):
    idservicio = models.AutoField(db_column='idServicio', primary_key=True)  # Field name made lowercase.
    codigo = models.CharField(max_length=10, blank=True, null=True)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'servicio'


class Sysdiagrams(models.Model):
    name = models.CharField(max_length=128)
    principal_id = models.IntegerField()
    diagram_id = models.AutoField(primary_key=True)
    version = models.IntegerField(blank=True, null=True)
    definition = models.BinaryField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sysdiagrams'
        unique_together = (('principal_id', 'name'),)


class Ticketparqueadero(models.Model):
    idticket = models.AutoField(db_column='idTicket', primary_key=True)  # Field name made lowercase.
    noticket = models.CharField(db_column='NoTicket', max_length=10, blank=True, null=True)  # Field name made lowercase.
    placa = models.CharField(db_column='Placa', max_length=10, blank=True, null=True)  # Field name made lowercase.
    horaingreso = models.DateTimeField(db_column='HoraIngreso', blank=True, null=True)  # Field name made lowercase.
    horasalida = models.DateTimeField(db_column='HoraSalida', blank=True, null=True)  # Field name made lowercase.
    valor = models.DecimalField(db_column='Valor', max_digits=19, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    autorizado = models.DecimalField(db_column='Autorizado', max_digits=19, decimal_places=4, blank=True, null=True)  # Field name made lowercase.
    observacion = models.CharField(db_column='Observacion', max_length=50, blank=True, null=True)  # Field name made lowercase.
    idusuariocreacion = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='idUsuarioCreacion', blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='FechaCreacion', blank=True, null=True)  # Field name made lowercase.
    idusuariomodificacion = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='idUsuarioModificacion', related_name='ticketparqueadero_idusuariomodificacion_set', blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='FechaModificacion', blank=True, null=True)  # Field name made lowercase.
    activo = models.BooleanField(db_column='Activo', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'ticketParqueadero'


class Triage(models.Model):
    idtriage = models.AutoField(db_column='idTriage', primary_key=True)  # Field name made lowercase.
    codigo = models.CharField(max_length=20, blank=True, null=True)
    descripcion = models.CharField(max_length=300, blank=True, null=True)
    usuariocreacion = models.CharField(db_column='usuarioCreacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechacreacion = models.DateTimeField(db_column='fechaCreacion', blank=True, null=True)  # Field name made lowercase.
    usuariomodificacion = models.CharField(db_column='usuarioModificacion', max_length=20, blank=True, null=True)  # Field name made lowercase.
    fechamodificacion = models.DateTimeField(db_column='fechaModificacion', blank=True, null=True)  # Field name made lowercase.
    estado = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'triage'
