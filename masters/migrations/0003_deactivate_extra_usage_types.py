from django.db import migrations

# Only these usage types drive the Start Activity usage-type selection; the
# rest were seeded speculatively and are being retired per the equipment log
# feature spec (equipment status is set from Set Equipment State instead).
KEEP = ['Process', 'Cleaning', 'Maintenance', 'Qualification', 'Calibration']


def deactivate_extra_usage_types(apps, schema_editor):
    EquipmentUsageType = apps.get_model('masters', 'EquipmentUsageType')
    EquipmentUsageType.objects.exclude(name__in=KEEP).update(active=False)


def reactivate_extra_usage_types(apps, schema_editor):
    EquipmentUsageType = apps.get_model('masters', 'EquipmentUsageType')
    EquipmentUsageType.objects.exclude(name__in=KEEP).update(active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0002_alter_equipment_state'),
    ]

    operations = [
        migrations.RunPython(deactivate_extra_usage_types, reactivate_extra_usage_types),
    ]
