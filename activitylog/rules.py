"""Activity Rules: what equipment status an Activity + Sub Activity requires to
start, what it shows while running, and what it leaves behind on completion.

Source: the ActivityRuleConfig table (admin-editable — Activity Log ▸
Activity rule configs), seeded from what used to be a hardcoded
ACTIVITY_RULES dict here.
Sub-activity codes for Cleaning reuse activitylog.models.CleaningType values
directly (A/B/Q/G) so there is exactly one enum for cleaning sub-type, not
two.

The rule set is read once per cache period (see get_rules_dict) rather than
per lookup — it's queried from a handful of call sites, some of them
(entry_list rendering) once per row, so an uncached DB round trip per lookup
would turn a page of 500 entries into 500 extra queries.
"""

from dataclasses import dataclass

from django.core.cache import cache

REACTION = 'REACTION'
OTHER_EQUIPMENT = 'OTHER_EQUIPMENT'
HOLDING = 'HOLDING'

BREAKDOWN = 'BREAKDOWN'
PREVENTIVE = 'PREVENTIVE'

QUALIFICATION = 'QUALIFICATION'

CACHE_KEY = 'activitylog:activity_rules'
# Signals (activitylog/apps.py) clear this immediately in the worker that
# handled the edit; the TTL is a backstop for other gunicorn workers, whose
# in-memory cache a signal in one process can't reach.
CACHE_TTL = 300


@dataclass(frozen=True)
class ActivityRule:
    label: str
    during_state: str
    after_state: str
    allowed_prior_states: frozenset


def _load_rules_dict():
    from .models import ActivityRuleConfig

    return {
        (config.usage_type.name, config.code): ActivityRule(
            config.label,
            config.during_state,
            config.after_state,
            frozenset(config.allowed_prior_states),
        )
        for config in ActivityRuleConfig.objects.select_related('usage_type').all()
    }


def get_rules_dict():
    """{(usage_type_name, code): ActivityRule}, cached — see module docstring."""
    rules = cache.get(CACHE_KEY)
    if rules is None:
        rules = _load_rules_dict()
        cache.set(CACHE_KEY, rules, CACHE_TTL)
    return rules


def get_during_states():
    return frozenset(rule.during_state for rule in get_rules_dict().values())


def next_actions_for_state(state):
    """(usage_type_name, code, rule) for every activity startable from `state`."""
    return [
        (usage_type_name, code, rule)
        for (usage_type_name, code), rule in get_rules_dict().items()
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
    return get_rules_dict().get((usage_type_name, code))


def get_rule_for_entry(entry):
    usage_type_name = entry.usage_type.name
    return get_rule(usage_type_name, sub_activity_code(usage_type_name, entry))
