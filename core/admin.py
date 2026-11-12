from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProfile
from finance.admin import CashFlowSourceInline, BaseOwnedModelAdmin, CurrentUserFilterMixin

@admin.register(CustomUser)
class CustomUserAdmin(CurrentUserFilterMixin, UserAdmin):
    user_filter_field = 'pk'
    inlines = [CashFlowSourceInline]

    def get_fieldsets(self, request, obj=None):
        if not request.user.is_superuser:
            # Hide permission flags and group assignments from regular users
            return (
                (None, {'fields': ('username', 'password')}),
                (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
            )
        return super().get_fieldsets(request, obj)

    def has_add_permission(self, request):
        # Only superusers can create users directly in admin (regular users register via signup)
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

from django import forms

@admin.register(UserProfile)
class UserProfileAdmin(BaseOwnedModelAdmin):
    list_display = ('user', 'display_name', 'partner_name', 'birth_date', 'partner_birth_date', 'retirement_age', 'partner_retirement_age')
    search_fields = ('user__username', 'user__email', 'display_name', 'partner_name')
    fieldsets = (
        (_('User'), {'fields': ('user', 'display_name', 'avatar')}),
        (_('Person 1 (Main)'), {'fields': ('birth_date', 'retirement_age')}),
        (_('Person 2 (Partner)'), {'fields': ('partner_name', 'partner_birth_date', 'partner_retirement_age')}),
        (_('Planning & Simulation'), {'fields': ('target_pension_payout', 'simulation_max_age', 'simulation_start_date', 'inflation_rate', 'salary_increase', 'pension_increase', 'investment_return_offset', 'real_estate_growth_rate')}),
        (_('Dashboard & Settings'), {'fields': ('dashboard_config', 'hide_wizard_on_start')}),
        (_('System'), {'fields': ('language', 'currency', 'auto_night_mode', 'dark_mode_config')}),
        (_('Theme & Styling'), {
            'classes': ('collapse',),
            'fields': (
                'gradient_start', 'gradient_end',
                'primary_color', 'secondary_color', 'background_color', 'text_color', 'sidebar_bg_color',
                'table_header_bg_color', 'table_header_text_color', 'table_filter_bg_color',
                'table_body_bg_color', 'table_body_text_color', 'table_border_color',
            )
        }),
    )


from .models import EditablePageContent, DesignHarmony

@admin.register(EditablePageContent)
class EditablePageContentAdmin(admin.ModelAdmin):
    list_display = ('page', 'section_key', 'language', 'updated_at')
    list_filter = ('page', 'language')
    search_fields = ('section_key', 'content')


@admin.register(DesignHarmony)
class DesignHarmonyAdmin(admin.ModelAdmin):
    list_display = ('name', 'preview_badge', 'order', 'primary_color', 'background_color', 'text_color', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    fieldsets = (
        (None, {'fields': ('name', 'order', 'is_active')}),
        (_('Colors & Gradient'), {
            'fields': (
                'primary_color', 'gradient_start', 'gradient_end',
                'background_color', 'sidebar_bg_color', 'text_color'
            )
        }),
        (_('Table Styling (Optional Overrides)'), {
            'classes': ('collapse',),
            'fields': (
                'table_header_bg_color', 'table_header_text_color',
                'table_body_bg_color', 'table_body_text_color',
                'table_border_color'
            )
        }),
    )

    def preview_badge(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<div style="width: 50px; height: 22px; border-radius: 12px; background: linear-gradient(135deg, {} 0%, {} 100%); border: 1px solid rgba(0,0,0,0.15);" title="{}"></div>',
            obj.gradient_start, obj.gradient_end, obj.name
        )
    preview_badge.short_description = _("Preview")
