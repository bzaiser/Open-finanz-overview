from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProfile, DesignHarmony

class AppAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        label=_('Angemeldet bleiben'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label=_("First Name"), required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label=_("Last Name"), required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label=_("Email Address"), required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
            # Set placeholder for display_name based on fallback
            fallback_name = self.instance.user.first_name or self.instance.user.last_name or self.instance.user.username
            self.fields['display_name'].widget.attrs['placeholder'] = fallback_name
            self.fields['display_name'].widget.attrs['class'] = 'form-control'

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
        label=_("Follow System Night Mode Settings"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    simulation_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=False,
        label=_("Simulation Start Date")
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

    partner_birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=False,
        label=_("Partner Birth Date")
    )

    def clean_backup_path(self):
        path = self.cleaned_data.get('backup_path')
        if not path or not path.strip():
            return None
        clean = path.strip()
        import os
        from .backup_service import test_directory_writable
        if not os.path.isabs(clean):
            raise forms.ValidationError(_("Bitte einen absoluten Pfad eingeben (z. B. D:\\Backups oder /volume2/backup)."))
        
        writable, err_msg = test_directory_writable(clean)
        if not writable:
            raise forms.ValidationError(_(f"Keine Schreibrechte auf dem Server für diesen Pfad: {err_msg}"))
        return clean

    class Meta:
        model = UserProfile
        fields = [
            'display_name', 'avatar', 'birth_date', 'retirement_age',
            'partner_name', 'partner_birth_date', 'partner_retirement_age',
            'language', 'currency', 'target_pension_payout', 'simulation_max_age', 'simulation_start_date',
            'inflation_rate', 'salary_increase', 'pension_increase', 'investment_return_offset',
            'real_estate_growth_rate',
            'auto_night_mode', 'dark_mode_config',
            'gradient_start', 'gradient_end', 'primary_color', 'secondary_color',
            'background_color', 'text_color', 'sidebar_bg_color',
            'table_header_bg_color', 'table_header_text_color', 'table_filter_bg_color',
            'table_body_bg_color', 'table_body_text_color', 'table_border_color',
            'backup_frequency', 'backup_path', 'backup_max_keep'
        ]
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'dark_mode_config': forms.HiddenInput(),
            'backup_frequency': forms.Select(attrs={'class': 'form-select'}),
            'backup_path': forms.TextInput(attrs={'class': 'form-control', 'placeholder': r'D:\Backups\Finanzplan'}),
            'backup_max_keep': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 50}),
        }


class DesignHarmonyAdminForm(forms.ModelForm):
    class Meta:
        model = DesignHarmony
        fields = '__all__'
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'gradient_start': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'gradient_end': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'background_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'sidebar_bg_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'text_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'table_header_bg_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'table_header_text_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'table_body_bg_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'table_body_text_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
            'table_border_color': forms.TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; padding: 2px; cursor: pointer; vertical-align: middle;'}),
        }
