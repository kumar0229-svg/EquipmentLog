from django.db import migrations

SYSTEMS = ['System-1', 'System-2', 'System-3', 'System-4', 'System-5']


def seed_computerized_systems(apps, schema_editor):
    ComputerizedSystem = apps.get_model('masters', 'ComputerizedSystem')
    for name in SYSTEMS:
        ComputerizedSystem.objects.get_or_create(name=name)


def unseed_computerized_systems(apps, schema_editor):
    ComputerizedSystem = apps.get_model('masters', 'ComputerizedSystem')
    ComputerizedSystem.objects.filter(name__in=SYSTEMS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0021_computerizedsystem'),
    ]

    operations = [
        migrations.RunPython(seed_computerized_systems, unseed_computerized_systems),
    ]
