from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Category, CashFlowSource, Asset, OneTimeEvent, Pension, FinancialStatusProxy, PhysicalAsset, RealEstate, Loan, LoanExtraRepayment, AssetSnapshot
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

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
        # Auto-assign user only for regular users (who don't see the field)
        if not request.user.is_superuser and getattr(obj, 'user', None) is None:
            obj.user = request.user
        
        # Save snapshot if value changed
        val_field = getattr(self, 'snapshot_value_field', None)
        if val_field and change:
            try:
                old_obj = obj.__class__.objects.get(pk=obj.pk)
                old_val = getattr(old_obj, val_field)
                new_val = getattr(obj, val_field)
                if old_val != new_val:
                    AssetSnapshot.objects.update_or_create(
                        user=obj.user, # Use the object's user
                        content_type=ContentType.objects.get_for_model(obj),
                        object_id=obj.pk,
                        date=timezone.now().date(),
                        defaults={'value': new_val}
                    )
            except:
                pass

        super().save_model(request, obj, form, change)
        
        # Capture snapshot for new objects after they have a PK
        if val_field and not change:
            AssetSnapshot.objects.update_or_create(
                user=obj.user, # Use the object's user
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.pk,
                date=timezone.now().date(),
                defaults={'value': getattr(obj, val_field)}
            )

    def save_formset(self, request, form, formset, change):
        """Ensure inlines (like AssetSnapshots) get the correct user from the parent."""
        instances = formset.save(commit=False)
        for instance in instances:
            if hasattr(instance, 'user') and not getattr(instance, 'user_id', None):
                instance.user = formset.instance.user
            instance.save()
        formset.save_m2m()

    def get_list_filter(self, request):
        """Remove 'user' from filters for standard users."""
        filters = super().get_list_filter(request)
        if not request.user.is_superuser and filters:
            return tuple(f for f in filters if f != 'user')
        return filters

class AssetSnapshotInline(GenericTabularInline):
    model = AssetSnapshot
    extra = 0
    fields = ('date', 'value', 'notes')
    classes = ['collapse']

@admin.register(Pension)
class PensionAdmin(BaseOwnedModelAdmin):
    list_display = ('provider', 'user', 'current_value', 'monthly_contribution', 'expected_payout_at_retirement', 'is_indexed', 'contribution_end_date', 'start_payout_date')
    list_editable = ('is_indexed',)
    search_fields = ('provider', 'user__username')
    list_filter = ('user',)
    list_select_related = ('user',)
    inlines = [AssetSnapshotInline]
    snapshot_value_field = 'current_value'

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
    fields = ('name', 'property_value', 'appreciation_rate', 'location', 'current_tenant', 'rental_income_monthly', 'maintenance_costs_monthly', 'ancillary_costs_monthly', 'acquisition_date', 'sale_date', 'is_sold')
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
    list_select_related = ('category', 'user')
    search_fields = ('name',)
    actions = [duplicate_and_increment_cashflow]

@admin.register(Asset)
class AssetAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'value', 'growth_rate', 'interest_teaser_rate', 'interest_teaser_until', 'withdrawal_amount', 'withdrawal_start_date')

    list_filter = ('user',)
    list_select_related = ('user',)
    search_fields = ('name',)
    list_editable = ('value', 'growth_rate', 'interest_teaser_rate', 'interest_teaser_until', 'withdrawal_amount', 'withdrawal_start_date')
    inlines = [AssetSnapshotInline]
    snapshot_value_field = 'value'


@admin.register(OneTimeEvent)
class OneTimeEventAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'value', 'date')
    list_filter = ('user',)
    list_select_related = ('user',)
    search_fields = ('name',)

@admin.register(PhysicalAsset)
class PhysicalAssetAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'value', 'appreciation_rate', 'storage_costs_monthly', 'is_sold', 'sale_date')
    list_filter = ('user', 'is_sold')
    list_select_related = ('user',)
    search_fields = ('name',)
    list_editable = ('value', 'appreciation_rate', 'storage_costs_monthly', 'is_sold', 'sale_date')
    inlines = [AssetSnapshotInline]
    snapshot_value_field = 'value'

@admin.register(RealEstate)
class RealEstateAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'property_value', 'appreciation_rate', 'rental_income_monthly', 'acquisition_date', 'sale_date', 'is_sold')
    list_filter = ('user', 'is_sold')
    list_select_related = ('user',)
    search_fields = ('name',)
    list_editable = ('property_value', 'appreciation_rate', 'rental_income_monthly', 'acquisition_date', 'sale_date', 'is_sold')
    inlines = [AssetSnapshotInline]
    snapshot_value_field = 'property_value'

class LoanExtraRepaymentInline(admin.TabularInline):
    model = LoanExtraRepayment
    extra = 1

