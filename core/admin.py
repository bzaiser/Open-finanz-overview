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


from .forms import DesignHarmonyAdminForm

@admin.register(DesignHarmony)
class DesignHarmonyAdmin(admin.ModelAdmin):
    form = DesignHarmonyAdminForm
    list_display = ('name', 'preview_badge', 'order', 'primary_color', 'background_color', 'text_color', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('live_preview',)
    fieldsets = (
        (None, {'fields': ('name', 'order', 'is_active')}),
        (_('Live-Vorschau'), {'fields': ('live_preview',)}),
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

    def live_preview(self, obj):
        from django.utils.html import format_html
        start = obj.gradient_start if obj and obj.gradient_start else '#6610f2'
        end = obj.gradient_end if obj and obj.gradient_end else '#0d6efd'
        primary = obj.primary_color if obj and obj.primary_color else '#0d6efd'
        bg = obj.background_color if obj and obj.background_color else '#ffffff'
        text = obj.text_color if obj and obj.text_color else '#212529'
        return format_html(
            '''
            <div id="harmony-admin-preview" style="padding: 1.5rem; border-radius: 12px; background: {}; color: {}; border: 2px solid {}; max-width: 480px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <div id="preview-gradient-box" style="height: 50px; border-radius: 8px; background: linear-gradient(135deg, {} 0%, {} 100%); margin-bottom: 12px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: bold; text-shadow: 0 1px 2px rgba(0,0,0,0.4);">
                    {}
                </div>
                <div style="display: flex; gap: 8px; align-items: center; font-size: 0.85rem;">
                    <span id="preview-btn" style="padding: 4px 12px; border-radius: 20px; background: {}; color: #fff; font-weight: 600;">Button</span>
                    <span>Textfarbe Vorschau auf Hintergrund</span>
                </div>
            </div>
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                function updateAdminPreview() {
                    const gStart = document.getElementById('id_gradient_start')?.value || '#6610f2';
                    const gEnd = document.getElementById('id_gradient_end')?.value || '#0d6efd';
                    const prim = document.getElementById('id_primary_color')?.value || '#0d6efd';
                    const bg = document.getElementById('id_background_color')?.value || '#ffffff';
                    const txt = document.getElementById('id_text_color')?.value || '#212529';
                    const gBox = document.getElementById('preview-gradient-box');
                    const container = document.getElementById('harmony-admin-preview');
                    const btn = document.getElementById('preview-btn');
                    if (gBox) gBox.style.background = `linear-gradient(135deg, ${gStart} 0%, ${gEnd} 100%)`;
                    if (container) {
                        container.style.backgroundColor = bg;
                        container.style.color = txt;
                        container.style.borderColor = prim;
                    }
                    if (btn) btn.style.backgroundColor = prim;
                }
                const inputs = document.querySelectorAll('input[type="color"]');
                inputs.forEach(inp => inp.addEventListener('input', updateAdminPreview));
            });
            </script>
            ''',
            bg, text, primary, start, end, obj.name or _('Preset Preview'), primary
        )
    live_preview.short_description = _("Live Vorschau")

    def preview_badge(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<div style="width: 50px; height: 22px; border-radius: 12px; background: linear-gradient(135deg, {} 0%, {} 100%); border: 1px solid rgba(0,0,0,0.15);" title="{}"></div>',
            obj.gradient_start, obj.gradient_end, obj.name
        )
    preview_badge.short_description = _("Preview")
