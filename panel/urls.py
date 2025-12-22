from django.urls import path
from . import views

app_name = "panel"

urlpatterns = [
    path("", views.index, name="index"),

    # User management
    path("usuarios/", views.UserListView.as_view(), name="users_list"),
    path("usuarios/nuevo/", views.UserCreateView.as_view(), name="users_add"),
    path("usuarios/<int:pk>/editar/", views.UserUpdateView.as_view(), name="users_edit"),
    path("usuarios/<int:pk>/eliminar/", views.UserDeleteView.as_view(), name="users_delete"),

    # Import atenciones (CSV)
    path("atenciones/import/", views.import_atenciones, name="import_atenciones"),
]