from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProfile
from finance.admin import CashFlowSourceInline, BaseOwnedModelAdmin

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = [CashFlowSourceInline]

from django import forms

@admin.register(UserProfile)
class UserProfileAdmin(BaseOwnedModelAdmin):
    list_display = ('user', 'display_name', 'partner_name', 'birth_date', 'partner_birth_date', 'retirement_age', 'partner_retirement_age')
    search_fields = ('user__username', 'user__email', 'display_name', 'partner_name')
    fieldsets = (
        (_('User'), {'fields': ('user', 'display_name', 'avatar')}),
        (_('Person 1 (Main)'), {'fields': ('birth_date', 'retirement_age')}),
        (_('Person 2 (Partner)'), {'fields': ('partner_name', 'partner_birth_date', 'partner_retirement_age')}),
        (_('Planning & Simulation'), {'fields': ('target_pension_payout', 'simulation_max_age', 'simulation_start_date', 'inflation_rate', 'salary_increase', 'pension_increase')}),
        (_('System'), {'fields': ('language', 'currency')}),
    )
