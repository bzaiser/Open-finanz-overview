from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Theme, UserProfile
from finance.admin import CashFlowSourceInline, BaseOwnedModelAdmin


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = [CashFlowSourceInline]


from django import forms

class ColorPickerWidget(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {'type': 'color', 'class': 'form-control-color'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'primary_color', 'background_color')
    search_fields = ('name',)
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name.endswith('_color') or db_field.name.startswith('gradient_'):
            kwargs['widget'] = ColorPickerWidget
        return super().formfield_for_dbfield(db_field, **kwargs)

@admin.register(UserProfile)
class UserProfileAdmin(BaseOwnedModelAdmin):
    list_display = ('user', 'language', 'currency', 'simulation_max_age', 'real_estate_growth_rate', 'physical_asset_growth_rate')
    search_fields = ('user__username', 'user__email')
