import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from masters.models import (
    Area, AreaType, Equipment, EquipmentState, EquipmentType, EquipmentUsageType, Product,
    ProductEquipment,
)

from .models import ActivityLogEntry, EntryStatus, MaintenanceType, ProcessSubType

User = get_user_model()


class ActivityLogTestCase(TestCase):
    def setUp(self):
        self.stream = Area.objects.create(name='Stream-1', area_type=AreaType.STREAM)
        self.location = Area.objects.create(
            name='Floor-1', area_type=AreaType.LOCATION, parent=self.stream
        )
        self.equipment_type = EquipmentType.objects.create(name='Reactor')
        self.equipment = Equipment.objects.create(
            code='RX-101', equipment_type=self.equipment_type, area=self.location
        )
        self.non_reactor_type = EquipmentType.objects.create(name='Centrifuge')
        self.non_reactor_equipment = Equipment.objects.create(
            code='CF-101', equipment_type=self.non_reactor_type, area=self.location
        )
        # get_or_create, not create: activitylog.0005_seed_activity_rules now
        # seeds these same usage types as a side effect of seeding
        # ActivityRuleConfig rows, so a freshly migrated test database
        # already has them.
        self.process = EquipmentUsageType.objects.get_or_create(name='Process')[0]
        self.cleaning = EquipmentUsageType.objects.get_or_create(name='Cleaning')[0]
        self.maintenance = EquipmentUsageType.objects.get_or_create(name='Maintenance')[0]
        self.operator = User.objects.create_user(
            'op1', password='pw-test-12345', role=Role.OPERATOR
        )

    def make_entry(self, **overrides):
        fields = {
            'equipment': self.equipment,
            'usage_type': self.process,
            'start_date': '2026-01-01',
            'start_time': '09:00',
            'start_by': self.operator,
            'created_by': self.operator,
        }
        fields.update(overrides)
        return ActivityLogEntry.objects.create(**fields)


class ActivityLogEntryModelTests(ActivityLogTestCase):
    def test_area_snapshot_defaults_to_equipment_area(self):
        entry = self.make_entry()
        self.assertEqual(entry.area_snapshot, self.equipment.area.full_path)

    def test_is_open_true_until_end_date_set(self):
        entry = self.make_entry()
        self.assertTrue(entry.is_open)
        entry.end_date = '2026-01-02'
        entry.save()
        self.assertFalse(entry.is_open)

    def test_duration_display_blank_while_open(self):
        entry = self.make_entry()
        self.assertIsNone(entry.duration)
        self.assertEqual(entry.duration_display, '')

    def test_duration_display_formats_days_hours_minutes(self):
        entry = self.make_entry(
            start_date='2026-01-01', start_time='09:00',
            end_date='2026-01-02', end_time='11:17',
        )
        entry.refresh_from_db()
        self.assertEqual(entry.duration, datetime.timedelta(days=1, hours=2, minutes=17))
        self.assertEqual(entry.duration_display, '1d 2h 17m')

    def test_duration_display_omits_zero_days(self):
        entry = self.make_entry(
            start_date='2026-01-01', start_time='09:00',
            end_date='2026-01-01', end_time='09:45',
        )
        entry.refresh_from_db()
        self.assertEqual(entry.duration_display, '45m')


