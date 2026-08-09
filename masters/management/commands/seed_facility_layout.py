from django.core.management.base import BaseCommand
from django.db import transaction

from masters.models import Area, AreaType, Equipment, EquipmentType

# Facilities from the equipment-log facility spec. Only API-1 has its streams
# and floor locations spelled out so far; API-2/API-3 exist as bare facilities
# ready to be broken down the same way once that's specified.
FACILITIES = ['API-1', 'API-2', 'API-3']

STREAMS_BY_FACILITY = {
    'API-1': [
        ('Stream-1', 'ST1'),
        ('Stream-2', 'ST2'),
        ('Stream-3', 'ST3'),
        ('Stream-4', 'ST4'),
        ('Stream-5', 'ST5'),
        ('Powder Processing', 'PP'),
    ],
}

# (location name, code) — same 5 floor locations under every stream.
LOCATIONS = [
    ('Ground Floor-Intermediate', 'GF_INT'),
    ('Ground Floor-Final Area', 'GF_FA'),
    ('1st Floor-Intermediate', 'F1_INT'),
    ('1st Floor-Final area', 'F1_FA'),
    ('2nd Floor-Intermediate', 'F2_INT'),
]

# (equipment type name, short code for the generated equipment code).
EQUIPMENT_TYPE_CODES = [
    ('Reactor', 'RX'),
    ('ANFD', 'ANFD'),
    ('Multi Mill', 'MM'),
    ('Isolator', 'ISO'),
    ('Sifter', 'SF'),
    ('Centrifuge', 'CFG'),
    ('Jet Mill', 'JM'),
]


class Command(BaseCommand):
    help = (
        'Seed the API-1 facility layout (streams -> floor locations -> cubicles) '
        'and populate every cubicle with one equipment of each type.'
    )

    def handle(self, *args, **options):
        equipment_types = {
            name: EquipmentType.objects.get_or_create(name=name)[0]
            for name, _ in EQUIPMENT_TYPE_CODES
        }

        areas_created = 0
        equipment_created = 0

        with transaction.atomic():
            for facility_name in FACILITIES:
                facility, created = Area.objects.get_or_create(
                    name=facility_name, parent=None, defaults={'area_type': AreaType.BLOCK}
                )
                areas_created += created

                for stream_name, stream_code in STREAMS_BY_FACILITY.get(facility_name, []):
                    stream, created = Area.objects.get_or_create(
                        name=stream_name, parent=facility, defaults={'area_type': AreaType.STREAM}
                    )
                    areas_created += created

                    for location_name, location_code in LOCATIONS:
                        location, created = Area.objects.get_or_create(
                            name=location_name,
                            parent=stream,
                            defaults={'area_type': AreaType.LOCATION},
                        )
                        areas_created += created

                        cubicle_name = f'{facility_name}_{stream_code}_{location_code}_001'
                        cubicle, created = Area.objects.get_or_create(
                            name=cubicle_name,
                            parent=location,
                            defaults={'area_type': AreaType.CUBICLE},
                        )
                        areas_created += created

                        for type_name, type_code in EQUIPMENT_TYPE_CODES:
                            _, created = Equipment.objects.get_or_create(
                                code=f'{cubicle_name}-{type_code}',
                                defaults={
                                    'equipment_type': equipment_types[type_name],
                                    'area': cubicle,
                                },
                            )
                            equipment_created += created

        self.stdout.write(
            self.style.SUCCESS(
                f'Facility layout seeded: {areas_created} areas, '
                f'{equipment_created} equipment created.'
            )
        )
