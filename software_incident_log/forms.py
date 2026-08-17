from django import forms

from masters.models import ComputerizedSystem

from .models import IncidentStatus, SoftwareIncidentEntry


class DateInput(forms.DateInput):
    input_type = 'date'


class EntryFilterForm(forms.Form):
    system = forms.ModelChoiceField(
        queryset=ComputerizedSystem.objects.filter(active=True), required=False,
        label='Computerized System',
    )
    date_from = forms.DateField(required=False, widget=DateInput(), label='Logged From')
    date_to = forms.DateField(required=False, widget=DateInput(), label='Logged To')


class LogIncidentForm(forms.Form):
    incident_no = forms.CharField(label='Incident No', max_length=20)
    system = forms.ModelChoiceField(
        queryset=ComputerizedSystem.objects.filter(active=True),
        label='Name of the Computerized System',
    )
    description = forms.CharField(
        label='Brief Description of Issue', widget=forms.Textarea(attrs={'rows': 4}),
    )

    def clean_incident_no(self):
        value = self.cleaned_data['incident_no'].strip()
        if SoftwareIncidentEntry.objects.filter(incident_no=value).exists():
            raise forms.ValidationError('This Incident No has already been used.')
        return value


class SelectSystemForm(forms.Form):
    system = forms.ModelChoiceField(
        queryset=ComputerizedSystem.objects.filter(active=True),
        label='Name of the Computerized System',
    )


class SelectIncidentForm(forms.Form):
    incident = forms.ModelChoiceField(
        queryset=SoftwareIncidentEntry.objects.none(),
        label='Open Incident', empty_label='Select an open incident',
    )

    def __init__(self, *args, system=None, **kwargs):
        super().__init__(*args, **kwargs)
        open_incidents = SoftwareIncidentEntry.objects.filter(
            status=IncidentStatus.OPEN, system=system,
        ).order_by('-created_at')
        self.fields['incident'].queryset = open_incidents
        self.fields['incident'].label_from_instance = (
            lambda obj: f'{obj.incident_no} — {obj.description[:40]}'
        )


class CloseoutForm(forms.ModelForm):
    class Meta:
        model = SoftwareIncidentEntry
        fields = ['category', 'validation_required']

    def clean(self):
        cleaned_data = super().clean()
        for field in self.Meta.fields:
            if not cleaned_data.get(field):
                self.add_error(field, 'This field is required to close out the incident.')
        return cleaned_data
