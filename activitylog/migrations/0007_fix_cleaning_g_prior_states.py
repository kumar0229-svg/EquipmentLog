from django.db import migrations

# Cleaning/Type-G (After Maintenance) was seeded (0005) with plain TO_BE_CLEANED
# as an allowed prior state alongside TO_BE_CLEANED_AFTER_MAINTENANCE, which
# incorrectly offered Type G any time equipment was generically "To Be
# Cleaned" (e.g. after Process or Qualification), not just after Maintenance.
# It should only be startable from TO_BE_CLEANED_AFTER_MAINTENANCE.
OLD_PRIOR_STATES = ['TO_BE_CLEANED_AFTER_MAINTENANCE', 'TO_BE_CLEANED']
NEW_PRIOR_STATES = ['TO_BE_CLEANED_AFTER_MAINTENANCE']


def fix_forward(apps, schema_editor):
    ActivityRuleConfig = apps.get_model('activitylog', 'ActivityRuleConfig')
    ActivityRuleConfig.objects.filter(
        usage_type__name='Cleaning', code='G'
    ).update(allowed_prior_states=NEW_PRIOR_STATES)


def fix_backward(apps, schema_editor):
    ActivityRuleConfig = apps.get_model('activitylog', 'ActivityRuleConfig')
    ActivityRuleConfig.objects.filter(
        usage_type__name='Cleaning', code='G'
    ).update(allowed_prior_states=OLD_PRIOR_STATES)


class Migration(migrations.Migration):

    dependencies = [
        ('activitylog', '0006_activitylogentry_adhered_material_removed'),
    ]

    operations = [
        migrations.RunPython(fix_forward, fix_backward),
    ]
