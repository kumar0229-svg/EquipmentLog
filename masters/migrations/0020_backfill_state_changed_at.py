from django.db import migrations
from django.utils import timezone

# state_changed_at didn't exist before 0019, so every equipment's current
# `state` has no recorded start time yet. Best available anchor: the most
# recent *completed* activity log entry on that equipment — in normal usage
# that's what produced the current state. Not exact for equipment whose
# state was hand-edited in admin after that entry, but that's a rare
# override, and leaving state_changed_at NULL (activitylog.expiry's
# untouched case) is the safe fallback either way.


def backfill_state_changed_at(apps, schema_editor):
    Equipment = apps.get_model('masters', 'Equipment')
    ActivityLogEntry = apps.get_model('activitylog', 'ActivityLogEntry')

    for equipment in Equipment.objects.filter(state_changed_at__isnull=True):
        latest = (
            ActivityLogEntry.objects.filter(equipment=equipment, end_date__isnull=False)
            .order_by('-end_date', '-end_time', '-id')
            .first()
        )
        if latest is None:
            continue
        equipment.state_changed_at = timezone.make_aware(
            timezone.datetime.combine(latest.end_date, latest.end_time)
        )
        equipment.save(update_fields=['state_changed_at'])


def noop_backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0019_equipment_state_changed_at'),
        ('activitylog', '0009_seed_cleaning_validity'),
    ]

    operations = [
        migrations.RunPython(backfill_state_changed_at, noop_backward),
    ]
