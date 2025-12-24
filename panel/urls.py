from django.urls import path
from . import views

app_name = "panel"

urlpatterns = [
    # Ruta principal (Index)
    path("", views.index, name="index"),

    # Gestión de Usuarios
    path("usuarios/", views.UserListView.as_view(), name="users_list"),
    path("usuarios/nuevo/", views.UserCreateView.as_view(), name="users_add"),
    path("usuarios/<int:pk>/editar/", views.UserUpdateView.as_view(), name="users_edit"),
    path("usuarios/<int:pk>/eliminar/", views.UserDeleteView.as_view(), name="users_delete"),

    # Importación de Atenciones
    path("atenciones/import/", views.import_atenciones, name="import_atenciones"),

    # Ruta de Pacientes (la que agregamos recién)
    path('pacientes/', views.lista_pacientes, name='lista_pacientes'),

    # Importar desde Access (superusers)
    path('import/access/', views.import_access, name='import_access'),
    # Exportar archivo Access persistente
    path('export/access/', views.export_access, name='export_access'),
    # Ejecutar consultas SELECT contra el Access (superusers)
    path('access/queries/', views.access_queries, name='access_queries'),
    # Manual trigger para importar desde el archivo Access persistente
    path('import/access/run/', views.run_import_access, name='run_import_access'),
    # Documentación del proyecto (reporte de pasantías)
    path('docs/report/', views.report_view, name='report'),

    # Dashboard y API para agregados
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/dashboard/', views.dashboard_api, name='dashboard_api'),
    path('api/dashboard/export_csv/', views.dashboard_export_csv, name='dashboard_export_csv'),
    path('api/dashboard/export_xlsx/', views.dashboard_export_xlsx, name='dashboard_export_xlsx'),
    path('api/dashboard/export_pdf/', views.dashboard_export_pdf, name='dashboard_export_pdf'),
]