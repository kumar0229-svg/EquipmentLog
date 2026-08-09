from django.db import migrations

# Calibration has no Activity Rules entry, so End Activity can no longer derive
# its closing status/state automatically — retiring it rather than guessing.
NAME = 'Calibration'


def deactivate_calibration(apps, schema_editor):
    EquipmentUsageType = apps.get_model('masters', 'EquipmentUsageType')
    EquipmentUsageType.objects.filter(name=NAME).update(active=False)


def reactivate_calibration(apps, schema_editor):
    EquipmentUsageType = apps.get_model('masters', 'EquipmentUsageType')
    EquipmentUsageType.objects.filter(name=NAME).update(active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0005_alter_equipment_state'),
    ]

    operations = [
        migrations.RunPython(deactivate_calibration, reactivate_calibration),
    ]
