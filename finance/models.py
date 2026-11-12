from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from django.conf import settings
from core.models import CustomUser
from django.utils.text import slugify
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal


OWNER_ROLE_CHOICES = [
    ('primary', _('Hauptperson')),
    ('partner', _('Partner/in')),
    ('joint', _('Gemeinsam / Haushalt')),
]


class Category(models.Model):
    name = models.CharField(_("Display Name"), max_length=100)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    color = models.CharField(_("Color"), max_length=7, default="#6c757d", help_text=_("Hex color code, e.g. #FF0000"))
    is_system = models.BooleanField(_("System Category"), default=False)
    
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise PermissionError(_("System categories cannot be deleted."))
        super().delete(*args, **kwargs)

    @property
    def translated_name(self):
        return gettext(self.name)

    def __str__(self):
        return self.translated_name

class CashFlowSource(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cash_flows')
    name = models.CharField(_("Display Name"), max_length=100)
    value = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    start_date = models.DateField(_("Start Date"), blank=True, null=True)
    end_date = models.DateField(_("End Date"), blank=True, null=True)
    is_income = models.BooleanField(_("Is Income"), default=True)
    is_inflation_adjusted = models.BooleanField(_("Indexed (Inflation Adjustment)"), default=True, help_text=_("If checked, the payout will increase annually based on the global pension increase rate."))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Category"))
    frequency = models.CharField(_("Frequency"), max_length=20, default='monthly', choices=FREQUENCY_CHOICES)
    owner_role = models.CharField(_("Zugeordnete Person"), max_length=20, choices=OWNER_ROLE_CHOICES, default='primary')
    notes = models.TextField(_("Notes"), blank=True, null=True)
    template_id = models.CharField(_("Template ID"), max_length=100, blank=True, null=True, db_index=True)
    
    class Meta:
        verbose_name = _("Cash Flow Source")
        verbose_name_plural = _("Cash Flow Sources")

    @property
    def monthly_amount(self):
        if self.frequency == 'yearly' and self.value:
            return (self.value / Decimal('12')).quantize(Decimal('0.01'))
        return self.value

    def __str__(self):
        return f"{self.name} ({self.value})"

    @classmethod
    def active_on_q(cls, ref_date=None):
        """Return Q filter for cash flows active on ref_date (defaults to today)."""
        if ref_date is None:
            ref_date = timezone.localdate()
        return (
            (models.Q(start_date__isnull=True) | models.Q(start_date__lte=ref_date))
            & (models.Q(end_date__isnull=True) | models.Q(end_date__gte=ref_date))
        )

    @classmethod
    def expense_choices_q(cls, user_id=None, include_pk=None, ref_date=None):
        """Return Q filter for currently valid expense cash flows (optionally scoped by user)."""
        active_expense_q = cls.active_on_q(ref_date=ref_date) & models.Q(is_income=False)
        q = (models.Q(user_id=user_id) & active_expense_q) if user_id else active_expense_q
        if include_pk:
            q = q | models.Q(pk=include_pk)
        return q

    def format_choice_label(self):
        """Format label with optional validity range for linked policy dropdowns."""
        base = str(self)
        if not self.start_date and not self.end_date:
            return base
        start_s = self.start_date.strftime('%d.%m.%Y') if self.start_date else '...'
        end_s = self.end_date.strftime('%d.%m.%Y') if self.end_date else '...'
        return f"{base} [{start_s}–{end_s}]"

class Asset(models.Model):
    ASSET_TYPE_CHOICES = [
        ('cash', _('Cash & Checking')),
        ('overnight', _('Overnight & Money Market')),
        ('depot', _('Securities & ETF Depot')),
        ('crypto', _('Cryptocurrencies (Bitcoin / Altcoins)')),
        ('precious_metal', _('Precious Metals (Gold / Silver)')),
        ('other', _('Other Financial Asset')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(_("Display Name"), max_length=100)
    asset_type = models.CharField(_("Asset Type"), max_length=20, choices=ASSET_TYPE_CHOICES, default='cash')
    institution = models.CharField(_("Bank / Broker / Platform"), max_length=100, blank=True, null=True)
    isin_ticker = models.CharField(_("ISIN / WKN / Ticker"), max_length=30, blank=True, null=True)
    monthly_savings_amount = models.DecimalField(_("Monthly Savings Plan"), max_digits=10, decimal_places=2, default=0.0, help_text=_("Optional regular monthly savings or purchase amount"))
    is_emergency_fund = models.BooleanField(_("Emergency Fund (Notgroschen)"), default=False, help_text=_("Designate this cash/overnight account as emergency liquidity reserve"))

    value = models.DecimalField(_("Current Value"), max_digits=12, decimal_places=2)
    growth_rate = models.DecimalField(_("Annual Growth Rate (%)"), max_digits=5, decimal_places=2, default=0.0)
    interest_teaser_rate = models.DecimalField(_("Teaser Interest Rate (%)"), max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("Higher promotional interest rate (e.g. for new customers)"))
    interest_teaser_until = models.DateField(_("Teaser Rate Expiry Date"), null=True, blank=True, help_text=_("Date when the teaser rate expires and falls back to the standard growth rate"))

    
    # Withdrawal / Decumulation
    withdrawal_amount = models.DecimalField(_("Monthly Withdrawal"), max_digits=12, decimal_places=2, default=0.0, help_text=_("Amount to take out of this asset each month"))
    withdrawal_start_date = models.DateField(_("Withdrawal Start Date"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Asset")
        verbose_name_plural = _("Assets")

    def __str__(self):
        return self.name

class OneTimeEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(_("Display Name"), max_length=100)
    value = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2, help_text=_("Positive for income, negative for expense"))
    date = models.DateField(_("Entry Date"))
    description = models.TextField(_("Description"), blank=True)
    
    class Meta:
        verbose_name = _("One Time Event")
        verbose_name_plural = _("One Time Events")

    def __str__(self):
        return self.name

class Pension(models.Model):
    PENSION_TYPE_CHOICES = [
        ('capital', _('Kapital- / Private Rentenversicherung')),
        ('statutory', _('Gesetzliche Rente (DRV)')),
        ('civil_service', _('Beamtenpension / Ruhegehalt')),
        ('occupational_fund', _('Berufsständisches Versorgungswerk / VBL')),
    ]

    PAYOUT_TYPE_CHOICES = [
        ('capital_drawdown', _('Monatlicher Auszahlungsplan (Kapitalverzehr)')),
        ('lifelong_annuity', _('Laufende Rente (Lebenslang)')),
        ('one_time', _('Einmalige Kapitalabfindung (z. B. bAV)')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pensions')
    provider = models.CharField(_("Provider/Name"), max_length=100)
    owner_role = models.CharField(_("Zugeordnete Person"), max_length=20, choices=OWNER_ROLE_CHOICES, default='primary')
    pension_type = models.CharField(_("Pension Type"), max_length=20, choices=PENSION_TYPE_CHOICES, default='capital')
    payout_type = models.CharField(_("Payout Type"), max_length=20, choices=PAYOUT_TYPE_CHOICES, default='capital_drawdown', help_text=_("Auszahlungsart: Kapitalverzehr, lebenslange Rente oder Einmalabfindung"))
    current_value = models.DecimalField(_("Current Value"), max_digits=12, decimal_places=2, default=0.00)
    monthly_contribution = models.DecimalField(_("Monthly Contribution"), max_digits=10, decimal_places=2, default=0.00)
    growth_rate = models.DecimalField(_("Annual Growth Rate (%)"), max_digits=5, decimal_places=2, default=0.00)
    
    # Statutory pension fields
    pension_points = models.DecimalField(_("Pension Points (Entgeltpunkte)"), max_digits=8, decimal_places=4, null=True, blank=True, help_text=_("Number of statutory pension points accumulated"))
    point_value = models.DecimalField(_("Point Value (€)"), max_digits=6, decimal_places=2, null=True, blank=True, help_text=_("Value of 1 pension point in EUR (e.g. 40.79)"))
    gross_payout_amount = models.DecimalField(_("Gross Monthly Payout (€)"), max_digits=10, decimal_places=2, null=True, blank=True, help_text=_("Calculated automatically from points * point_value, or enter manually"))
    social_deduction_rate = models.DecimalField(_("Social Security Deduction (%)"), max_digits=5, decimal_places=2, default=11.50, help_text=_("Deduction percentage for health & nursing care insurance (~11.5%)"))
    disability_pension_net = models.DecimalField(_("Disability Pension Net (€/month)"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Pension in case of full reduction in earning capacity ('Wären Sie heute voll erwerbsgemindert...')"))

    expected_payout_at_retirement = models.DecimalField(_("Expected Monthly Net Payout"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Projected regular old-age pension ('Sollten bis zum Rentenbeginn Beiträge gezahlt werden...')"))
    retirement_age = models.PositiveIntegerField(_("Retirement Age"), blank=True, null=True, help_text=_("Target retirement age for this specific pension contract (e.g. 67)"))
    target_pension_payout = models.DecimalField(_("Target Monthly Payout (€)"), max_digits=12, decimal_places=2, blank=True, null=True, help_text=_("Target net monthly payout desired for this specific contract"))
    is_indexed = models.BooleanField(_("Indexed (Inflation Adjustment)"), default=True, help_text=_("If checked, the payout will increase annually based on the global pension increase rate."))
    contribution_end_date = models.DateField(verbose_name=_("Contribution End Date"), blank=True, null=True, help_text=_("Date when you stop paying into this pension"))
    start_payout_date = models.DateField(_("Payout Start Date"), blank=True, null=True, help_text=_("Approximate date when pension payout starts"))
    notes = models.TextField(_("Notes"), blank=True, null=True, help_text=_("Additional multiline notes or details"))

    class Meta:
        verbose_name = _("Pension")
        verbose_name_plural = _("Pensions")

    @property
    def gross_payout(self):
        if self.gross_payout_amount:
            return self.gross_payout_amount
        if self.pension_type == 'statutory' and self.pension_points is not None and self.point_value is not None:
            return (self.pension_points * self.point_value).quantize(Decimal('0.01'))
        return self.expected_payout_at_retirement

    def save(self, *args, **kwargs):
        # Fallback 1: Calculate gross only if empty and points & point_value are given
        if self.gross_payout_amount is None:
            if self.pension_type == 'statutory' and self.pension_points is not None and self.point_value is not None:
                self.gross_payout_amount = (self.pension_points * self.point_value).quantize(Decimal('0.01'))

        # Fallback 2: Calculate net only if empty and gross is available
        if self.expected_payout_at_retirement is None:
            gross = self.gross_payout_amount or (self.gross_payout if self.gross_payout else None)
            if gross and self.social_deduction_rate is not None:
                rate = (self.social_deduction_rate or Decimal('0.00')) / Decimal('100.00')
                net = gross * (Decimal('1.00') - rate)
                self.expected_payout_at_retirement = net.quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    def __str__(self):
        return self.provider


class ImportBatch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='import_batches')
    date = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=128, blank=True, null=True, db_index=True) # SHA256 of the file content
    is_applied = models.BooleanField(default=False)
    ai_log = models.TextField(_("AI Log / Errors"), blank=True, null=True)

    class Meta:
        verbose_name = _("Import Batch")
        verbose_name_plural = _("Import Batches")

    def __str__(self):
        return f"{self.filename} ({self.date.strftime('%d.%m.%Y')})"

class PendingTransaction(models.Model):
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField(_("Entry Date"))
    description = models.TextField(_("Description"))
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    is_income = models.BooleanField(_("Is Income"), default=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Suggested Category"))
    
    # Matching against Finance Plan
    planned_amount = models.DecimalField(_("Planned Amount"), max_digits=12, decimal_places=2, null=True, blank=True)
    
    # AI/Heuristic Suggestions
    is_recurring = models.BooleanField(_("Is Recurring"), default=False)
    frequency = models.CharField(_("Frequency"), max_length=20, default='monthly', choices=CashFlowSource.FREQUENCY_CHOICES)
    ai_reasoning = models.TextField(_("AI Reasoning"), blank=True, null=True)
    ai_confidence = models.FloatField(_("AI Confidence"), default=1.0, help_text=_("0.0 to 1.0"))
    
    # User Review state
    is_ignored = models.BooleanField(_("Ignore"), default=False)
    
    # Consolidation & Duplicate Detection
    matched_terms = models.TextField(_("Matched Terms (Notes)"), blank=True, null=True)
    integration_count = models.IntegerField(_("Integration Count"), default=1)
    signature = models.CharField(_("Transaction Signature"), max_length=255, blank=True, null=True, db_index=True)
    
    # Conflict state with Plan
    has_conflict = models.BooleanField(_("Has Plan Conflict"), default=False)
    is_confirmed = models.BooleanField(_("Confirmed Conflict"), default=False) # For manual overwrite approval
    existing_source = models.ForeignKey(CashFlowSource, on_delete=models.SET_NULL, null=True, blank=True, related_name='conflicting_transactions')

    # Row Tracking (Fingerprints)
    raw_signatures = models.TextField(_("Raw Row Fingerprints"), blank=True, null=True, help_text=_("Semicolon-separated MD5 hashes of original Excel rows"))

    class Meta:
        verbose_name = _("Pending Transaction")
        verbose_name_plural = _("Pending Transactions")

    def __str__(self):
        return f"{self.description} ({self.amount})"


class ProcessedTransactionHash(models.Model):
    """
    Stores a persistent MD5 hash of an individual transaction row
    to prevent re-importing the same transaction in future files.
    Linked to a batch for easy cleanup if needed.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='processed_hashes')
    hash = models.CharField(max_length=64, db_index=True)
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name='row_hashes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'hash')
        verbose_name = _("Processed Transaction Hash")
        verbose_name_plural = _("Processed Transaction Hashes")


class PhysicalAsset(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='physical_assets')
    name = models.CharField(_("Display Name"), max_length=100)
    value = models.DecimalField(_("Current Value"), max_digits=12, decimal_places=2)
    appreciation_rate = models.DecimalField(_("Annual Appreciation Rate (%)"), max_digits=5, decimal_places=2, default=0.0)
    location = models.CharField(_("Location / Storage"), max_length=255, blank=True)
    storage_costs_monthly = models.DecimalField(_("Monthly Storage/Maintenance Costs"), max_digits=10, decimal_places=2, default=0.0)
    acquisition_date = models.DateField(_("Acquisition Date"), null=True, blank=True)
    is_sold = models.BooleanField(_("Is Sold"), default=False)
    sale_date = models.DateField(_("Sale Date"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Physical Asset")
        verbose_name_plural = _("Physical Assets")

    def __str__(self):
        return f"{self.name} ({self.value})"


class RealEstate(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ('apartment', _('Apartment / Condominium')),
        ('house', _('Single-Family / Semi-Detached House')),
        ('multi_family', _('Multi-Family Building')),
        ('land', _('Land / Plot (Unbuilt)')),
        ('commercial', _('Commercial / Other')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='real_estates')
    name = models.CharField(_("Provider / Name"), max_length=100)
    property_type = models.CharField(_("Property Type"), max_length=20, choices=PROPERTY_TYPE_CHOICES, default='apartment')
    property_value = models.DecimalField(_("Property Value"), max_digits=12, decimal_places=2)
    appreciation_rate = models.DecimalField(_("Annual Appreciation Rate (%)"), max_digits=5, decimal_places=2, default=0.0)
    location = models.CharField(_("Location"), max_length=255, blank=True)
    current_tenant = models.CharField(_("Current Tenant"), max_length=100, blank=True)
    rental_income_monthly = models.DecimalField(_("Monthly Rental Income (Net)"), max_digits=10, decimal_places=2, default=0.0)
    maintenance_costs_monthly = models.DecimalField(_("Monthly Maintenance/Mgmt Costs"), max_digits=10, decimal_places=2, default=0.0)
    ancillary_costs_monthly = models.DecimalField(_("Monthly Ancillary Costs (Nebenkosten)"), max_digits=10, decimal_places=2, default=0.0)
    construction_year = models.PositiveIntegerField(_("Construction Year"), null=True, blank=True)
    living_space_sqm = models.DecimalField(_("Living Space (sqm)"), max_digits=8, decimal_places=2, null=True, blank=True)
    current_maintenance_reserve = models.DecimalField(_("Current Maintenance Reserve"), max_digits=12, decimal_places=2, default=0.0, help_text=_("Current accumulated reserve for this property"))
    monthly_maintenance_allocation = models.DecimalField(_("Monthly Reserve Allocation"), max_digits=10, decimal_places=2, default=0.0, help_text=_("Monthly allocation to the maintenance reserve"))
    building_share_percent = models.DecimalField(_("Building Share (% of Value)"), max_digits=5, decimal_places=2, default=70.0, help_text=_("Percentage of property value attributable to the building for tax depreciation"))
    depreciation_rate_percent = models.DecimalField(_("Depreciation Rate (% AfA p.a.)"), max_digits=5, decimal_places=2, default=2.0, help_text=_("Annual linear tax depreciation rate (e.g. 2.0%, 2.5%, 3.0%)"))
    is_rental_property = models.BooleanField(_("Rented Property (Subject to Tax / Anlage V)"), default=True)
    is_sold = models.BooleanField(_("Is Sold"), default=False)
    sale_date = models.DateField(_("Sale Date"), null=True, blank=True)
    acquisition_date = models.DateField(_("Acquisition Date"), null=True, blank=True)

    class Meta:
        verbose_name = _("Real Estate")
        verbose_name_plural = _("Real Estates")

    def __str__(self):
        return f"{self.name} ({self.property_value})"


class PropertyComponent(models.Model):
    COMPONENT_TYPE_CHOICES = [
        ('roof', _('Roof')),
        ('heating', _('Heating System')),
        ('windows', _('Windows & Doors')),
        ('facade', _('Facade & Insulation')),
        ('bathroom', _('Bathrooms & Sanitary')),
        ('electrical', _('Electrical Installations')),
        ('plumbing', _('Plumbing & Pipes')),
        ('elevator', _('Elevator')),
        ('balcony', _('Balconies / Terraces')),
        ('other', _('Other / General Renovation')),
    ]

    CONDITION_CHOICES = [
        ('good', _('Good (No immediate action)')),
        ('moderate', _('Moderate (Action in medium term)')),
        ('critical', _('Critical (Renovation / Replacement required soon)')),
    ]

    real_estate = models.ForeignKey(RealEstate, on_delete=models.CASCADE, related_name='components', verbose_name=_("Real Estate"))
    component_type = models.CharField(_("Component Type"), max_length=30, choices=COMPONENT_TYPE_CHOICES, default='roof')
    name = models.CharField(_("Component Name / Specification"), max_length=150)
    installation_year = models.PositiveIntegerField(_("Year of Installation / Renovation"))
    expected_lifespan = models.PositiveIntegerField(_("Expected Lifespan (Years)"), default=25)
    estimated_cost = models.DecimalField(_("Estimated Replacement Cost"), max_digits=12, decimal_places=2, default=0.0)
    condition = models.CharField(_("Condition"), max_length=20, choices=CONDITION_CHOICES, default='good')
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Property Component")
        verbose_name_plural = _("Property Components")
        ordering = ['real_estate', 'installation_year']

    @property
    def replacement_year(self):
        return self.installation_year + self.expected_lifespan

    @property
    def remaining_years(self):
        current_year = timezone.now().year
        return self.replacement_year - current_year

    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()}) - {self.real_estate.name}"


class PropertyDocument(models.Model):
    CATEGORY_CHOICES = [
        ('contract', _('Purchase / Notary Contract')),
        ('loan_agreement', _('Loan / Financing Agreement')),
        ('land_register', _('Land Register Excerpt')),
        ('energy_cert', _('Energy Performance Certificate')),
        ('lease', _('Tenancy / Lease Agreement')),
        ('maintenance_invoice', _('Renovation / Craftsman Invoice')),
        ('tax_statement', _('Property Tax / Tax Assessment')),
        ('insurance', _('Building Insurance Policy')),
        ('other', _('Other Document')),
    ]

    real_estate = models.ForeignKey(RealEstate, on_delete=models.CASCADE, related_name='documents', verbose_name=_("Real Estate"))
    title = models.CharField(_("Document Title"), max_length=200)
    category = models.CharField(_("Category"), max_length=30, choices=CATEGORY_CHOICES, default='other')
    file = models.FileField(_("File"), upload_to='property_documents/')
    date = models.DateField(_("Document / Invoice Date"), default=timezone.now)
    amount = models.DecimalField(_("Invoice Amount (€)"), max_digits=12, decimal_places=2, null=True, blank=True, help_text=_("Optional: Invoice amount for tax deduction"))
    notes = models.TextField(_("Notes"), blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Property Document")
        verbose_name_plural = _("Property Documents")
        ordering = ['-date', '-uploaded_at']

    @property
    def file_size_display(self):
        try:
            size = self.file.size
            if size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            return f"{size / (1024 * 1024):.1f} MB"
        except Exception:
            return "N/A"

    def __str__(self):
        return f"{self.title} ({self.get_category_display()}) - {self.real_estate.name}"


class FinancialStatusProxy(CustomUser):
    class Meta:
        proxy = True
        verbose_name = _("My Financial Status")
        verbose_name_plural = _("My Finances (Quick Entry)")


class Loan(models.Model):
    LOAN_TYPE_CHOICES = [
        ('annuity', _('Annuity Loan (Constant Installment)')),
        ('fixed_amortization', _('Amortization Loan (Fixed Principal + Falling Interest)')),
        ('bullet', _('Bullet Loan (Interest-Only, Lump-Sum at End)')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loans')
    loan_type = models.CharField(_("Loan Type"), max_length=20, choices=LOAN_TYPE_CHOICES, default='annuity')
    owner_role = models.CharField(_("Zugeordnete Person"), max_length=20, choices=OWNER_ROLE_CHOICES, default='joint')
    name = models.CharField(_("Display Name"), max_length=100)
    provider = models.CharField(_("Provider / Bank"), max_length=100, blank=True)
    nominal_amount = models.DecimalField(_("Initial Loan Amount"), max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(_("Interest Rate (%)"), max_digits=5, decimal_places=2)
    interest_lock_end = models.DateField(_("Interest Lock End Date"), null=True, blank=True)
    monthly_installment = models.DecimalField(_("Monthly Installment"), max_digits=12, decimal_places=2)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    allows_extra_repayment = models.BooleanField(_("Extra Repayment Possible"), default=False)
    real_estate = models.ForeignKey(
        'RealEstate', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='loans', verbose_name=_("Associated Real Estate")
    )
    account_number = models.CharField(_("Account / Loan Number"), max_length=50, blank=True)
    effective_interest_rate = models.DecimalField(_("Effective Interest Rate (%)"), max_digits=5, decimal_places=2, null=True, blank=True)
    initial_repayment_rate = models.DecimalField(_("Initial Repayment Rate (%)"), max_digits=5, decimal_places=2, null=True, blank=True)
    special_repayment_rate = models.DecimalField(_("Annual Special Repayment Limit (%)"), max_digits=5, decimal_places=2, null=True, blank=True, default=0.0)

    class Meta:
        verbose_name = _("Loan / Debt")
        verbose_name_plural = _("Loans / Debts")

    def __str__(self):
        return f"{self.name} ({self.provider})"


class LoanExtraRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='extra_repayments')
    date = models.DateField(_("Entry Date"))
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _("Extra Repayment")
        verbose_name_plural = _("Extra Repayments")
        ordering = ['date']

class ImportFilter(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='import_filters')
    search_query = models.CharField(_("Search Query"), max_length=255, help_text=_("Separated by semicolon, e.g. EDEKA;REWE"))
    target_name = models.CharField(_("Target Name"), max_length=100, help_text=_("e.g. Grocery shopping"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Category"))
    is_income = models.BooleanField(_("Is Income"), default=False)
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    # Bridge to Finance Plan
    linked_cash_flow = models.ForeignKey(CashFlowSource, on_delete=models.SET_NULL, null=True, blank=True, 
                                        related_name='import_filters', verbose_name=_("Linked Cash Flow Source"))

    class Meta:
        verbose_name = _("Import Filter")
        verbose_name_plural = _("Import Filters")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'category'], 
                name='unique_filter_per_category',
                condition=models.Q(category__isnull=False)
            )
        ]

    def __str__(self):
        return f"{self.target_name} ({self.search_query})"

class CategorizationMemory(models.Model):
    """
    Learned categorization memory based on user confirmation.
    Stores clean_description -> category mapping.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cat_memories')
    description = models.CharField(_("Description"), max_length=255) # Cleaned version
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_("Category"))
    last_used = models.DateTimeField(auto_now=True)
    usage_count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = _("Categorization Memory")
        verbose_name_plural = _("Categorization Memories")
        constraints = [
            models.UniqueConstraint(fields=['user', 'description'], name='unique_memory_per_desc')
        ]

    def __str__(self):
        return f"{self.description} -> {self.category.name}"

class AssetSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='asset_snapshots')
    
    # Generic relationship to any asset (Account, PhysicalAsset, RealEstate, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    date = models.DateField(_("Date"))
    value = models.DecimalField(_("Value"), max_digits=15, decimal_places=2)
    
    # Optional statutory pension & private net payout historical tracking
    pension_points = models.DecimalField(_("Pension Points (Entgeltpunkte)"), max_digits=8, decimal_places=4, null=True, blank=True)
    point_value = models.DecimalField(_("Point Value (€)"), max_digits=6, decimal_places=2, null=True, blank=True)
    expected_payout_net = models.DecimalField(_("Monthly Net Payout (€)"), max_digits=10, decimal_places=2, null=True, blank=True)
    disability_pension_net = models.DecimalField(_("Disability Pension Net (€)"), max_digits=10, decimal_places=2, null=True, blank=True)

    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Historical Data")
        verbose_name_plural = _("Historical Data")
        ordering = ['-date']
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.date} - {self.content_object}: {self.value}"


class InsurancePolicy(models.Model):
    INSURANCE_TYPE_CHOICES = [
        ('liability', _('Privathaftpflichtversicherung')),
        ('disability', _('Berufsunfähigkeitsversicherung (BU)')),
        ('term_life', _('Risikolebensversicherung')),
        ('sick_pay', _('Krankentagegeldversicherung')),
        ('accident', _('Unfallversicherung')),
        ('household', _('Hausratversicherung')),
        ('building', _('Wohngebäudeversicherung')),
        ('legal', _('Rechtsschutzversicherung')),
        ('health_addon', _('Krankenzusatz / PKV')),
        ('kfz', _('KFZ-Versicherung')),
        ('other', _('Sonstige Versicherung')),
    ]

    INSURED_PERSON_CHOICES = [
        ('primary', _('Hauptperson')),
        ('partner', _('Partner/in')),
        ('joint', _('Gemeinsam / Familie')),
        ('children', _('Kinder')),
    ]

    FREQUENCY_CHOICES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='insurances')
    name = models.CharField(_("Bezeichnung / Tarif"), max_length=120)
    provider = models.CharField(_("Versicherungsgesellschaft"), max_length=120, blank=True)
    policy_number = models.CharField(_("Policen- / Vertragsnummer"), max_length=80, blank=True)
    insurance_type = models.CharField(_("Versicherungsart"), max_length=30, choices=INSURANCE_TYPE_CHOICES, default='liability')
    insured_person = models.CharField(_("Versicherte Person"), max_length=20, choices=INSURED_PERSON_CHOICES, default='primary')
    premium_amount = models.DecimalField(_("Beitrag (€)"), max_digits=10, decimal_places=2, default=0.00)
    payment_frequency = models.CharField(_("Zahlweise"), max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    linked_cash_flow = models.ForeignKey(
        CashFlowSource, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='linked_insurances', verbose_name=_("Verknüpfter Cashflow-Eintrag"),
        help_text=_("Optional: Verknüpfung zu bestehendem Ausgaben-Eintrag, um Doppelzählung zu vermeiden.")
    )
    include_in_cashflow = models.BooleanField(
        _("In Cashflow-Prognose berücksichtigen"),
        default=True,
        help_text=_("Wenn aktiviert und kein Cashflow-Eintrag verknüpft ist, fließt der Beitrag in die Simulation ein.")
    )
    coverage_lump_sum = models.DecimalField(
        _("Deckungssumme / Einmalzahlung (€)"), max_digits=14, decimal_places=2, null=True, blank=True,
        help_text=_("z. B. Todesfallsumme bei Risikoleben oder Invaliditätssumme")
    )
    coverage_monthly_payout = models.DecimalField(
        _("Monatliche Leistungsrente (€)"), max_digits=10, decimal_places=2, null=True, blank=True,
        help_text=_("z. B. monatliche BU-Rente oder Krankentagegeld-Leistung")
    )
    waiting_period_months = models.PositiveIntegerField(
        _("Karenzzeit (Monate)"), default=0,
        help_text=_("Wartezeit in Monaten bis zur Leistungszahlung (z. B. 6 Monate bei BU)")
    )
    payout_duration_months = models.PositiveIntegerField(
        _("Leistungsdauer (Monate)"), null=True, blank=True,
        help_text=_("Optional begrenzte Leistungsdauer (leer = unbegrenzt bzw. bis Vertragsende)")
    )
    start_date = models.DateField(_("Vertragsbeginn"), null=True, blank=True)
    end_date = models.DateField(_("Vertragsende / Ablaufdatum"), null=True, blank=True)
    is_active = models.BooleanField(_("Aktiv"), default=True)
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Insurance Policy")
        verbose_name_plural = _("Insurance Policies")
        ordering = ['insurance_type', 'name']

    @property
    def monthly_premium_amount(self):
        if not self.premium_amount:
            return Decimal('0.00')
        if self.payment_frequency == 'yearly':
            return (self.premium_amount / Decimal('12')).quantize(Decimal('0.01'))
        return self.premium_amount

    def __str__(self):
        return f"{self.name} ({self.get_insurance_type_display()})"
