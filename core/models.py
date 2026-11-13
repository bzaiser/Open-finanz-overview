from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

def get_default_dashboard_config():
    return {
        "layout": [
            {"id": "upcoming_dates_widget", "visible": True, "width": 6, "height": "medium", "order": 0},
            {"id": "income_table_widget", "visible": True, "width": 6, "height": "medium", "order": 1},
            {"id": "cashflow_chart", "visible": True, "width": 12, "height": "medium", "order": 2},
            {"id": "net_worth_chart", "visible": True, "width": 12, "height": "small", "order": 3},
            {"id": "liquid_pension_forecast_chart", "visible": True, "width": 12, "height": "small", "order": 4},
            {"id": "real_estate_forecast_chart", "visible": True, "width": 12, "height": "small", "order": 5},
            {"id": "physical_asset_forecast_chart", "visible": True, "width": 12, "height": "small", "order": 6},
            {"id": "inflation_monitor_chart", "visible": True, "width": 12, "height": "small", "order": 7},
            {"id": "income_evolution_chart", "visible": True, "width": 12, "height": "medium", "order": 8},
            {"id": "expense_evolution_chart", "visible": True, "width": 6, "height": "medium", "order": 9},
            {"id": "budget_pie_chart", "visible": True, "width": 6, "height": "medium", "order": 10},
            {"id": "asset_allocation_chart", "visible": True, "width": 6, "height": "medium", "order": 11},
            {"id": "asset_table_widget", "visible": True, "width": 6, "height": "medium", "order": 12},
            {"id": "pension_table_widget", "visible": True, "width": 6, "height": "medium", "order": 13},
            {"id": "event_table_widget", "visible": True, "width": 6, "height": "medium", "order": 14},
            {"id": "expense_table_widget", "visible": True, "width": 6, "height": "medium", "order": 15},
            {"id": "loan_evolution_chart", "visible": True, "width": 6, "height": "medium", "order": 16},
            {"id": "loan_table_widget", "visible": True, "width": 6, "height": "medium", "order": 17}
        ],
        "summary_layout": [
            {"id": "monthly_income", "visible": True, "bg_color": "#198754", "text_color": "#ffffff", "order": 1},
            {"id": "monthly_expenses", "visible": True, "bg_color": "#dc3545", "text_color": "#ffffff", "order": 2},
            {"id": "current_pension_payout", "visible": True, "bg_color": "#fd7e14", "text_color": "#ffffff", "order": 3},
            {"id": "total_pensions", "visible": True, "bg_color": "#0dcaf0", "text_color": "#ffffff", "order": 4},
            {"id": "current_assets", "visible": True, "bg_color": "#36d956", "text_color": "#ffffff", "order": 5},
            {"id": "expected_payout", "visible": True, "bg_color": "#6f42c1", "text_color": "#ffffff", "order": 6},
            {"id": "total_physical_assets", "visible": True, "bg_color": "#2c93e2", "text_color": "#ffffff", "order": 7},
            {"id": "total_real_estate", "visible": True, "bg_color": "#20c997", "text_color": "#ffffff", "order": 8},
            {"id": "total_combined_assets", "visible": True, "bg_color": "#e8b017", "text_color": "#ffffff", "order": 9},
            {"id": "total_debts", "visible": True, "bg_color": "#746d6d", "text_color": "#fbacac", "order": 10}
        ]
    }


def get_dashboard_config_for_situation(situation):
    """Returns a target-group tailored default dashboard configuration."""
    config = get_default_dashboard_config()
    budget_focused = {'low_income', 'single_parent', 'student', 'unemployed'}
    if situation in budget_focused:
        hidden_charts = {'real_estate_forecast_chart', 'physical_asset_forecast_chart'}
        hidden_summary = {'total_physical_assets', 'total_real_estate'}
        priority_order = {
            'cashflow_chart': 0,
            'budget_pie_chart': 1,
            'upcoming_dates_widget': 2,
            'income_table_widget': 3,
            'expense_table_widget': 4,
            'loan_evolution_chart': 5,
            'loan_table_widget': 6,
            'net_worth_chart': 7,
        }
        for item in config['layout']:
            if item['id'] in hidden_charts:
                item['visible'] = False
            if item['id'] in priority_order:
                item['order'] = priority_order[item['id']]
            else:
                item['order'] += 10
        config['layout'].sort(key=lambda x: x['order'])
        for s_item in config['summary_layout']:
            if s_item['id'] in hidden_summary:
                s_item['visible'] = False
    elif situation == 'early_retiree':
        for item in config['layout']:
            if item['id'] in {'real_estate_forecast_chart', 'physical_asset_forecast_chart'}:
                item['visible'] = False
            elif item['id'] == 'liquid_pension_forecast_chart':
                item['order'] = 1
        config['layout'].sort(key=lambda x: x['order'])
    return config

