from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import Category, CashFlowSource, Asset, OneTimeEvent, Pension, FinancialStatusProxy, PhysicalAsset, RealEstate, Loan, LoanExtraRepayment, AssetSnapshot
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

class CurrentUserDefaultFilter(admin.SimpleListFilter):
    title = _('Benutzer')
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        from core.models import CustomUser
        users = CustomUser.objects.filter(is_active=True).order_by('username')
        items = [('all', _('--- Alle Benutzer anzeigen ---'))]
        for u in users:
            label = f"{u.username} (Du)" if u.pk == request.user.pk else u.username
            items.append((str(u.pk), label))
        return items

    def choices(self, changelist):
        # Override choices to hide the default Django 'All' which has value None,
        # so that our explicit 'all' option behaves cleanly.
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == str(lookup) or (self.value() is None and lookup == 'all'),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
            }

    def queryset(self, request, queryset):
        val = self.value()
        if val == 'all':
            return queryset
        if val:
            return queryset.filter(user_id=val)
        # Default when opening the changelist without explicit ?user= query param
        if request.user.is_authenticated:
            return queryset.filter(user=request.user)
        return queryset


class BaseOwnedModelAdmin(admin.ModelAdmin):
    """
    Base Admin class that enforces user-scoped management:
    - Non-superusers only see their own objects.
    - Superusers default to seeing their own objects, with a filter to switch to other users or view all.
    - Non-superusers have the 'user' field hidden and autofilled to request.user.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(user=request.user)
        return qs

    def changelist_view(self, request, extra_context=None):
        if request.user.is_superuser and 'user' not in request.GET:
            # Superusers default to seeing all records, with a filter sidebar to select users
            q = request.GET.copy()
            q['user'] = 'all'
            request.GET = q
            request.META['QUERY_STRING'] = q.urlencode()
        return super().changelist_view(request, extra_context=extra_context)

    def get_exclude(self, request, obj=None):
        exclude = super().get_exclude(request, obj) or []
        if not request.user.is_superuser:
            if 'user' not in exclude:
                exclude = list(exclude) + ['user']
        return exclude

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser:
            clean_fieldsets = []
            for name, opts in fieldsets:
                flds = opts.get('fields', ())
                new_flds = []
                for f in flds:
                    if isinstance(f, (list, tuple)):
                        sub = [item for item in f if item != 'user']
                        if sub:
                            new_flds.append(tuple(sub) if isinstance(f, tuple) else sub)
                    elif f != 'user':
                        new_flds.append(f)
                if new_flds:
                    opts_copy = dict(opts)
                    opts_copy['fields'] = tuple(new_flds)
                    clean_fieldsets.append((name, opts_copy))
            return tuple(clean_fieldsets)
        return fieldsets

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
        
        # Determine the user to assign
        parent_obj = formset.instance
        # Default to parent object's user, or the parent itself if it's a user, 
        # or fallback to current request user
        assigned_user = getattr(parent_obj, 'user', None)
        if not assigned_user and isinstance(parent_obj, CustomUser):
            assigned_user = parent_obj
        if not assigned_user:
            assigned_user = request.user
            
        for instance in instances:
            if hasattr(instance, 'user') and not getattr(instance, 'user_id', None):
                instance.user = assigned_user
            instance.save()
            
        # Handle deletions (which commit=False misses)
        for obj in formset.deleted_objects:
            obj.delete()
            
        formset.save_m2m()

    def get_list_filter(self, request):
        """Apply CurrentUserDefaultFilter for superusers, hide user filter for standard users."""
        filters = super().get_list_filter(request) or ()
        if not request.user.is_superuser:
            return tuple(f for f in filters if f != 'user' and f != CurrentUserDefaultFilter)
        # Replace raw 'user' with CurrentUserDefaultFilter, or add it if not present
        new_filters = []
        has_user_filter = False
        for f in filters:
            if f == 'user' or f == CurrentUserDefaultFilter:
                new_filters.append(CurrentUserDefaultFilter)
                has_user_filter = True
            else:
                new_filters.append(f)
        if not has_user_filter:
            new_filters.append(CurrentUserDefaultFilter)
        return tuple(new_filters)

class AssetSnapshotInlineForm(forms.ModelForm):
    class Meta:
        model = AssetSnapshot
        fields = '__all__'
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 1, 'style': 'width: 400px;'}),
        }

class AssetSnapshotInline(GenericTabularInline):
    model = AssetSnapshot
    form = AssetSnapshotInlineForm
    extra = 0
    fields = ('date', 'value', 'expected_payout_net', 'disability_pension_net', 'pension_points', 'point_value', 'notes')
    classes = ['collapse']

    def get_fields(self, request, obj=None):
        fields = list(self.fields)
        if request.user.is_superuser:
            fields.insert(0, 'user')
        return fields

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if obj:
            user = getattr(obj, 'user', None)
            if not user and isinstance(obj, CustomUser):
                user = obj
            if user and 'user' in formset.form.base_fields:
                formset.form.base_fields['user'].initial = user
        return formset

class PensionAdminForm(forms.ModelForm):
    class Meta:
        model = Pension
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        is_statutory = instance and instance.pension_type == 'statutory'
        
        if is_statutory:
            self.fields['expected_payout_at_retirement'].label = _("Projected Net Monthly Pension (€)")
            self.fields['expected_payout_at_retirement'].help_text = _("Projected regular old-age pension ('Sollten bis zum Rentenbeginn Beiträge wie in den letzten 5 Jahren gezahlt werden...')")
        else:
            self.fields['expected_payout_at_retirement'].label = _("Expected Monthly Payout (€)")
            self.fields['expected_payout_at_retirement'].help_text = _("Expected monthly net payout at retirement from this private/capital pension.")

@admin.register(Pension)
class PensionAdmin(BaseOwnedModelAdmin):
    form = PensionAdminForm
    list_display = ('provider', 'pension_type', 'payout_type', 'user', 'pension_points', 'point_value', 'gross_payout_amount', 'social_deduction_rate', 'expected_payout_at_retirement', 'disability_pension_net', 'is_indexed', 'notes')
    list_editable = ('is_indexed',)
    search_fields = ('provider', 'user__username')
    list_filter = ('pension_type', 'payout_type', 'user')
    list_select_related = ('user',)
    inlines = [AssetSnapshotInline]

    fieldsets = (
        (None, {
            'fields': ('user', 'provider', 'pension_type', 'payout_type')
        }),
        (_('Capital & Contributions'), {
            'classes': ('pension-capital-group',),
            'fields': ('current_value', 'monthly_contribution', 'growth_rate')
        }),
        (_('Statutory Pension (Points & Deductions)'), {
            'classes': ('pension-statutory-group',),
            'fields': (
                ('pension_points', 'point_value'),
                ('gross_payout_amount', 'social_deduction_rate'),
                'disability_pension_net',
            )
        }),
        (_('Retirement Payout & Dates'), {
            'fields': (
                'expected_payout_at_retirement',
                ('retirement_age', 'target_pension_payout'),
                ('contribution_end_date', 'start_payout_date'),
                'is_indexed',
                'notes'
            )
        }),
    )

    def get_fieldsets(self, request, obj=None):
        pension_type = getattr(obj, 'pension_type', 'capital') if obj else 'capital'
        
        base_fields = ('user', 'provider', 'pension_type', 'payout_type') if request.user.is_superuser else ('provider', 'pension_type', 'payout_type')
        
        if pension_type == 'statutory':
            return (
                (None, {
                    'fields': base_fields
                }),
                (_('Statutory Pension (Points & Deductions)'), {
                    'fields': (
                        ('pension_points', 'point_value'),
                        ('gross_payout_amount', 'social_deduction_rate'),
                        'disability_pension_net',
                    )
                }),
                (_('Retirement Payout & Dates'), {
                    'fields': (
                        'expected_payout_at_retirement',
                        'growth_rate',
                        ('retirement_age', 'target_pension_payout'),
                        ('contribution_end_date', 'start_payout_date'),
                        'is_indexed',
                        'notes'
                    )
                }),
            )
        else:
            return (
                (None, {
                    'fields': base_fields
                }),
                (_('Capital & Contributions'), {
                    'fields': (
                        'current_value',
                        'monthly_contribution',
                        'growth_rate',
                    )
                }),
                (_('Retirement Payout & Dates'), {
                    'fields': (
                        'expected_payout_at_retirement',
                        ('contribution_end_date', 'start_payout_date'),
                        'is_indexed',
                        'notes'
                    )
                }),
            )

    class Media:
        js = ('js/admin_pension_calc.js',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # For statutory pensions, if user saved with points, record a rich snapshot
        if obj.pension_type == 'statutory' and (obj.pension_points or obj.expected_payout_at_retirement):
            snap_val = obj.expected_payout_at_retirement or Decimal('0.00')
            AssetSnapshot.objects.update_or_create(
                user=obj.user,
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.pk,
                date=timezone.now().date(),
                defaults={
                    'value': snap_val,
                    'pension_points': obj.pension_points,
                    'point_value': obj.point_value,
                    'expected_payout_net': obj.expected_payout_at_retirement,
                    'disability_pension_net': obj.disability_pension_net,
                }
            )
        elif obj.pension_type == 'capital' and obj.current_value:
            AssetSnapshot.objects.update_or_create(
                user=obj.user,
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.pk,
                date=timezone.now().date(),
                defaults={
                    'value': obj.current_value,
                    'expected_payout_net': obj.expected_payout_at_retirement,
                }
            )

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

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.append('is_system')
            if obj and obj.is_system:
                readonly.extend(['name', 'slug'])
        return readonly

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_system and not request.user.is_superuser:
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)

import datetime
import calendar
from django.utils.translation import gettext_lazy as _

@admin.action(description=_("Duplicate selection & increment date"))
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
    fields = ('name', 'value', 'category', 'is_income', 'frequency', 'template_id', 'is_inflation_adjusted', 'start_date', 'end_date')
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
    fields = ('provider', 'payout_type', 'current_value', 'monthly_contribution', 'contribution_end_date', 'expected_payout_at_retirement', 'is_indexed', 'growth_rate', 'start_payout_date')
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
    list_display = ('name', 'user', 'value', 'category', 'is_income', 'frequency', 'template_id', 'start_date', 'end_date')
    list_editable = ('value', 'category', 'is_income', 'frequency', 'start_date', 'end_date')
    list_filter = (YearListFilter, 'is_income', 'frequency', 'user', 'category')
    list_select_related = ('category', 'user')
    search_fields = ('name', 'template_id')
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
    list_display = ('date', 'content_object', 'value', 'expected_payout_net', 'pension_points', 'point_value', 'user')
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
