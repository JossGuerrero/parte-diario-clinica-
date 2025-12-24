from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.shortcuts import redirect
# use custom auth form that only allows superusers
from panel.forms import SuperuserAuthenticationForm
# use our small logout view that accepts GET so the sidebar link works
from panel.views import logout_view

from django.conf import settings
from django.conf.urls.static import static

# Root should show the login page so the app 'empiece' por autenticación
def root_redirect(request):
    return redirect('login')

urlpatterns = [
    # 1. Administración de Django
    path("admin/", admin.site.urls),

    # 2. Login / Logout (Restringido a superusuarios)
    path(
        "login/",
        LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=SuperuserAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", logout_view, name="logout"),

    # Root -> login
    path("", root_redirect, name="home"),

    # Mover el panel bajo /panel/ para evitar ambigüedades con la ruta raíz
    path("panel/", include(("panel.urls", "panel"), namespace="panel")),

    # Endpoints del dashboard para gráficos (Access en tiempo real)
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
]

# Servir archivos media en DEBUG para desarrollo local
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
