from django import forms
from django.utils.translation import gettext_lazy as _

class BankImportForm(forms.Form):
    file = forms.FileField(
        label=_("Excel-Datei auswählen"),
        help_text=_("Wähle eine Excel-Datei (.xlsx oder .xls) mit deinen Bankbuchungen aus."),
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'})
    )