class CustomUser(AbstractUser):
    @property
    def best_name(self):
        try:
            if hasattr(self, 'profile') and self.profile.display_name:
                return self.profile.display_name
        except:
            pass
        if self.first_name:
            return self.first_name
        if self.last_name:
            return self.last_name
        return self.username

class UserProfile(models.Model):
    HOUSEHOLD_SITUATION_CHOICES = [
        ('standard', _('Standard / Vermögensaufbau')),
        ('low_income', _('Geringverdiener / Knappes Budget')),
        ('single_parent', _('Alleinerziehend')),
        ('student', _('Student / Ausbildung')),
        ('unemployed', _('Arbeitssuchend (ALG I / Bürgergeld)')),
        ('early_retiree', _('Frührentner / Erwerbsminderung')),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(_("Display Name"), max_length=100, blank=True, null=True)
    household_situation = models.CharField(
        _("Lebenssituation / Zielgruppe"),
        max_length=20,
        choices=HOUSEHOLD_SITUATION_CHOICES,
        default='standard',
    )
    avatar = models.ImageField(_("Avatar"), upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(_("Birth Date"), blank=True, null=True)

    # Partner details (for couples / married users)
    partner_name = models.CharField(_("Partner Name"), max_length=100, blank=True, null=True)
    partner_birth_date = models.DateField(_("Partner Birth Date"), blank=True, null=True)
    partner_retirement_age = models.PositiveIntegerField(_("Partner Retirement Age"), default=67, blank=True, null=True)
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
    retirement_age = models.PositiveIntegerField(_("Retirement Age"), default=67, help_text=_("Target retirement age for planning and gap calculation (default 67)"))
    target_pension_payout = models.DecimalField(_("Target Monthly Pension Payout (€)"), max_digits=12, decimal_places=2, blank=True, null=True, help_text=_("Target net monthly payout at retirement for pension gap analysis."))
    simulation_start_date = models.DateField(_("Simulation Start Date"), blank=True, null=True, help_text=_("Earliest date to show in charts. Leave empty for automatic (based on oldest snapshot or current year)."))
    
    # Simulation Parameters (Defaults)
    inflation_rate = models.DecimalField(_("Default Inflation Rate (%)"), max_digits=5, decimal_places=2, default=2.0)
    salary_increase = models.DecimalField(_("Default Salary Increase (%)"), max_digits=5, decimal_places=2, default=1.5)
    pension_increase = models.DecimalField(_("Default Pension Increase (%)"), max_digits=5, decimal_places=2, default=1.0)
    investment_return_offset = models.DecimalField(_("Investment Return Buffer (%)"), max_digits=5, decimal_places=2, default=0.0)
    real_estate_growth_rate = models.DecimalField(_("Default Real Estate Growth (%)"), max_digits=5, decimal_places=2, default=0.0)
    dashboard_config = models.JSONField(_("Dashboard Configuration"), default=get_default_dashboard_config, blank=True)
    
    # Night Mode / System Sync
    auto_night_mode = models.BooleanField(_("Follow System Design"), default=False)
    hide_wizard_on_start = models.BooleanField(_("Hide Setup Wizard on Startup"), default=False)
    dark_mode_config = models.JSONField(_("Night Mode Colors"), default=dict, blank=True, null=True)

    # Gradient & Unified Design Fields
    gradient_start = models.CharField(_("Gradient Start Color"), max_length=7, default="#6610f2")
    gradient_end = models.CharField(_("Gradient End Color"), max_length=7, default="#0d6efd")
    
    primary_color = models.CharField(_("Primary Color"), max_length=7, default="#0d6efd")
    secondary_color = models.CharField(_("Secondary Color"), max_length=7, default="#6c757d")
    background_color = models.CharField(_("Background Color"), max_length=7, default="#ffffff")
    text_color = models.CharField(_("Text Color"), max_length=7, default="#212529")
    sidebar_bg_color = models.CharField(_("Sidebar Background"), max_length=7, default="#f8f9fa")
    
    # Table Specific Colors
    table_header_bg_color = models.CharField(_("Table Header Background"), max_length=7, default="#0d6efd")
    table_header_text_color = models.CharField(_("Table Header Text"), max_length=7, default="#ffffff")
    table_filter_bg_color = models.CharField(_("Table Filter Background"), max_length=7, default="#f1f3f5")
    table_body_bg_color = models.CharField(_("Table Body Background"), max_length=7, default="#ffffff")
    table_body_text_color = models.CharField(_("Table Body Text"), max_length=7, default="#212529")
    table_border_color = models.CharField(_("Table Border Color"), max_length=7, default="#dee2e6")

    # Data Backup & Recovery Configuration
    BACKUP_FREQUENCY_CHOICES = [
        ('never', _('Nie sichern (ich sichere bereits extern, z. B. am NAS)')),
        ('daily', _('Täglich')),
        ('weekly', _('Einmal pro Woche')),
        ('monthly', _('Einmal pro Monat')),
    ]
    backup_frequency = models.CharField(
        _("Sicherungs-Häufigkeit"),
        max_length=20,
        choices=BACKUP_FREQUENCY_CHOICES,
        default='weekly',
        help_text=_("Regelmäßigkeit der Erinnerung bzw. automatischen Sicherung.")
    )
    backup_path = models.CharField(
        _("Sicherungs-Ordnerpfad"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Optionaler Zielordner für automatische Backups (z. B. D:\\Backups oder Netzlaufwerk).")
    )
    backup_last_run = models.DateTimeField(
        _("Letzte Sicherung"),
        blank=True,
        null=True
    )
    backup_max_keep = models.PositiveIntegerField(
        _("Max. Sicherungen aufbewahren"),
        default=5,
        help_text=_("Ältere Backups im Zielordner werden automatisch bereinigt.")
    )
    backup_dismissed_until = models.DateField(
        _("Erinnerung stummgeschaltet bis"),
        blank=True,
        null=True
    )


    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"{self.user.username}'s Profile"


class EditablePageContent(models.Model):
    PAGE_CHOICES = [
        ('help', _('Help')),
        ('about', _('About')),
    ]
    page = models.CharField(_("Page"), max_length=20, choices=PAGE_CHOICES)
    section_key = models.CharField(_("Section Key"), max_length=100)
    language = models.CharField(_("Language"), max_length=10, default="de")
    content = models.TextField(_("Content"), blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Editable Page Content")
        verbose_name_plural = _("Editable Page Contents")
        unique_together = ('page', 'section_key', 'language')

    def __str__(self):
        return f"[{self.language}] {self.page} - {self.section_key}"


class DesignHarmony(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    primary_color = models.CharField(_("Primary Color"), max_length=20, default="#0d6efd")
    gradient_start = models.CharField(_("Gradient Start"), max_length=20, default="#6610f2")
    gradient_end = models.CharField(_("Gradient End"), max_length=20, default="#0d6efd")
    background_color = models.CharField(_("Background Color"), max_length=20, default="#ffffff")
    sidebar_bg_color = models.CharField(_("Sidebar Background"), max_length=20, default="#f8f9fa")
    text_color = models.CharField(_("Text Color"), max_length=20, default="#212529")
    table_header_bg_color = models.CharField(_("Table Header BG"), max_length=20, blank=True, null=True, help_text=_("Hintergrundfarbe der Tabellen-Überschriften (Leer = Fallback auf Primärfarbe)"))
    table_header_text_color = models.CharField(_("Table Header Text"), max_length=20, default="#ffffff", help_text=_("Schriftfarbe der Tabellen-Überschriften (z. B. #ffffff)"))
    table_body_bg_color = models.CharField(_("Table Body BG"), max_length=20, blank=True, null=True, help_text=_("Hintergrundfarbe der Datenzeilen (Leer = Fallback auf App-Hintergrund)"))
    table_body_text_color = models.CharField(_("Table Body Text"), max_length=20, blank=True, null=True, help_text=_("Schriftfarbe der Datenzeilen (Leer = Fallback auf App-Textfarbe)"))
    table_border_color = models.CharField(_("Table Border"), max_length=20, default="#dee2e6", help_text=_("Farbe der Trennlinien und Rahmen zwischen Zeilen und Spalten"))
    order = models.PositiveIntegerField(_("Display Order"), default=0)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Design Harmony")
        verbose_name_plural = _("Design Harmonies")
        ordering = ['order', 'id']

    def __str__(self):
        return self.name
