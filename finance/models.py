from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from core.models import CustomUser


class Category(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    slug = models.SlugField(_("Slug"), unique=True)
    color = models.CharField(_("Color"), max_length=7, default="#6c757d", help_text=_("Hex color code, e.g. #FF0000"))
    
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name

class CashFlowSource(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cash_flows')
    name = models.CharField(_("Name"), max_length=100)
    value = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    start_date = models.DateField(_("Start Date"), blank=True, null=True)
    end_date = models.DateField(_("End Date"), blank=True, null=True)
    is_income = models.BooleanField(_("Is Income"), default=True)
    is_inflation_adjusted = models.BooleanField(_("Inflation Adjusted"), default=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Category"))
    frequency = models.CharField(_("Frequency"), max_length=20, default='monthly', choices=FREQUENCY_CHOICES)
    
    class Meta:
        verbose_name = _("Cash Flow Source")
        verbose_name_plural = _("Cash Flow Sources")

    def __str__(self):
        return f"{self.name} ({self.value})"

class Asset(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(_("Name"), max_length=100)
    value = models.DecimalField(_("Current Value"), max_digits=12, decimal_places=2)
    growth_rate = models.DecimalField(_("Annual Growth Rate (%)"), max_digits=5, decimal_places=2, default=0.0)
    
    class Meta:
        verbose_name = _("Asset")
        verbose_name_plural = _("Assets")

    def __str__(self):
        return self.name

class OneTimeEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(_("Name"), max_length=100)
    value = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2, help_text=_("Positive for income, negative for expense"))
    date = models.DateField(_("Date"))
    description = models.TextField(_("Description"), blank=True)
    
    class Meta:
        verbose_name = _("One Time Event")
        verbose_name_plural = _("One Time Events")

    def __str__(self):
        return self.name

class Pension(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pensions')
    provider = models.CharField(_("Provider/Name"), max_length=100)
    current_value = models.DecimalField(_("Current Value"), max_digits=12, decimal_places=2, default=0.00)
    monthly_contribution = models.DecimalField(_("Monthly Contribution"), max_digits=10, decimal_places=2, default=0.00)
    growth_rate = models.DecimalField(_("Annual Growth Rate (%)"), max_digits=5, decimal_places=2, default=0.00)
    expected_payout_at_retirement = models.DecimalField(_("Expected Monthly Payout"), max_digits=10, decimal_places=2, blank=True, null=True)
    start_payout_date = models.DateField(_("Payout Start Date"), blank=True, null=True, help_text=_("Approximate date when pension payout starts"))

    class Meta:
        verbose_name = _("Pension")
        verbose_name_plural = _("Pensions")

    def __str__(self):
        return self.provider

class FinancialStatusProxy(CustomUser):
    class Meta:
        proxy = True
        verbose_name = _("Mein Finanzstatus (Vorausgefüllt)")
        verbose_name_plural = _("Meine Finanzen (Schnelleingabe)")

