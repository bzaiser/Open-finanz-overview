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
    
    # Design & Colors (Explicit overrides)
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
    primary_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Primary Color"),
        required=False,
    )
    secondary_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Secondary Color"),
        required=False,
    )
    background_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Background Color"),
        required=False,
    )
    text_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Text Color"),
        required=False,
    )
    sidebar_bg_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Sidebar Background"),
        required=False,
    )
    table_header_bg_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Table Header BG"),
        required=False,
    )
    table_header_text_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Table Header Text"),
        required=False,
    )
    table_filter_bg_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Table Filter BG"),
        required=False,
    )
    table_body_bg_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Table Body BG"),
        required=False,
    )
    table_body_text_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Table Body Text"),
        required=False,
    )
    table_border_color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        label=_("Table Border"),
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = [
            'avatar', 'birth_date', 'language', 'currency', 'simulation_max_age',
            'inflation_rate', 'salary_increase', 'pension_increase', 'investment_return_offset',
            'gradient_start', 'gradient_end', 'primary_color', 'secondary_color',
            'background_color', 'text_color', 'sidebar_bg_color',
            'table_header_bg_color', 'table_header_text_color', 'table_filter_bg_color',
            'table_body_bg_color', 'table_body_text_color', 'table_border_color'
        ]
