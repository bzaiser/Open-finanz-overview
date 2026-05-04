from django import forms
from django.utils.translation import gettext_lazy as _

class BankImportForm(forms.Form):
    file = forms.FileField(
        label=_("Select Excel file"),
        help_text=_("Select an Excel file (.xlsx or .xls) with your bank transactions."),
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'})
    )
