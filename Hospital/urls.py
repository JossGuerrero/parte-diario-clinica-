from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView, LoginView
from django.urls import reverse_lazy
# use custom auth form that only allows superusers
from panel.forms import SuperuserAuthenticationForm

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
    path("logout/", LogoutView.as_view(next_page=reverse_lazy('login')), name="logout"),

    path("", include(("panel.urls", "panel"), namespace="panel")),
]