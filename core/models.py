from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    pass

class Theme(models.Model):
    name = models.CharField(_("Name"), max_length=100)
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
    
    # Gradient Design (Moved into Theme)
    gradient_start = models.CharField(_("Gradient Start Color"), max_length=7, default="#6610f2")
    gradient_end = models.CharField(_("Gradient End Color"), max_length=7, default="#0d6efd")
    
    class Meta:
        verbose_name = _("Theme")
        verbose_name_plural = _("Themes")

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(_("Avatar"), upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(_("Birth Date"), blank=True, null=True)
    CURRENCY_CHOICES = [
        ('EUR', 'EUR \u2013 Euro'),
        ('USD', 'USD \u2013 US Dollar'),
        ('GBP', 'GBP \u2013 British Pound'),
        ('CHF', 'CHF \u2013 Swiss Franc'),
        ('JPY', 'JPY \u2013 Japanese Yen'),
        ('CNY', 'CNY \u2013 Chinese Yuan'),
        ('AUD', 'AUD \u2013 Australian Dollar'),
        ('CAD', 'CAD \u2013 Canadian Dollar'),
        ('NZD', 'NZD \u2013 New Zealand Dollar'),
        ('SEK', 'SEK \u2013 Swedish Krona'),
        ('NOK', 'NOK \u2013 Norwegian Krone'),
        ('DKK', 'DKK \u2013 Danish Krone'),
        ('PLN', 'PLN \u2013 Polish Zloty'),
        ('CZK', 'CZK \u2013 Czech Koruna'),
        ('TRY', 'TRY \u2013 Turkish Lira'),
        ('INR', 'INR \u2013 Indian Rupee'),
        ('BRL', 'BRL \u2013 Brazilian Real'),
        ('ZAR', 'ZAR \u2013 South African Rand'),
    ]
    currency = models.CharField(_("Currency"), max_length=3, default="EUR", choices=CURRENCY_CHOICES)
    language = models.CharField(_("Language"), max_length=10, default="de", choices=[
        ('de', 'Deutsch'),
        ('en', 'English'),
        ('fr', 'Français'),
        ('es', 'Español'),
        ('it', 'Italiano'),
    ])
    simulation_max_age = models.PositiveIntegerField(_("Simulation Max Age"), default=90)
    
    # Simulation Parameters (Defaults)
    inflation_rate = models.DecimalField(_("Default Inflation Rate (%)"), max_digits=5, decimal_places=2, default=2.0)
    salary_increase = models.DecimalField(_("Default Salary Increase (%)"), max_digits=5, decimal_places=2, default=1.5)
    pension_increase = models.DecimalField(_("Default Pension Increase (%)"), max_digits=5, decimal_places=2, default=1.0)
    investment_return_offset = models.DecimalField(_("Investment Return Offset (%)"), max_digits=5, decimal_places=2, default=0.0)
    
    theme = models.ForeignKey(Theme, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Theme"))
    dashboard_config = models.JSONField(_("Dashboard Configuration"), default=dict, blank=True)

    # Gradient Design
    gradient_start = models.CharField(_("Gradient Start Color"), max_length=7, default="#6610f2",
                                      help_text=_("Hex color for gradient start (e.g. #6610f2)"))
    gradient_end = models.CharField(_("Gradient End Color"), max_length=7, default="#0d6efd",
                                    help_text=_("Hex color for gradient end (e.g. #0d6efd)"))


    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"{self.user.username}'s Profile"
