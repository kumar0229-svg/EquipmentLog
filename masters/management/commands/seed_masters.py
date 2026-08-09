from django.core.management.base import BaseCommand

from masters.models import EquipmentType, EquipmentUsageType

EQUIPMENT_TYPES = [
    'Reactor',
    'ANFD',
    'Multi Mill',
    'Isolator',
    'Sifter',
    'Centrifuge',
    'Jet Mill',
]

USAGE_TYPES = [
    'Process',
    'Cleaning',
    'Maintenance',
    'Qualification',
]


class Command(BaseCommand):
    help = 'Seed reference data (equipment types, usage types).'

    def handle(self, *args, **options):
        for name in EQUIPMENT_TYPES:
            _, created = EquipmentType.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'Created equipment type: {name}')

        for name in USAGE_TYPES:
            _, created = EquipmentUsageType.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f'Created usage type: {name}')

        self.stdout.write(self.style.SUCCESS('Reference data seeded.'))
