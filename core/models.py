from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    pass

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(_("Avatar"), upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(_("Birth Date"), blank=True, null=True)
    dashboard_config = models.JSONField(_("Dashboard Configuration"), default=dict, blank=True)

    # Gradient & Unified Design Fields
    gradient_start = models.CharField(_("Gradient Start Color"), max_length=7, default="#6610f2")
    gradient_end = models.CharField(_("Gradient End Color"), max_length=7, default="#0d6efd")
    
    primary_color = models.CharField(_("Primary Color"), max_length=7, default="#0d6efd")
    secondary_color = models.CharField(_("Secondary Color"), max_length=7, default="#6c757d")
    background_color = models.CharField(_("Background Color"), max_length=7, default="#ffffff")
    text_color = models.CharField(_("Text Color"), max_length=7, default="#212529")
    sidebar_bg_color = models.CharField(_("Sidebar Background"), max_length=7, default="#f8f9fa")
    
    # Table Specific Colors
    table_header_bg_color = models.CharField(_("Table Header Background"), max_length=7, default="#212529")
    table_header_text_color = models.CharField(_("Table Header Text"), max_length=7, default="#ffffff")
    table_filter_bg_color = models.CharField(_("Table Filter Background"), max_length=7, default="#f1f3f5")
    table_body_bg_color = models.CharField(_("Table Body Background"), max_length=7, default="#ffffff")
    table_body_text_color = models.CharField(_("Table Body Text"), max_length=7, default="#212529")
    table_border_color = models.CharField(_("Table Border Color"), max_length=7, default="#dee2e6")


    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"{self.user.username}'s Profile"
