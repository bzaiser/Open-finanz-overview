from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, UserProfile
from django.utils.translation import gettext_lazy as _

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label=_("Vorname"), required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label=_("Nachname"), required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label=_("E-Mail-Adresse"), required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if profile.user:
            profile.user.first_name = self.cleaned_data.get('first_name', '')
            profile.user.last_name = self.cleaned_data.get('last_name', '')
            profile.user.email = self.cleaned_data.get('email', '')
            if commit:
                profile.user.save()
        if commit:
            profile.save()
        return profile

    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=False,
        label=_("Birth Date")
    )
    
    auto_night_mode = forms.BooleanField(
        required=False,
        label=_("Nachtmodus Einstellungen vom System übernehmen"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
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
            'display_name', 'avatar', 'birth_date', 'language', 'currency', 'simulation_max_age',
            'inflation_rate', 'salary_increase', 'pension_increase', 'investment_return_offset',
            'real_estate_growth_rate', 'physical_asset_growth_rate',
            'auto_night_mode', 'dark_mode_config',
            'gradient_start', 'gradient_end', 'primary_color', 'secondary_color',
            'background_color', 'text_color', 'sidebar_bg_color',
            'table_header_bg_color', 'table_header_text_color', 'table_filter_bg_color',
            'table_body_bg_color', 'table_body_text_color', 'table_border_color'
        ]
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'dark_mode_config': forms.HiddenInput(),
        }
