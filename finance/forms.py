from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

class BankImportForm(forms.Form):
    file = forms.FileField(
        label=_("Select Excel file"),
        help_text=_("Select an Excel file (.xlsx or .xls) with your bank transactions."),
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'})
    )


from .models import CashFlowSource, Category

class CashFlowSourceForm(forms.ModelForm):
    class Meta:
        model = CashFlowSource
        fields = [
            'name', 'value', 'is_income', 'frequency', 'owner_role',
            'category', 'start_date', 'end_date',
            'is_inflation_adjusted', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Salary, Rent, Subscription')}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'is_income': forms.Select(choices=[(True, _('Income')), (False, _('Expense'))], attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'owner_role': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_inflation_adjusted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Optional notes...')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].empty_label = _('-- Select Category --')
        self.fields['owner_role'].required = False

    def clean_owner_role(self):
        return self.cleaned_data.get('owner_role') or 'primary'


from .models import Pension

class PensionForm(forms.ModelForm):
    class Meta:
        model = Pension
        fields = [
            'provider', 'owner_role', 'pension_type', 'payout_type', 'current_value', 'monthly_contribution', 'growth_rate',
            'pension_points', 'point_value', 'gross_payout_amount', 'social_deduction_rate', 'disability_pension_net',
            'expected_payout_at_retirement', 'retirement_age', 'target_pension_payout',
            'contribution_end_date', 'start_payout_date', 'is_indexed', 'notes'
        ]
        widgets = {
            'provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Statutory Pension, Allianz Riester')}),
            'owner_role': forms.Select(attrs={'class': 'form-select'}),
            'pension_type': forms.Select(attrs={'class': 'form-select'}),
            'payout_type': forms.Select(attrs={'class': 'form-select'}),
            'current_value': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'monthly_contribution': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'growth_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'pension_points': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.0001'}),
            'point_value': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'gross_payout_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'social_deduction_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'disability_pension_net': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'expected_payout_at_retirement': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'retirement_age': forms.NumberInput(attrs={'class': 'form-control font-monospace'}),
            'target_pension_payout': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'contribution_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_payout_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_indexed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner_role'].required = False

    def clean_owner_role(self):
        return self.cleaned_data.get('owner_role') or 'primary'


from .models import RealEstate, Loan, LoanExtraRepayment, PropertyComponent, PropertyDocument

class RealEstateForm(forms.ModelForm):
    class Meta:
        model = RealEstate
        fields = [
            'name', 'property_value', 'appreciation_rate', 'location',
            'current_tenant', 'rental_income_monthly', 'maintenance_costs_monthly',
            'ancillary_costs_monthly', 'construction_year', 'living_space_sqm',
            'current_maintenance_reserve', 'monthly_maintenance_allocation',
            'building_share_percent', 'depreciation_rate_percent', 'is_rental_property',
            'acquisition_date', 'is_sold', 'sale_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Downtown Apartment, Multi-Family Home')}),
            'property_value': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'appreciation_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Main Street 12, Berlin')}),
            'current_tenant': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. John Doe')}),
            'rental_income_monthly': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'maintenance_costs_monthly': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'ancillary_costs_monthly': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'construction_year': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'placeholder': '1995'}),
            'living_space_sqm': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'placeholder': '85.00'}),
            'current_maintenance_reserve': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'placeholder': '5000.00'}),
            'monthly_maintenance_allocation': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'placeholder': '150.00'}),
            'building_share_percent': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.1', 'placeholder': '70.0'}),
            'depreciation_rate_percent': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'placeholder': '2.00'}),
            'is_rental_property': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acquisition_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sale_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_sold': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            'name', 'provider', 'owner_role', 'loan_type', 'account_number', 'nominal_amount',
            'interest_rate', 'effective_interest_rate', 'initial_repayment_rate',
            'special_repayment_rate', 'monthly_installment', 'start_date', 'end_date',
            'interest_lock_end', 'real_estate', 'allows_extra_repayment', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Bank Mortgage, Annuity Loan')}),
            'provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Sparkasse, ING, DKB')}),
            'owner_role': forms.Select(attrs={'class': 'form-select'}),
            'loan_type': forms.Select(attrs={'class': 'form-select'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control font-monospace', 'placeholder': _('e.g. Loan No. 12345678')}),
            'nominal_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'effective_interest_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'initial_repayment_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'special_repayment_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'monthly_installment': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'interest_lock_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'real_estate': forms.Select(attrs={'class': 'form-select'}),
            'allows_extra_repayment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['real_estate'].queryset = RealEstate.objects.filter(user=user).order_by('name')
        self.fields['real_estate'].empty_label = _('-- No Real Estate (Unsecured Loan) --')
        self.fields['owner_role'].required = False

    def clean_owner_role(self):
        return self.cleaned_data.get('owner_role') or 'joint'


class LoanExtraRepaymentForm(forms.ModelForm):
    class Meta:
        model = LoanExtraRepayment
        fields = ['loan', 'date', 'amount']
        widgets = {
            'loan': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['loan'].queryset = Loan.objects.filter(user=user).order_by('name')
        self.fields['loan'].empty_label = _('-- Select Loan --')


class PropertyComponentForm(forms.ModelForm):
    class Meta:
        model = PropertyComponent
        fields = [
            'real_estate', 'component_type', 'name', 'installation_year',
            'expected_lifespan', 'estimated_cost', 'condition', 'notes'
        ]
        widgets = {
            'real_estate': forms.Select(attrs={'class': 'form-select'}),
            'component_type': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Gas Heating Buderus, Double Glazed Windows')}),
            'installation_year': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'placeholder': '2015'}),
            'expected_lifespan': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'placeholder': '20'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'placeholder': '15000.00'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Optional notes on condition or manufacturer...')}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['real_estate'].queryset = RealEstate.objects.filter(user=user).order_by('name')
        self.fields['real_estate'].empty_label = _('-- Select Real Estate --')


class PropertyDocumentForm(forms.ModelForm):
    class Meta:
        model = PropertyDocument
        fields = [
            'real_estate', 'title', 'category', 'file', 'date', 'amount', 'notes'
        ]
        widgets = {
            'real_estate': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Purchase Contract, Heating Invoice 2024')}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01', 'placeholder': '0.00'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Optional notes on this document...')}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['real_estate'].queryset = RealEstate.objects.filter(user=user).order_by('name')
        self.fields['real_estate'].empty_label = _('-- Select Real Estate --')


from .models import Asset, PhysicalAsset, AssetSnapshot, InsurancePolicy

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'name', 'asset_type', 'institution', 'isin_ticker', 'value', 'growth_rate',
            'monthly_savings_amount', 'is_emergency_fund', 'interest_teaser_rate',
            'interest_teaser_until', 'withdrawal_amount', 'withdrawal_start_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. DKB Giro, Trade Republic Depot, Bitcoin Wallet')}),
            'asset_type': forms.Select(attrs={'class': 'form-select'}),
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. ING, DKB, Scalable, Bison')}),
            'isin_ticker': forms.TextInput(attrs={'class': 'form-control font-monospace', 'placeholder': _('e.g. IE00B4L5Y983, BTC')}),
            'value': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'growth_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'monthly_savings_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'is_emergency_fund': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'interest_teaser_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'interest_teaser_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'withdrawal_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'withdrawal_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['growth_rate'].required = False
        self.fields['monthly_savings_amount'].required = False
        self.fields['withdrawal_amount'].required = False
        if self.is_bound:
            for optional_modal_field in (
                'interest_teaser_rate',
                'interest_teaser_until',
                'withdrawal_amount',
                'withdrawal_start_date',
            ):
                if optional_modal_field not in self.data:
                    self.fields.pop(optional_modal_field, None)

    def clean_growth_rate(self):
        val = self.cleaned_data.get('growth_rate')
        return Decimal('0.00') if val is None else val

    def clean_monthly_savings_amount(self):
        val = self.cleaned_data.get('monthly_savings_amount')
        return Decimal('0.00') if val is None else val

    def clean_withdrawal_amount(self):
        val = self.cleaned_data.get('withdrawal_amount')
        return Decimal('0.00') if val is None else val