class StartActivityViewTests(ActivityLogTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='op1', password='pw-test-12345')

    def test_start_activity_sets_equipment_state_and_creates_entry(self):
        self.equipment.state = EquipmentState.TO_BE_CLEANED
        self.equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'batch_no': 'B-1',
                'cleaning_sop_no': 'SOP-1',
                'cleaning_type': 'A',
                'adhered_material_removed': 'YES',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = ActivityLogEntry.objects.get(equipment=self.equipment)
        self.assertEqual(entry.status, EntryStatus.IN_PROGRESS)
        self.assertTrue(entry.is_open)
        self.assertEqual(entry.adhered_material_removed, 'YES')
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.state, EquipmentState.UNDER_CLEANING)

    def test_cannot_start_second_activity_while_one_is_open(self):
        self.make_entry()
        response = self.client.post(
            reverse('start_activity'),
            {'equipment': self.equipment.pk, 'usage_type': self.process.pk, 'remarks': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already has an activity in progress')
        self.assertEqual(ActivityLogEntry.objects.filter(equipment=self.equipment).count(), 1)

    def test_get_with_equipment_param_redirects_to_stop_when_already_open(self):
        entry = self.make_entry()
        response = self.client.get(reverse('start_activity') + f'?equipment={self.equipment.pk}')
        self.assertRedirects(response, reverse('stop_activity', args=[entry.pk]))

    def test_blocked_when_equipment_status_not_allowed_for_rule(self):
        # Fresh equipment defaults to Idle, which only unlocks Cleaning/Type-B
        # — Cleaning/Type-A requires To Be Cleaned or Cleaned and QA Certified.
        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'A',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'requires status')
        self.assertFalse(ActivityLogEntry.objects.filter(equipment=self.equipment).exists())

    def test_idle_equipment_can_start_cleaning_type_b(self):
        # Idle (the default status) unlocks exactly one activity: Cleaning
        # Type-B (product changeover) — this is the cycle's entry point.
        self.assertEqual(self.equipment.state, EquipmentState.NOT_IN_USE)
        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'B',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.state, EquipmentState.UNDER_CLEANING)

    def test_cleaning_sop_no_must_be_in_product_master_when_master_has_entries(self):
        product = Product.objects.create(name='Product-Mapped')
        ProductEquipment.objects.create(
            product=product, equipment=self.equipment, cleaning_sop_no='SOP-MASTER'
        )

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'B',
                'cleaning_sop_no': 'SOP-NOT-IN-MASTER',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is not a Cleaning SOP No defined for')
        self.assertFalse(ActivityLogEntry.objects.filter(equipment=self.equipment).exists())

    def test_cleaning_sop_no_from_product_master_is_accepted(self):
        product = Product.objects.create(name='Product-Mapped')
        ProductEquipment.objects.create(
            product=product, equipment=self.equipment, cleaning_sop_no='SOP-MASTER'
        )

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'B',
                'cleaning_sop_no': 'SOP-MASTER',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = ActivityLogEntry.objects.get(equipment=self.equipment)
        self.assertEqual(entry.cleaning_sop_no, 'SOP-MASTER')

    def test_cleaning_sop_no_unrestricted_when_no_master_entries_configured(self):
        # No ProductEquipment rows have a cleaning_sop_no set, so the field
        # isn't gated yet — same "not configured" leniency as the Process
        # product picker.
        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'B',
                'cleaning_sop_no': 'SOP-ANYTHING',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = ActivityLogEntry.objects.get(equipment=self.equipment)
        self.assertEqual(entry.cleaning_sop_no, 'SOP-ANYTHING')

    def test_type_g_cleaning_is_not_offered_from_plain_to_be_cleaned(self):
        # Type G is strictly post-maintenance — it requires
        # TO_BE_CLEANED_AFTER_MAINTENANCE specifically, not the generic
        # "To Be Cleaned" status equipment reaches after Process or
        # Qualification. Type A / Type B cover that case instead.
        self.equipment.state = EquipmentState.TO_BE_CLEANED
        self.equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'G',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'requires status')
        self.assertFalse(ActivityLogEntry.objects.filter(equipment=self.equipment).exists())

    def test_process_on_reactor_forces_reaction_sub_type(self):
        self.equipment.state = EquipmentState.CLEANED_AND_QA_CERTIFIED
        self.equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.process.pk,
                # Posting a sub-type is ignored for reactors — it's forced.
                'process_sub_type': ProcessSubType.HOLDING,
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = ActivityLogEntry.objects.get(equipment=self.equipment)
        self.assertEqual(entry.process_sub_type, ProcessSubType.REACTION)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.state, EquipmentState.IN_PROCESS)

    def test_process_on_non_reactor_requires_sub_type(self):
        self.non_reactor_equipment.state = EquipmentState.CLEANED_AND_QA_CERTIFIED
        self.non_reactor_equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {'equipment': self.non_reactor_equipment.pk, 'usage_type': self.process.pk, 'remarks': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select whether this is equipment use')

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.non_reactor_equipment.pk,
                'usage_type': self.process.pk,
                'process_sub_type': ProcessSubType.OTHER_EQUIPMENT,
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.non_reactor_equipment.refresh_from_db()
        self.assertEqual(self.non_reactor_equipment.state, EquipmentState.IN_USE)

    def test_process_product_must_be_mapped_to_equipment_when_mappings_exist(self):
        self.equipment.state = EquipmentState.CLEANED_AND_QA_CERTIFIED
        self.equipment.save(update_fields=['state'])
        mapped_product = Product.objects.create(name='Product-Mapped')
        other_product = Product.objects.create(name='Product-Other')
        ProductEquipment.objects.create(product=mapped_product, equipment=self.equipment)

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.process.pk,
                'product': other_product.pk,
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is not mapped to')
        self.assertFalse(ActivityLogEntry.objects.filter(equipment=self.equipment).exists())

    def test_process_product_mapped_to_equipment_is_accepted(self):
        self.equipment.state = EquipmentState.CLEANED_AND_QA_CERTIFIED
        self.equipment.save(update_fields=['state'])
        mapped_product = Product.objects.create(name='Product-Mapped')
        ProductEquipment.objects.create(product=mapped_product, equipment=self.equipment)

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.process.pk,
                'product': mapped_product.pk,
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        entry = ActivityLogEntry.objects.get(equipment=self.equipment)
        self.assertEqual(entry.product, mapped_product)

    def test_process_product_unrestricted_when_no_mappings_configured(self):
        # No ProductEquipment rows exist for this equipment at all, so the
        # product picker isn't gated yet — same "not configured" leniency as
        # usage_type_field_map.
        self.equipment.state = EquipmentState.CLEANED_AND_QA_CERTIFIED
        self.equipment.save(update_fields=['state'])
        product = Product.objects.create(name='Product-Unmapped')

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.process.pk,
                'product': product.pk,
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_cleaning_qa_certification_sets_under_qa_certification(self):
        self.equipment.state = EquipmentState.CLEANED_READY_FOR_QA
        self.equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'Q',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.state, EquipmentState.UNDER_QA_CERTIFICATION)

    def test_maintenance_completion_only_unlocks_cleaning_type_g(self):
        self.equipment.state = EquipmentState.UNDER_MAINTENANCE
        self.equipment.save(update_fields=['state'])
        entry = self.make_entry(
            usage_type=self.maintenance, maintenance_type=MaintenanceType.BREAKDOWN,
        )

        response = self.client.post(reverse('stop_activity', args=[entry.pk]))
        self.assertEqual(response.status_code, 302)
        self.equipment.refresh_from_db()
        self.assertEqual(
            self.equipment.state, EquipmentState.TO_BE_CLEANED_AFTER_MAINTENANCE
        )

        # Type A is not offered post-maintenance — only Type G is.
        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'A',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'requires status')

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'G',
                # Not applicable to Type G — should be dropped even if submitted.
                'adhered_material_removed': 'YES',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.state, EquipmentState.UNDER_CLEANING)
        entry = ActivityLogEntry.objects.get(equipment=self.equipment, cleaning_type='G')
        self.assertEqual(entry.adhered_material_removed, '')

    def test_qa_certification_also_allowed_from_cleaned_after_maintenance(self):
        # Per the Activity rules table, QA Certification's prior status can be
        # either "Cleaned and ready for QA certification" (the normal Type-B
        # path) or "Cleaned after maintenance" (post Type-G cleaning).
        self.equipment.state = EquipmentState.CLEANED_AFTER_MAINTENANCE
        self.equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.cleaning.pk,
                'cleaning_type': 'Q',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.state, EquipmentState.UNDER_QA_CERTIFICATION)

    def test_maintenance_requires_type_and_both_kinds_set_under_maintenance(self):
        self.equipment.state = EquipmentState.CLEANED_AFTER_MAINTENANCE
        self.equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {'equipment': self.equipment.pk, 'usage_type': self.maintenance.pk, 'remarks': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select Breakdown / Repair or Preventive Maintenance')

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.maintenance.pk,
                'maintenance_type': MaintenanceType.BREAKDOWN,
                'sap_document_no': 'SAP-123',
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.state, EquipmentState.UNDER_MAINTENANCE)

    def test_maintenance_requires_sap_document_no(self):
        self.equipment.state = EquipmentState.CLEANED_AFTER_MAINTENANCE
        self.equipment.save(update_fields=['state'])

        response = self.client.post(
            reverse('start_activity'),
            {
                'equipment': self.equipment.pk,
                'usage_type': self.maintenance.pk,
                'maintenance_type': MaintenanceType.BREAKDOWN,
                'remarks': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SAP Document No is required for Maintenance.')

    def test_context_map_suggests_cleaning_sop_from_last_process_product(self):
        product = Product.objects.create(name='Product-1')
        ProductEquipment.objects.create(
            product=product, equipment=self.equipment, cleaning_sop_no='SOP-P1'
        )
        self.make_entry(
            product=product, process_sub_type=ProcessSubType.REACTION,
            end_date='2026-01-02', end_time='09:00',
        )

        response = self.client.get(reverse('start_activity'))
        equipment_context = response.context['equipment_context_map'][str(self.equipment.pk)]
        self.assertEqual(equipment_context['last_product_id'], str(product.pk))
        self.assertEqual(
            equipment_context['products'][str(product.pk)],
            {'name': 'Product-1', 'cleaning_sop_no': 'SOP-P1'},
        )


class StopActivityViewTests(ActivityLogTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='op1', password='pw-test-12345')

    def test_stop_activity_closes_entry_and_frees_equipment(self):
        entry = self.make_entry(process_sub_type=ProcessSubType.REACTION)
        self.equipment.state = EquipmentState.IN_PROCESS
        self.equipment.save(update_fields=['state'])

        response = self.client.post(reverse('stop_activity', args=[entry.pk]))
        self.assertEqual(response.status_code, 302)

        entry.refresh_from_db()
        self.equipment.refresh_from_db()
        self.assertFalse(entry.is_open)
        self.assertEqual(entry.status, EntryStatus.COMPLETED)
        self.assertEqual(self.equipment.state, EquipmentState.TO_BE_CLEANED)

    def test_cannot_stop_an_already_closed_entry(self):
        entry = self.make_entry(end_date='2026-01-02', end_time='10:00')
        response = self.client.post(reverse('stop_activity', args=[entry.pk]), follow=True)
        self.assertContains(response, 'already completed')

    def test_stop_activity_without_sub_activity_data_is_blocked(self):
        # An entry with no recorded sub-activity has no rule to resolve —
        # stopping it must fail loudly rather than guess a status.
        entry = self.make_entry()
        response = self.client.post(reverse('stop_activity', args=[entry.pk]), follow=True)
        self.assertContains(response, 'No activity rule is defined')
        entry.refresh_from_db()
        self.assertTrue(entry.is_open)


class DashboardViewTests(ActivityLogTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='op1', password='pw-test-12345')

    def test_dashboard_lists_equipment_for_selected_stream(self):
        response = self.client.get(reverse('dashboard') + f'?stream={self.stream.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.equipment.code)

    def test_dashboard_links_open_equipment_straight_to_stop(self):
        entry = self.make_entry()
        response = self.client.get(reverse('dashboard') + f'?stream={self.stream.pk}')
        self.assertContains(response, reverse('stop_activity', args=[entry.pk]))
