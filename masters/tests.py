from django.test import TestCase

from .models import Area, AreaType


class AreaFullPathTests(TestCase):
    def test_full_path_is_just_the_name_at_the_root(self):
        facility = Area.objects.create(name='API-1', area_type=AreaType.BLOCK)
        self.assertEqual(facility.full_path, 'API-1')

    def test_full_path_recurses_through_every_ancestor(self):
        facility = Area.objects.create(name='API-1', area_type=AreaType.BLOCK)
        stream = Area.objects.create(name='Stream-1', area_type=AreaType.STREAM, parent=facility)
        location = Area.objects.create(
            name='Ground Floor-Intermediate', area_type=AreaType.LOCATION, parent=stream
        )
        cubicle = Area.objects.create(
            name='API-1_ST1_GF_INT_001', area_type=AreaType.CUBICLE, parent=location
        )
        self.assertEqual(
            cubicle.full_path,
            'API-1 / Stream-1 / Ground Floor-Intermediate / API-1_ST1_GF_INT_001',
        )
