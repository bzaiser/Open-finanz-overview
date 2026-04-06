from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile
from finance.admin import CashFlowSourceInline, BaseOwnedModelAdmin

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    inlines = [CashFlowSourceInline]

from django import forms

@admin.register(UserProfile)
class UserProfileAdmin(BaseOwnedModelAdmin):
    list_display = ('user', 'language', 'currency', 'simulation_max_age', 'real_estate_growth_rate', 'physical_asset_growth_rate')
    search_fields = ('user__username', 'user__email')
