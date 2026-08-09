"""Activity Rules: what equipment status an Activity + Sub Activity requires to
start, what it shows while running, and what it leaves behind on completion.

Source: the "Activity rules" table (Activity / Sub Activity / Equipment Status
during activity / Equipment Status after completion / Rules for the status to
choose). Sub-activity codes for Cleaning reuse activitylog.models.CleaningType
values directly (A/B/Q/G) so there is exactly one enum for cleaning sub-type,
not two.
"""

from dataclasses import dataclass

from masters.models import EquipmentState

REACTION = 'REACTION'
OTHER_EQUIPMENT = 'OTHER_EQUIPMENT'
HOLDING = 'HOLDING'

BREAKDOWN = 'BREAKDOWN'
PREVENTIVE = 'PREVENTIVE'

QUALIFICATION = 'QUALIFICATION'


@dataclass(frozen=True)
class ActivityRule:
    label: str
    during_state: str
    after_state: str
    allowed_prior_states: frozenset


_PROCESS_PRIOR = frozenset(
    {
        EquipmentState.CLEANED_TYPE_A,
        EquipmentState.CLEANED_AND_QA_CERTIFIED,
        EquipmentState.CLEANED_AFTER_MAINTENANCE,
    }
)

_MAINTENANCE_PRIOR = frozenset(
    {
        EquipmentState.CLEANED_AND_QA_CERTIFIED,
        EquipmentState.CLEANED_AFTER_MAINTENANCE,
        EquipmentState.CLEANED_READY_FOR_QA,
    }
)

ACTIVITY_RULES = {
    ('Process', REACTION): ActivityRule(
        'Reaction (Reactor Only)',
        EquipmentState.IN_PROCESS,
        EquipmentState.TO_BE_CLEANED,
        _PROCESS_PRIOR,
    ),
    ('Process', OTHER_EQUIPMENT): ActivityRule(
        'Equipment Other Than Reactor',
        EquipmentState.IN_USE,
        EquipmentState.TO_BE_CLEANED,
        _PROCESS_PRIOR,
    ),
    ('Process', HOLDING): ActivityRule(
        'Holding of Mother Liquor / Distilled Solvent',
        EquipmentState.TO_BE_PRESERVED,
        EquipmentState.TO_BE_CLEANED,
        _PROCESS_PRIOR,
    ),
    ('Cleaning', 'A'): ActivityRule(
        'Type-A (Same Product)',
        EquipmentState.UNDER_CLEANING,
        EquipmentState.CLEANED_TYPE_A,
        frozenset({EquipmentState.TO_BE_CLEANED, EquipmentState.CLEANED_AND_QA_CERTIFIED}),
    ),
    ('Cleaning', 'B'): ActivityRule(
        'Type-B (Product Changeover)',
        EquipmentState.UNDER_CLEANING,
        EquipmentState.CLEANED_READY_FOR_QA,
        frozenset(
            {
                EquipmentState.TO_BE_CLEANED,
                EquipmentState.CLEANED_TYPE_A,
                EquipmentState.CLEANED_AND_QA_CERTIFIED,
                EquipmentState.CLEANED_AFTER_MAINTENANCE,
                EquipmentState.NOT_IN_USE,
            }
        ),
    ),
    ('Cleaning', 'Q'): ActivityRule(
        'QA Certification',
        EquipmentState.UNDER_QA_CERTIFICATION,
        EquipmentState.CLEANED_AND_QA_CERTIFIED,
        frozenset({EquipmentState.CLEANED_READY_FOR_QA}),
    ),
    ('Cleaning', 'G'): ActivityRule(
        'Type-G (After Maintenance)',
        EquipmentState.UNDER_CLEANING,
        EquipmentState.CLEANED_AFTER_MAINTENANCE,
        frozenset({EquipmentState.UNDER_MAINTENANCE}),
    ),
    ('Maintenance', BREAKDOWN): ActivityRule(
        'Breakdown / Repair',
        EquipmentState.UNDER_MAINTENANCE,
        EquipmentState.TO_BE_CLEANED,
        _MAINTENANCE_PRIOR,
    ),
    ('Maintenance', PREVENTIVE): ActivityRule(
        'Preventive Maintenance',
        EquipmentState.UNDER_MAINTENANCE,
        EquipmentState.TO_BE_CLEANED,
        _MAINTENANCE_PRIOR,
    ),
    ('Qualification', QUALIFICATION): ActivityRule(
        'Qualification / Requalification',
        EquipmentState.UNDER_QUALIFICATION,
        EquipmentState.TO_BE_CLEANED,
        frozenset({EquipmentState.CLEANED_AND_QA_CERTIFIED, EquipmentState.CLEANED_READY_FOR_QA}),
    ),
}


DURING_STATES = frozenset(rule.during_state for rule in ACTIVITY_RULES.values())


def next_actions_for_state(state):
    """(usage_type_name, code, rule) for every activity startable from `state`."""
    return [
        (usage_type_name, code, rule)
        for (usage_type_name, code), rule in ACTIVITY_RULES.items()
        if state in rule.allowed_prior_states
    ]


def sub_activity_code_from_values(
    usage_type_name, process_sub_type='', cleaning_type='', maintenance_type=''
):
    if usage_type_name == 'Process':
        return process_sub_type or None
    if usage_type_name == 'Cleaning':
        return cleaning_type or None
    if usage_type_name == 'Maintenance':
        return maintenance_type or None
    if usage_type_name == 'Qualification':
        return QUALIFICATION
    return None


def sub_activity_code(usage_type_name, entry):
    """The sub-activity code stored on entry for its usage type, or None."""
    return sub_activity_code_from_values(
        usage_type_name,
        process_sub_type=entry.process_sub_type,
        cleaning_type=entry.cleaning_type,
        maintenance_type=entry.maintenance_type,
    )


def get_rule(usage_type_name, code):
    if not code:
        return None
    return ACTIVITY_RULES.get((usage_type_name, code))


def get_rule_for_entry(entry):
    usage_type_name = entry.usage_type.name
    return get_rule(usage_type_name, sub_activity_code(usage_type_name, entry))
