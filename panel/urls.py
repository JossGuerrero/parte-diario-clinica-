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
]