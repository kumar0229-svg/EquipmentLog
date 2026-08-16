from django.db import migrations

# Cleaned status now has a shelf life: Type-A cleans are only valid 3 days,
# Type-B and Type-G are valid 6 days. Once that lapses, activitylog.expiry
# auto-reverts the equipment to expired_state. Q (QA Certification) has no
# expiry — it's the terminal "ready" state, not itself a rules(cleaning)
# style hold — so it's left blank like every other row.
VALIDITY = [
    ('A', 3, 'TO_BE_CLEANED'),
    ('B', 6, 'NOT_IN_USE'),
    ('G', 6, 'TO_BE_CLEANED_AFTER_MAINTENANCE'),
]


def seed_validity(apps, schema_editor):
    ActivityRuleConfig = apps.get_model('activitylog', 'ActivityRuleConfig')

    for code, validity_days, expired_state in VALIDITY:
        ActivityRuleConfig.objects.filter(usage_type__name='Cleaning', code=code).update(
            validity_days=validity_days, expired_state=expired_state,
        )


def unseed_validity(apps, schema_editor):
    ActivityRuleConfig = apps.get_model('activitylog', 'ActivityRuleConfig')

    for code, *_ in VALIDITY:
        ActivityRuleConfig.objects.filter(usage_type__name='Cleaning', code=code).update(
            validity_days=None, expired_state='',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('activitylog', '0008_activityruleconfig_expired_state_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_validity, unseed_validity),
    ]
