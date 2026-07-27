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

