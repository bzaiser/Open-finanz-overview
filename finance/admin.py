from django.contrib import admin
from .models import Category, CashFlowSource, Asset, OneTimeEvent, Pension, FinancialStatusProxy, PhysicalAsset, RealEstate, Loan, LoanExtraRepayment

admin.site.site_header = "Finanzplan Admin"
admin.site.index_title = "Finanzplan Admin"

class BaseOwnedModelAdmin(admin.ModelAdmin):
    """
    Base Admin class that enforces tenant isolation:
    - Non-superusers only see their own objects.
    - Non-superusers have the 'user' field hidden and autofilled to request.user.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def get_exclude(self, request, obj=None):
        exclude = super().get_exclude(request, obj) or []
        if not request.user.is_superuser:
            if 'user' not in exclude:
                exclude = list(exclude) + ['user']
        return exclude

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'user', None) is None:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

    def get_list_filter(self, request):
        """Remove 'user' from filters for standard users."""
        filters = super().get_list_filter(request)
        if not request.user.is_superuser and filters:
            return tuple(f for f in filters if f != 'user')
        return filters

@admin.register(Pension)
class PensionAdmin(BaseOwnedModelAdmin):
    list_display = ('provider', 'user', 'current_value', 'monthly_contribution', 'expected_payout_at_retirement', 'is_indexed', 'contribution_end_date', 'start_payout_date')
    list_editable = ('is_indexed',)
    search_fields = ('provider', 'user__username')
    list_filter = ('user',)

from django import forms

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
        }

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = ('name', 'slug', 'color', 'is_system')
    prepopulated_fields = {'slug': ('name',)}

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)

import datetime
import calendar
from django.utils.translation import gettext_lazy as _

@admin.action(description=_("Auswahl duplizieren & Datum hochzählen"))
def duplicate_and_increment_cashflow(modeladmin, request, queryset):
    count = 0
    for obj in queryset:
        obj.pk = None  # Duplicate record
        
        def add_months(sourcedate, months):
            if not sourcedate: return None
            month = sourcedate.month - 1 + months
            year = int(sourcedate.year + month // 12)
            month = month % 12 + 1
            day = min(sourcedate.day, calendar.monthrange(year, month)[1])
            return datetime.date(year, month, day)

        def add_years(sourcedate, years):
            if not sourcedate: return None
            try:
                return sourcedate.replace(year=sourcedate.year + years)
            except ValueError:
                # Handle leap years (Feb 29)
                return sourcedate.replace(year=sourcedate.year + years, day=28)
                
        if obj.frequency == 'yearly':
            obj.start_date = add_years(obj.start_date, 1)
            obj.end_date = add_years(obj.end_date, 1)
        elif obj.frequency == 'monthly':
            obj.start_date = add_months(obj.start_date, 1)
            obj.end_date = add_months(obj.end_date, 1)
            
        obj.save()
        count += 1
    
    modeladmin.message_user(request, f"{count} Datensätze erfolgreich dupliziert und aktualisiert.")

class YearListFilter(admin.SimpleListFilter):
    title = _('Jahr')
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        # Hole alle verwendeten Jahre aus der Datenbank, absteigend sortiert
        qs = model_admin.get_queryset(request)
        dates = qs.values_list('start_date', flat=True)
        years = set([d.year for d in dates if d])
        return [(str(y), str(y)) for y in sorted(years, reverse=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(start_date__year=self.value())
        return queryset

class CashFlowSourceInline(admin.TabularInline):
    model = CashFlowSource
    extra = 3  # Zeige 3 leere Zeilen für neue Einträge an
    fields = ('name', 'value', 'category', 'is_income', 'frequency', 'is_inflation_adjusted', 'start_date', 'end_date')
    classes = ['collapse']

class AssetInline(admin.TabularInline):
    model = Asset
    extra = 1
    fields = ('name', 'value', 'growth_rate', 'interest_teaser_rate', 'interest_teaser_until', 'withdrawal_amount', 'withdrawal_start_date')

    classes = ['collapse']

class OneTimeEventInline(admin.TabularInline):
    model = OneTimeEvent
    extra = 1
    fields = ('name', 'value', 'date', 'description')
    classes = ['collapse']

class PensionInline(admin.TabularInline):
    model = Pension
    extra = 1
    fields = ('provider', 'current_value', 'monthly_contribution', 'contribution_end_date', 'expected_payout_at_retirement', 'is_indexed', 'growth_rate', 'start_payout_date')
    classes = ['collapse']

class PhysicalAssetInline(admin.TabularInline):
    model = PhysicalAsset
    extra = 1
    fields = ('name', 'value', 'appreciation_rate', 'location', 'storage_costs_monthly', 'is_sold')
    classes = ['collapse']

class RealEstateInline(admin.TabularInline):
    model = RealEstate
    extra = 1
    fields = ('name', 'property_value', 'appreciation_rate', 'location', 'current_tenant', 'rental_income_monthly', 'maintenance_costs_monthly', 'ancillary_costs_monthly', 'is_sold')
    classes = ['collapse']

class LoanInline(admin.TabularInline):
    model = Loan
    extra = 1
    fields = ('name', 'provider', 'nominal_amount', 'interest_rate', 'monthly_installment', 'start_date', 'end_date', 'allows_extra_repayment')
    classes = ['collapse']

@admin.register(FinancialStatusProxy)
class FinancialStatusAdmin(admin.ModelAdmin):
    inlines = [CashFlowSourceInline, AssetInline, OneTimeEventInline, PensionInline, PhysicalAssetInline, RealEstateInline, LoanInline]
    fieldsets = (
        (None, {'fields': ('username',)}),
    )
    list_display = ('username', 'email', 'is_staff')
    
    def get_queryset(self, request):
        # Zeige nur den eigenen User an (außer für Superuser, die alles sehen können)
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(id=request.user.id)

    def has_add_permission(self, request):
        return False # User werden hier nicht neu angelegt

    def has_delete_permission(self, request, obj=None):
        return False # User werden hier nicht gelöscht

@admin.register(CashFlowSource)
class CashFlowSourceAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'value', 'category', 'is_income', 'frequency', 'start_date', 'end_date')
    list_editable = ('value', 'category', 'is_income', 'frequency', 'start_date', 'end_date')
    list_filter = (YearListFilter, 'is_income', 'frequency', 'user', 'category')
    search_fields = ('name',)
    actions = [duplicate_and_increment_cashflow]

@admin.register(Asset)
class AssetAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'value', 'growth_rate', 'interest_teaser_rate', 'interest_teaser_until', 'withdrawal_amount', 'withdrawal_start_date')

    list_filter = ('user',)
    search_fields = ('name',)
    list_editable = ('value', 'growth_rate', 'interest_teaser_rate', 'interest_teaser_until', 'withdrawal_amount', 'withdrawal_start_date')


@admin.register(OneTimeEvent)
class OneTimeEventAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'value', 'date')
    list_filter = ('user',)
    search_fields = ('name',)

@admin.register(PhysicalAsset)
class PhysicalAssetAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'value', 'appreciation_rate', 'storage_costs_monthly', 'is_sold', 'sale_date')
    list_filter = ('user', 'is_sold')
    search_fields = ('name',)
    list_editable = ('value', 'appreciation_rate', 'storage_costs_monthly', 'is_sold', 'sale_date')

@admin.register(RealEstate)
class RealEstateAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'property_value', 'appreciation_rate', 'rental_income_monthly', 'is_sold', 'sale_date')
    list_filter = ('user', 'is_sold')
    search_fields = ('name',)
    list_editable = ('property_value', 'appreciation_rate', 'rental_income_monthly', 'is_sold', 'sale_date')

class LoanExtraRepaymentInline(admin.TabularInline):
    model = LoanExtraRepayment
    extra = 1

@admin.register(Loan)
class LoanAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'provider', 'nominal_amount', 'interest_rate', 'monthly_installment', 'start_date', 'end_date')
    list_filter = ('user', 'provider')
    search_fields = ('name', 'provider')
    inlines = [LoanExtraRepaymentInline]

