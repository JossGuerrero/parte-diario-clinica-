from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView, LoginView

# use custom auth form that only allows superusers
from panel.forms import SuperuserAuthenticationForm

urlpatterns = [
    path("admin/", admin.site.urls),
    # login / logout (restrict login to superusers via authentication_form)
    path(
        "login/",
        LoginView.as_view(
            template_name='registration/login.html',
            authentication_form=SuperuserAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(next_page=__import__('django.urls').urls.reverse_lazy('login')), name="logout"),
    # incluir panel con namespace 'panel'
    path("", include(("panel.urls", "panel"), namespace="panel")),
]

