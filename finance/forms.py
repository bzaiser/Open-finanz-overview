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
            'name', 'value', 'is_income', 'frequency', 
            'category', 'start_date', 'end_date', 
            'is_inflation_adjusted', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Salary, Rent, Subscription')}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'is_income': forms.Select(choices=[(True, _('Income')), (False, _('Expense'))], attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
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


from .models import Pension

class PensionForm(forms.ModelForm):
    class Meta:
        model = Pension
        fields = [
            'provider', 'pension_type', 'pension_points', 'point_value',
            'gross_payout_amount', 'social_deduction_rate', 'expected_payout_at_retirement',
            'retirement_age', 'target_pension_payout',
            'monthly_contribution', 'contribution_end_date', 'start_payout_date',
            'is_indexed', 'notes'
        ]
        widgets = {
            'provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. Statutory Pension, Allianz Riester')}),
            'pension_type': forms.Select(attrs={'class': 'form-select'}),
            'pension_points': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.0001'}),
            'point_value': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'gross_payout_amount': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'social_deduction_rate': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'expected_payout_at_retirement': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'monthly_contribution': forms.NumberInput(attrs={'class': 'form-control font-monospace', 'step': '0.01'}),
            'contribution_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_payout_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_indexed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

