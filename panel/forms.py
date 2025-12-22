from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active", "is_staff"]


class SuperuserAuthenticationForm(AuthenticationForm):
    """AuthenticationForm that allows only active superusers to log in."""
    def confirm_login_allowed(self, user):
        # Keep default active check
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise forms.ValidationError(
                "Solo los superusuarios pueden iniciar sesión en esta aplicación.",
                code='invalid_login',
            )
