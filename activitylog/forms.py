from django import forms
from django.urls import reverse

from masters.models import Equipment, EquipmentState, EquipmentUsageType, Product

from . import rules
from .models import ActivityLogEntry, CleaningType, MaintenanceType, ProcessSubType

# Per-usage-type visible field sets for the dynamic Start Activity form — once
# the operator picks Equipment and then Usage (Process, Cleaning, Maintenance,
# Qualification), only that type's fields are offered, exactly as listed in
# the "fields to be entered to start" table. Every field is filled at start
# only; Stop Activity asks for nothing further.
#
# process_sub_type and maintenance_frequency/pm_process_order_no have a second
# layer of visibility handled in the template JS (equipment-type / maintenance
# type dependent) — being listed here only means "possibly visible for this
# usage type".
USAGE_TYPE_FIELDS = {
    'Process': ['product', 'batch_no', 'process_sub_type', 'remarks'],
    'Cleaning': ['cleaning_type', 'batch_no', 'cleaning_sop_no', 'remarks'],
    'Maintenance': [
        'equipment_maintenance_sop_no', 'maintenance_type', 'maintenance_frequency',
        'pm_process_order_no', 'remarks',
    ],
    'Qualification': ['qualification_protocol_no', 'remarks'],
}


def usage_type_field_map():
    """{usage_type_id (str): [field names] or None} for active usage types.

    None means "no mapping configured yet — show every field". Keys are strings
    because this is embedded as JSON and read back against a <select> value.
    """
    return {
        str(ut.id): USAGE_TYPE_FIELDS.get(ut.name)
        for ut in EquipmentUsageType.objects.filter(active=True)
    }


def equipment_context_map():
    """{equipment_id (str): {"code", "state", "state_label", "open_entry_url",
    "busy_no_entry", "next_actions"}}.

    Feeds the Start Activity page's JS so it can show the equipment's current
    status next to the picker, steer straight to stopping it if an activity is
    already in progress, and narrow the Usage Type / sub-activity choices down
    to only what's valid from its current status. "busy_no_entry" flags the
    data-inconsistency case: equipment showing a mid-activity status
    (rules.DURING_STATES) with no open entry to link to (state was set some
    other way, e.g. directly in admin).
    """
    open_entry_by_equipment = dict(
        ActivityLogEntry.objects.filter(equipment__active=True, end_date__isnull=True)
        .values_list('equipment_id', 'pk')
    )
    usage_type_ids = dict(EquipmentUsageType.objects.filter(active=True).values_list('name', 'id'))
    return {
        str(e.id): {
            'code': e.code,
            'state': e.state,
            'state_label': e.get_state_display(),
            'is_reactor': e.equipment_type.name == 'Reactor',
            'open_entry_url': (
                reverse('stop_activity', args=[open_entry_by_equipment[e.id]])
                if e.id in open_entry_by_equipment
                else None
            ),
            'busy_no_entry': (
                e.id not in open_entry_by_equipment and e.state in rules.DURING_STATES
            ),
            'next_actions': [
                {'usage_type_id': str(usage_type_ids[usage_type_name]), 'code': code, 'label': rule.label}
                for usage_type_name, code, rule in rules.next_actions_for_state(e.state)
                if usage_type_name in usage_type_ids
            ],
        }
        for e in Equipment.objects.filter(active=True).select_related('equipment_type')
    }


class DateInput(forms.DateInput):
    input_type = 'date'


class StartActivityForm(forms.ModelForm):
    class Meta:
        model = ActivityLogEntry
        # start_date/start_time are not user-entered — the view stamps them from
        # the server clock (IST) when the activity is started.
        fields = [
            'equipment',
            'usage_type',
            'cleaning_type',
            'product',
            'batch_no',
            'process_sub_type',
            'cleaning_sop_no',
            'equipment_maintenance_sop_no',
            'maintenance_type',
            'maintenance_frequency',
            'pm_process_order_no',
            'qualification_protocol_no',
            'remarks',
        ]
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipment'].queryset = Equipment.objects.filter(active=True)
        self.fields['usage_type'].queryset = EquipmentUsageType.objects.filter(active=True)
        self.fields['product'].queryset = Product.objects.filter(active=True)
        # REACTION is derived from the equipment's type, never operator-picked.
        self.fields['process_sub_type'].choices = [('', '---------')] + [
            choice for choice in ProcessSubType.choices if choice[0] != ProcessSubType.REACTION
        ]

    def clean(self):
        cleaned = super().clean()
        equipment = cleaned.get('equipment')
        usage_type = cleaned.get('usage_type')
        if not equipment or not usage_type:
            return cleaned

        if equipment.log_entries.filter(end_date__isnull=True).exists():
            self.add_error(
                'equipment',
                f'{equipment.code} already has an activity in progress. Stop it before starting a new one.',
            )
            return cleaned

        usage_type_name = usage_type.name

        if usage_type_name == 'Process':
            if equipment.equipment_type.name == 'Reactor':
                cleaned['process_sub_type'] = ProcessSubType.REACTION
            elif cleaned.get('process_sub_type') not in (
                ProcessSubType.OTHER_EQUIPMENT, ProcessSubType.HOLDING,
            ):
                self.add_error(
                    'process_sub_type',
                    'Select whether this is equipment use or holding of mother liquor / distilled solvent.',
                )
        elif usage_type_name == 'Cleaning':
            if not cleaned.get('cleaning_type'):
                self.add_error('cleaning_type', 'Select a type of cleaning.')
            elif cleaned['cleaning_type'] == CleaningType.Q:
                cleaned['batch_no'] = ''
                cleaned['cleaning_sop_no'] = ''
        elif usage_type_name == 'Maintenance':
            if not cleaned.get('maintenance_type'):
                self.add_error('maintenance_type', 'Select Breakdown / Repair or Preventive Maintenance.')
            elif cleaned['maintenance_type'] == MaintenanceType.BREAKDOWN:
                cleaned['maintenance_frequency'] = ''
                cleaned['pm_process_order_no'] = ''

        if self.errors:
            return cleaned

        code = rules.sub_activity_code_from_values(
            usage_type_name,
            process_sub_type=cleaned.get('process_sub_type', ''),
            cleaning_type=cleaned.get('cleaning_type', ''),
            maintenance_type=cleaned.get('maintenance_type', ''),
        )
        rule = rules.get_rule(usage_type_name, code)
        if rule is None:
            self.add_error(None, f'No activity rule is defined for {usage_type_name}.')
            return cleaned

        if equipment.state not in rule.allowed_prior_states:
            allowed = ', '.join(
                sorted(EquipmentState(s).label for s in rule.allowed_prior_states)
            )
            self.add_error(
                'equipment',
                f'{equipment.code} is currently "{equipment.get_state_display()}". '
                f'Starting {usage_type_name} ({rule.label}) requires status: {allowed}.',
            )
            return cleaned

        self.rule = rule
        return cleaned


class EntryFilterForm(forms.Form):
    equipment = forms.ModelChoiceField(
        queryset=Equipment.objects.filter(active=True), required=False
    )
    product = forms.ModelChoiceField(queryset=Product.objects.filter(active=True), required=False)
    status = forms.ChoiceField(
        choices=[('', 'Any status')] + ActivityLogEntry._meta.get_field('status').choices,
        required=False,
    )
    date_from = forms.DateField(required=False, widget=DateInput())
    date_to = forms.DateField(required=False, widget=DateInput())