class PhysicalAssetForm(forms.ModelForm):
    class Meta:
        model = PhysicalAsset
        fields = [
            'name', 'value', 'appreciation_rate', 'location', 'storage_costs_monthly',
            'acquisition_date', 'sale_date', 'is_sold'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Goldmünzen Krügerrand, Rolex Submariner, Oldtimer Porsche 911')}),
            'value': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'appreciation_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Banktresor, Tresor daheim')}),
            'storage_costs_monthly': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'acquisition_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sale_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_sold': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class InsurancePolicyForm(forms.ModelForm):
    class Meta:
        model = InsurancePolicy
        fields = [
            'name', 'provider', 'policy_number', 'insurance_type', 'insured_person',
            'premium_amount', 'payment_frequency', 'linked_cash_flow', 'include_in_cashflow',
            'coverage_lump_sum', 'coverage_monthly_payout', 'waiting_period_months',
            'payout_duration_months', 'start_date', 'end_date', 'is_active', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('z. B. Privathaftpflicht Familie, BU-Schutz')}),
            'provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('z. B. HUK24, Allianz, Hannoversche')}),
            'policy_number': forms.TextInput(attrs={'class': 'form-control font-monospace'}),
            'insurance_type': forms.Select(attrs={'class': 'form-select'}),
            'insured_person': forms.Select(attrs={'class': 'form-select'}),
            'premium_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'payment_frequency': forms.Select(attrs={'class': 'form-select'}),
            'linked_cash_flow': forms.Select(attrs={'class': 'form-select'}),
            'include_in_cashflow': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'coverage_lump_sum': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'coverage_monthly_payout': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'waiting_period_months': forms.NumberInput(attrs={'class': 'form-control font-monospace'}),
            'payout_duration_months': forms.NumberInput(attrs={'class': 'form-control font-monospace'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['linked_cash_flow'].queryset = CashFlowSource.objects.filter(
                user=user, is_income=False
            ).order_by('name')
        self.fields['linked_cash_flow'].empty_label = _('-- Keine Verknüpfung (Beitrag separat zählen) --')
        self.fields['linked_cash_flow'].required = False
        self.fields['waiting_period_months'].required = False
        self.fields['include_in_cashflow'].required = False
        self.fields['is_active'].required = False

    def clean_waiting_period_months(self):
        return self.cleaned_data.get('waiting_period_months') or 0
