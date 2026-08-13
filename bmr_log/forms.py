from django import forms
from django.contrib.auth import get_user_model

from masters.models import Area, AreaType, Product

from .models import BatchType, BMRIssuanceEntry

User = get_user_model()


class DateInput(forms.DateInput):
    input_type = 'date'


class IssueBMRForm(forms.ModelForm):
    class Meta:
        model = BMRIssuanceEntry
        fields = [
            'batch_no', 'batch_type', 'process_order_no', 'product', 'master_document_no',
            'production_block', 'issued_to', 'remarks',
        ]
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(active=True)
        self.fields['production_block'].queryset = Area.objects.filter(
            area_type=AreaType.BLOCK, active=True
        )
        self.fields['issued_to'].queryset = User.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'username'
        )

    def clean_batch_no(self):
        # Upper-cased before the uniqueness / format check so a case-only
        # difference (e.g. "cm260001" vs "CM260001") can't sneak past the
        # "must not repeat" rule as two distinct values.
        value = self.cleaned_data['batch_no'].strip().upper()
        if ' ' in value:
            raise forms.ValidationError('Batch No must not contain spaces.')
        return value

    def clean_process_order_no(self):
        # Numeric only, no spaces — belt-and-braces alongside the model field's
        # RegexValidator, since a raised ValidationError here reports against
        # this specific field instead of a generic non-field error.
        value = self.cleaned_data['process_order_no'].strip()
        if not value.isdigit():
            raise forms.ValidationError('Process Order No must be numeric only, with no spaces.')
        return value


class EntryFilterForm(forms.Form):
    batch_type = forms.ChoiceField(choices=[('', 'Any type')] + BatchType.choices, required=False)
    product = forms.ModelChoiceField(queryset=Product.objects.filter(active=True), required=False)
    date_from = forms.DateField(required=False, widget=DateInput())
    date_to = forms.DateField(required=False, widget=DateInput())
