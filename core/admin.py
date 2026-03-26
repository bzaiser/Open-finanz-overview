from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Theme, UserProfile

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    pass

@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'primary_color', 'background_color')
    search_fields = ('name',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'currency', 'simulation_max_age')
    search_fields = ('user__username', 'user__email')
