from django.db import models
from django.utils.translation import gettext_lazy as _, gettext
from django.conf import settings
from core.models import CustomUser
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(_("Name"), max_length=100)
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
    name = models.CharField(_("Name"), max_length=100)
    value = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    start_date = models.DateField(_("Start Date"), blank=True, null=True)
    end_date = models.DateField(_("End Date"), blank=True, null=True)
    is_income = models.BooleanField(_("Is Income"), default=True)
    is_inflation_adjusted = models.BooleanField(_("Indexed (Inflation Adjustment)"), default=True, help_text=_("If checked, the payout will increase annually based on the global pension increase rate."))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Category"))
    frequency = models.CharField(_("Frequency"), max_length=20, default='monthly', choices=FREQUENCY_CHOICES)
    notes = models.TextField(_("Notes"), blank=True, null=True)
    
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
    is_indexed = models.BooleanField(_("Indexed (Inflation Adjustment)"), default=True, help_text=_("If checked, the payout will increase annually based on the global pension increase rate."))
    contribution_end_date = models.DateField(verbose_name=_("Contribution End Date"), blank=True, null=True, help_text=_("Date when you stop paying into this pension"))
    start_payout_date = models.DateField(_("Payout Start Date"), blank=True, null=True, help_text=_("Approximate date when pension payout starts"))

    class Meta:
        verbose_name = _("Pension")
        verbose_name_plural = _("Pensions")

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
    date = models.DateField(_("Date"))
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
    name = models.CharField(_("Name"), max_length=100)
    value = models.DecimalField(_("Current Value"), max_digits=12, decimal_places=2)
    appreciation_rate = models.DecimalField(_("Annual Appreciation Rate (%)"), max_digits=5, decimal_places=2, default=0.0)
    location = models.CharField(_("Location / Storage"), max_length=255, blank=True)
    storage_costs_monthly = models.DecimalField(_("Monthly Storage/Maintenance Costs"), max_digits=10, decimal_places=2, default=0.0)
    is_sold = models.BooleanField(_("Is Sold"), default=False)
    sale_date = models.DateField(_("Sale Date"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Sachwert (Physical Asset)")
        verbose_name_plural = _("Sachwerte (Physical Assets)")

    def __str__(self):
        return f"{self.name} ({self.value})"


class RealEstate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='real_estates')
    name = models.CharField(_("Name / Property"), max_length=100)
    property_value = models.DecimalField(_("Property Value"), max_digits=12, decimal_places=2)
    appreciation_rate = models.DecimalField(_("Annual Appreciation Rate (%)"), max_digits=5, decimal_places=2, default=0.0)
    location = models.CharField(_("Location"), max_length=255, blank=True)
    current_tenant = models.CharField(_("Current Tenant"), max_length=100, blank=True)
    rental_income_monthly = models.DecimalField(_("Monthly Rental Income (Net)"), max_digits=10, decimal_places=2, default=0.0)
    maintenance_costs_monthly = models.DecimalField(_("Monthly Maintenance/Mgmt Costs"), max_digits=10, decimal_places=2, default=0.0)
    ancillary_costs_monthly = models.DecimalField(_("Monthly Ancillary Costs (Nebenkosten)"), max_digits=10, decimal_places=2, default=0.0)
    is_sold = models.BooleanField(_("Is Sold"), default=False)
    sale_date = models.DateField(_("Sale Date"), null=True, blank=True)

    class Meta:
        verbose_name = _("Immobilie (Real Estate)")
        verbose_name_plural = _("Immobilien (Real Estate)")

    def __str__(self):
        return f"{self.name} ({self.property_value})"


class FinancialStatusProxy(CustomUser):
    class Meta:
        proxy = True
        verbose_name = _("Mein Finanzstatus (Vorausgefüllt)")
        verbose_name_plural = _("Meine Finanzen (Schnelleingabe)")


class Loan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loans')
    name = models.CharField(_("Name"), max_length=100)
    provider = models.CharField(_("Provider / Bank"), max_length=100, blank=True)
    nominal_amount = models.DecimalField(_("Initial Loan Amount"), max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(_("Interest Rate (%)"), max_digits=5, decimal_places=2)
    interest_lock_end = models.DateField(_("Interest Lock End Date"), null=True, blank=True)
    monthly_installment = models.DecimalField(_("Monthly Installment"), max_digits=12, decimal_places=2)
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    allows_extra_repayment = models.BooleanField(_("Extra Repayment Possible"), default=False)

    class Meta:
        verbose_name = _("Loan / Debt")
        verbose_name_plural = _("Loans / Debts")

    def __str__(self):
        return f"{self.name} ({self.provider})"


class LoanExtraRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='extra_repayments')
    date = models.DateField(_("Date"))
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = _("Extra Repayment")
        verbose_name_plural = _("Extra Repayments")
        ordering = ['date']

class ImportFilter(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='import_filters')
    search_query = models.CharField(_("Search Query"), max_length=255, help_text=_("Separated by semicolon, e.g. EDEKA;REWE"))
    target_name = models.CharField(_("Target Name"), max_length=100, help_text=_("e.g. Lebensmitteleinkäufe"))
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
