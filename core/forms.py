from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, UserProfile
from django.utils.translation import gettext_lazy as _

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class UserProfileForm(forms.ModelForm):
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=False,
        label=_("Birth Date")
    )
    gradient_start = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Gradient Start Color"),
        required=False,
    )
    gradient_end = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Gradient End Color"),
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = [
            'avatar', 'birth_date', 'language', 'currency', 'simulation_max_age', 'theme',
            'inflation_rate', 'salary_increase', 'pension_increase', 'investment_return_offset',
            'gradient_start', 'gradient_end',
        ]