@admin.register(Loan)
class LoanAdmin(BaseOwnedModelAdmin):
    list_display = ('name', 'user', 'provider', 'nominal_amount', 'interest_rate', 'monthly_installment', 'start_date', 'end_date')
    list_filter = ('user', 'provider')
    list_select_related = ('user',)
    search_fields = ('name', 'provider')
    inlines = [LoanExtraRepaymentInline, AssetSnapshotInline]

class AssetSnapshotForm(forms.ModelForm):
    asset_choice = forms.ChoiceField(
        label=_("Asset/Object"),
        required=False,
        help_text=mark_safe(_("Select the concrete asset to create a snapshot for. This will automatically fill the Type and ID fields.") + """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const assetSelect = document.getElementById('id_asset_choice');
            const ctSelect = document.getElementById('id_content_type');
            const objIdInput = document.getElementById('id_object_id');
            
            console.log("Asset Snapshot Helper initialized");
            console.log("Elements found:", !!assetSelect, !!ctSelect, !!objIdInput);

            if (assetSelect && ctSelect && objIdInput) {
                assetSelect.addEventListener('change', function() {
                    const mappingRaw = this.getAttribute('data-mapping');
                    console.log("Selection changed:", this.value);
                    console.log("Mapping raw:", mappingRaw);
                    
                    const mapping = JSON.parse(mappingRaw || '{}');
                    const val = this.value;
                    if (val && val.includes('-')) {
                        const parts = val.split('-');
                        const prefix = parts[0];
                        const id = parts[1];
                        
                        console.log("Prefix:", prefix, "ID:", id, "CT:", mapping[prefix]);
                        
                        if (mapping[prefix]) {
                            ctSelect.value = mapping[prefix];
                            objIdInput.value = id;
                            console.log("Set CT to", ctSelect.value, "and ID to", objIdInput.value);
                        }
                    }
                });
            }
        });
        </script>
        """)
    )

    class Meta:
        model = AssetSnapshot
        fields = ['asset_choice', 'user', 'date', 'value', 'notes', 'content_type', 'object_id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = None
        if hasattr(self, 'request') and self.request.user:
            user = self.request.user
        elif self.instance and self.instance.user_id:
            user = self.instance.user

        if user:
            choices = [('', '---------')]
            
            # Accounts (Asset model)
            for obj in Asset.objects.filter(user=user):
                choices.append((f"asset-{obj.id}", f"{obj.name} ({_('Konto/Anlage')})"))
            
            # Physical Assets
            for obj in PhysicalAsset.objects.filter(user=user):
                choices.append((f"pa-{obj.id}", f"{obj.name} ({_('Sachwert')})"))
                
            # Real Estate
            for obj in RealEstate.objects.filter(user=user):
                choices.append((f"re-{obj.id}", f"{obj.name} ({_('Immobilie')})"))
                
            # Pensions
            for obj in Pension.objects.filter(user=user):
                choices.append((f"pen-{obj.id}", f"{obj.provider} ({_('Rente')})"))
                
            # Loans
            for obj in Loan.objects.filter(user=user):
                choices.append((f"loan-{obj.id}", f"{obj.name} ({_('Kredit')})"))
                
            self.fields['asset_choice'].choices = choices
            
            # Set initial value if editing
            if self.instance.pk and self.instance.content_type:
                model_name = self.instance.content_type.model
                prefix = ""
                if model_name == 'asset': prefix = "asset"
                elif model_name == 'physicalasset': prefix = "pa"
                elif model_name == 'realestate': prefix = "re"
                elif model_name == 'pension': prefix = "pen"
                elif model_name == 'loan': prefix = "loan"
                
                if prefix:
                    self.initial['asset_choice'] = f"{prefix}-{self.instance.object_id}"

    def clean(self):
        cleaned_data = super().clean()
        asset_choice = cleaned_data.get('asset_choice')
        
        if asset_choice:
            prefix, obj_id = asset_choice.split('-')
            obj_id = int(obj_id)
            
            model_map = {
                'asset': Asset,
                'pa': PhysicalAsset,
                're': RealEstate,
                'pen': Pension,
                'loan': Loan,
            }
            
            model_class = model_map.get(prefix)
            if model_class:
                cleaned_data['content_type'] = ContentType.objects.get_for_model(model_class)
                cleaned_data['object_id'] = obj_id
                
        return cleaned_data

@admin.register(AssetSnapshot)
class AssetSnapshotAdmin(BaseOwnedModelAdmin):
    form = AssetSnapshotForm
    list_display = ('date', 'content_object', 'value', 'user')
    list_filter = ('date', 'user')
    search_fields = ('notes',)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        
        # Add mapping to JS
        mapping = {}
        for prefix, model_class in [('asset', Asset), ('pa', PhysicalAsset), ('re', RealEstate), ('pen', Pension), ('loan', Loan)]:
            mapping[prefix] = ContentType.objects.get_for_model(model_class).id
        
        import json
        form.base_fields['asset_choice'].widget.attrs['data-mapping'] = json.dumps(mapping)
        return form

    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.js',
            'admin/js/jquery.init.js',
        )
