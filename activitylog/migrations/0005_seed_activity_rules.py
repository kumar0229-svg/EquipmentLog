from django.db import migrations

# The 10 rules that used to live only in activitylog/rules.py's ACTIVITY_RULES
# dict, seeded here so the cutover to a DB-backed table happens automatically
# on `migrate` — no manual seed step, no window where get_rule() returns None
# for everything.
_PROCESS_PRIOR = [
    'CLEANED_TYPE_A', 'CLEANED_AND_QA_CERTIFIED', 'CLEANED_AFTER_MAINTENANCE',
]

_MAINTENANCE_PRIOR = [
    'CLEANED_AND_QA_CERTIFIED', 'CLEANED_AFTER_MAINTENANCE', 'CLEANED_READY_FOR_QA',
]

RULES = [
    ('Process', 'REACTION', 'Reaction (Reactor Only)', 'IN_PROCESS', 'TO_BE_CLEANED', _PROCESS_PRIOR),
    ('Process', 'OTHER_EQUIPMENT', 'Equipment Other Than Reactor', 'IN_USE', 'TO_BE_CLEANED', _PROCESS_PRIOR),
    (
        'Process', 'HOLDING', 'Holding of Mother Liquor / Distilled Solvent', 'TO_BE_PRESERVED',
        'TO_BE_CLEANED', _PROCESS_PRIOR,
    ),
    (
        'Cleaning', 'A', 'Type-A (Same Product)', 'UNDER_CLEANING', 'CLEANED_TYPE_A',
        ['TO_BE_CLEANED', 'CLEANED_AND_QA_CERTIFIED'],
    ),
    (
        'Cleaning', 'B', 'Type-B (Product Changeover)', 'UNDER_CLEANING', 'CLEANED_READY_FOR_QA',
        [
            'TO_BE_CLEANED', 'CLEANED_TYPE_A', 'CLEANED_AND_QA_CERTIFIED',
            'CLEANED_AFTER_MAINTENANCE', 'NOT_IN_USE',
        ],
    ),
    (
        'Cleaning', 'Q', 'QA Certification', 'UNDER_QA_CERTIFICATION', 'CLEANED_AND_QA_CERTIFIED',
        ['CLEANED_READY_FOR_QA', 'CLEANED_AFTER_MAINTENANCE'],
    ),
    (
        'Cleaning', 'G', 'Type-G (After Maintenance)', 'UNDER_CLEANING', 'CLEANED_AFTER_MAINTENANCE',
        ['TO_BE_CLEANED_AFTER_MAINTENANCE', 'TO_BE_CLEANED'],
    ),
    (
        'Maintenance', 'BREAKDOWN', 'Breakdown / Repair', 'UNDER_MAINTENANCE',
        'TO_BE_CLEANED_AFTER_MAINTENANCE', _MAINTENANCE_PRIOR,
    ),
    (
        'Maintenance', 'PREVENTIVE', 'Preventive Maintenance', 'UNDER_MAINTENANCE',
        'TO_BE_CLEANED_AFTER_MAINTENANCE', _MAINTENANCE_PRIOR,
    ),
    (
        'Qualification', 'QUALIFICATION', 'Qualification / Requalification', 'UNDER_QUALIFICATION',
        'TO_BE_CLEANED', ['CLEANED_AND_QA_CERTIFIED', 'CLEANED_READY_FOR_QA'],
    ),
]


def seed_activity_rules(apps, schema_editor):
    EquipmentUsageType = apps.get_model('masters', 'EquipmentUsageType')
    ActivityRuleConfig = apps.get_model('activitylog', 'ActivityRuleConfig')

    for usage_type_name, code, label, during_state, after_state, allowed_prior_states in RULES:
        # get_or_create, not get: seed_masters (which normally creates these)
        # is a manual first-time-setup step per PROJECT.md, run *after*
        # `migrate` — so on a fresh database these rows don't exist yet when
        # this migration runs.
        usage_type, _ = EquipmentUsageType.objects.get_or_create(name=usage_type_name)
        ActivityRuleConfig.objects.update_or_create(
            usage_type=usage_type,
            code=code,
            defaults={
                'label': label,
                'during_state': during_state,
                'after_state': after_state,
                'allowed_prior_states': allowed_prior_states,
            },
        )


def unseed_activity_rules(apps, schema_editor):
    EquipmentUsageType = apps.get_model('masters', 'EquipmentUsageType')
    ActivityRuleConfig = apps.get_model('activitylog', 'ActivityRuleConfig')

    for usage_type_name, code, *_ in RULES:
        usage_type = EquipmentUsageType.objects.filter(name=usage_type_name).first()
        if usage_type:
            ActivityRuleConfig.objects.filter(usage_type=usage_type, code=code).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('activitylog', '0004_activityruleconfig'),
        ('masters', '0002_alter_equipment_state'),
    ]

    operations = [
        migrations.RunPython(seed_activity_rules, unseed_activity_rules),
    ]
