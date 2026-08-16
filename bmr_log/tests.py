from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from masters.models import Area, AreaType, Product

from .forms import PrepareBMRForm
from .models import BatchType, BMRIssuanceEntry, BMRStatus

User = get_user_model()


class BatchNoValidationTestCase(TestCase):
    def setUp(self):
        self.block = Area.objects.create(name='API-1', area_type=AreaType.BLOCK)
        self.product = Product.objects.create(name='Paracetamol')
        self.qa = User.objects.create_user('qa1', password='pw-test-12345', role=Role.QA)
        self.operator = User.objects.create_user('op1', password='pw-test-12345', role=Role.OPERATOR)

    def _form_data(self, batch_no):
        return {
            'batch_no': batch_no,
            'batch_type': BatchType.COMMERCIAL,
            'process_order_no': '123456',
            'product': self.product.pk,
            'master_document_no': 'MD-001',
            'production_block': self.block.pk,
            'issued_to': self.operator.pk,
            'remarks': '',
        }

    def _prepare(self, batch_no):
        return BMRIssuanceEntry.objects.create(
            batch_no=batch_no,
            batch_type=BatchType.COMMERCIAL,
            process_order_no='123456',
            product=self.product,
            master_document_no='MD-001',
            production_block=self.block,
            issued_to=self.operator,
            prepared_by=self.qa,
        )

    def test_valid_batch_no_is_accepted(self):
        form = PrepareBMRForm(self._form_data('CM260001'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_lower_case_batch_no_is_normalized_to_upper(self):
        form = PrepareBMRForm(self._form_data('cm260001'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['batch_no'], 'CM260001')

    def test_batch_no_with_space_is_rejected(self):
        form = PrepareBMRForm(self._form_data('CM 260001'))
        self.assertFalse(form.is_valid())
        self.assertIn('batch_no', form.errors)

    def test_non_alphanumeric_batch_no_is_rejected(self):
        form = PrepareBMRForm(self._form_data('CM-260001'))
        self.assertFalse(form.is_valid())
        self.assertIn('batch_no', form.errors)

    def test_duplicate_batch_no_is_rejected_by_form(self):
        self._prepare('CM260001')
        form = PrepareBMRForm(self._form_data('CM260001'))
        self.assertFalse(form.is_valid())
        self.assertIn('batch_no', form.errors)

    def test_duplicate_batch_no_case_insensitive_is_rejected_by_form(self):
        self._prepare('CM260001')
        form = PrepareBMRForm(self._form_data('cm260001'))
        self.assertFalse(form.is_valid())
        self.assertIn('batch_no', form.errors)

    def test_duplicate_batch_no_is_rejected_at_model_level(self):
        self._prepare('CM260001')
        with self.assertRaises(ValidationError):
            BMRIssuanceEntry(
                batch_no='CM260001',
                batch_type=BatchType.COMMERCIAL,
                process_order_no='999999',
                product=self.product,
                master_document_no='MD-002',
                production_block=self.block,
                issued_to=self.operator,
                prepared_by=self.qa,
            ).full_clean()


class ProcessOrderNoValidationTestCase(TestCase):
    def setUp(self):
        self.block = Area.objects.create(name='API-1', area_type=AreaType.BLOCK)
        self.product = Product.objects.create(name='Paracetamol')
        self.qa = User.objects.create_user('qa1', password='pw-test-12345', role=Role.QA)
        self.operator = User.objects.create_user('op1', password='pw-test-12345', role=Role.OPERATOR)

    def _form_data(self, process_order_no, batch_no='CM260001'):
        return {
            'batch_no': batch_no,
            'batch_type': BatchType.COMMERCIAL,
            'process_order_no': process_order_no,
            'product': self.product.pk,
            'master_document_no': 'MD-001',
            'production_block': self.block.pk,
            'issued_to': self.operator.pk,
            'remarks': '',
        }

    def _prepare(self, process_order_no):
        return BMRIssuanceEntry.objects.create(
            batch_no=f'CM26{process_order_no}',
            batch_type=BatchType.COMMERCIAL,
            process_order_no=process_order_no,
            product=self.product,
            master_document_no='MD-001',
            production_block=self.block,
            issued_to=self.operator,
            prepared_by=self.qa,
        )

    def test_numeric_process_order_no_is_valid(self):
        form = PrepareBMRForm(self._form_data('123456'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_alphabetic_process_order_no_is_rejected(self):
        form = PrepareBMRForm(self._form_data('ABC123'))
        self.assertFalse(form.is_valid())
        self.assertIn('process_order_no', form.errors)

    def test_process_order_no_with_space_is_rejected(self):
        form = PrepareBMRForm(self._form_data('123 456'))
        self.assertFalse(form.is_valid())
        self.assertIn('process_order_no', form.errors)

    def test_duplicate_process_order_no_is_rejected_by_form(self):
        self._prepare('123456')
        form = PrepareBMRForm(self._form_data('123456', batch_no='CM260002'))
        self.assertFalse(form.is_valid())
        self.assertIn('process_order_no', form.errors)

    def test_duplicate_process_order_no_is_rejected_at_model_level(self):
        self._prepare('123456')
        with self.assertRaises(ValidationError):
            BMRIssuanceEntry(
                batch_no='CM260002',
                batch_type=BatchType.COMMERCIAL,
                process_order_no='123456',
                product=self.product,
                master_document_no='MD-002',
                production_block=self.block,
                issued_to=self.operator,
                prepared_by=self.qa,
            ).full_clean()


class PrepareBMRViewTestCase(TestCase):
    def setUp(self):
        self.block = Area.objects.create(name='API-1', area_type=AreaType.BLOCK)
        self.product = Product.objects.create(name='Paracetamol')
        self.qa = User.objects.create_user('qa1', password='pw-test-12345', role=Role.QA)
        self.operator = User.objects.create_user('op1', password='pw-test-12345', role=Role.OPERATOR)

    def _post_data(self, batch_no, process_order_no='654321'):
        return {
            'batch_no': batch_no,
            'batch_type': BatchType.PACKING,
            'process_order_no': process_order_no,
            'product': self.product.pk,
            'master_document_no': 'MD-002',
            'production_block': self.block.pk,
            'issued_to': self.operator.pk,
        }

    def test_operator_cannot_prepare_bmr(self):
        self.client.force_login(self.operator)
        response = self.client.post(reverse('bmr_prepare'), self._post_data('CM260001'))
        self.assertEqual(response.status_code, 403)

    def test_qa_can_prepare_bmr_with_user_entered_batch_no(self):
        self.client.force_login(self.qa)
        response = self.client.post(reverse('bmr_prepare'), self._post_data('CM260001'))
        entry = BMRIssuanceEntry.objects.get(batch_no='CM260001')
        self.assertRedirects(response, reverse('bmr_entry_detail', args=[entry.pk]))
        self.assertEqual(entry.prepared_by, self.qa)
        self.assertEqual(entry.status, BMRStatus.PREPARED)
        self.assertEqual(len(entry.receive_token), 6)

    def test_qa_cannot_prepare_duplicate_batch_no(self):
        self.client.force_login(self.qa)
        self.client.post(reverse('bmr_prepare'), self._post_data('CM260001'))
        response = self.client.post(reverse('bmr_prepare'), self._post_data('CM260001'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BMRIssuanceEntry.objects.filter(batch_no='CM260001').count(), 1)

    def test_qa_cannot_prepare_duplicate_process_order_no(self):
        self.client.force_login(self.qa)
        self.client.post(reverse('bmr_prepare'), self._post_data('CM260001', '654321'))
        response = self.client.post(reverse('bmr_prepare'), self._post_data('CM260002', '654321'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BMRIssuanceEntry.objects.filter(process_order_no='654321').count(), 1)

    def test_entry_list_requires_login(self):
        response = self.client.get(reverse('bmr_log'))
        self.assertEqual(response.status_code, 302)


class WorkflowTransitionTestCase(TestCase):
    """Walks a BMR through all 6 steps, checking the identity/token gates at each."""

    def setUp(self):
        self.block = Area.objects.create(name='API-1', area_type=AreaType.BLOCK)
        self.product = Product.objects.create(name='Paracetamol')
        self.qa = User.objects.create_user('qa1', password='pw-test-12345', role=Role.QA)
        self.qa2 = User.objects.create_user('qa2', password='pw-test-12345', role=Role.QA)
        self.operator = User.objects.create_user('op1', password='pw-test-12345', role=Role.OPERATOR)
        self.other_operator = User.objects.create_user('op2', password='pw-test-12345', role=Role.OPERATOR)
        self.entry = BMRIssuanceEntry.objects.create(
            batch_no='CM260001',
            batch_type=BatchType.COMMERCIAL,
            process_order_no='123456',
            product=self.product,
            master_document_no='MD-001',
            production_block=self.block,
            issued_to=self.operator,
            prepared_by=self.qa,
        )

    def test_receive_token_is_hidden_from_qa(self):
        self.client.force_login(self.qa)
        response = self.client.get(reverse('bmr_entry_detail', args=[self.entry.pk]))
        self.assertNotContains(response, self.entry.receive_token)

    def test_wrong_user_cannot_verify_receive(self):
        self.client.force_login(self.other_operator)
        response = self.client.post(
            reverse('bmr_verify_receive', args=[self.entry.pk]), {'token': self.entry.receive_token}
        )
        self.assertEqual(response.status_code, 403)

    def test_wrong_token_is_rejected(self):
        self.client.force_login(self.operator)
        self.client.post(reverse('bmr_verify_receive', args=[self.entry.pk]), {'token': '000000'})
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, BMRStatus.PREPARED)

    def test_named_user_can_verify_receive_with_correct_token(self):
        self.client.force_login(self.operator)
        response = self.client.post(
            reverse('bmr_verify_receive', args=[self.entry.pk]), {'token': self.entry.receive_token}
        )
        self.entry.refresh_from_db()
        self.assertRedirects(response, reverse('bmr_entry_detail', args=[self.entry.pk]))
        self.assertEqual(self.entry.status, BMRStatus.RECEIVED)
        self.assertEqual(self.entry.received_by, self.operator)

    def _advance_to_received(self):
        self.client.force_login(self.operator)
        self.client.post(reverse('bmr_verify_receive', args=[self.entry.pk]), {'token': self.entry.receive_token})
        self.entry.refresh_from_db()

    def test_operator_cannot_mark_issued(self):
        self._advance_to_received()
        self.client.force_login(self.operator)
        response = self.client.post(reverse('bmr_mark_issued', args=[self.entry.pk]))
        self.assertEqual(response.status_code, 403)

    def test_qa_marks_issued(self):
        self._advance_to_received()
        self.client.force_login(self.qa)
        self.client.post(reverse('bmr_mark_issued', args=[self.entry.pk]))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, BMRStatus.ISSUED)
        self.assertIsNotNone(self.entry.issued_date)

    def _advance_to_issued(self):
        self._advance_to_received()
        self.client.force_login(self.qa)
        self.client.post(reverse('bmr_mark_issued', args=[self.entry.pk]))
        self.entry.refresh_from_db()

    def test_wrong_user_cannot_mark_returned(self):
        self._advance_to_issued()
        self.client.force_login(self.other_operator)
        response = self.client.post(reverse('bmr_mark_returned', args=[self.entry.pk]))
        self.assertEqual(response.status_code, 403)

    def test_named_user_marks_returned_and_generates_return_token(self):
        self._advance_to_issued()
        self.client.force_login(self.operator)
        self.client.post(reverse('bmr_mark_returned', args=[self.entry.pk]))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, BMRStatus.RETURNED)
        self.assertEqual(len(self.entry.return_token), 6)

    def _advance_to_returned(self):
        self._advance_to_issued()
        self.client.force_login(self.operator)
        self.client.post(reverse('bmr_mark_returned', args=[self.entry.pk]))
        self.entry.refresh_from_db()

    def test_return_token_is_hidden_from_operator(self):
        self._advance_to_returned()
        self.client.force_login(self.qa)
        self.client.post(reverse('bmr_verify_return', args=[self.entry.pk]))
        self.entry.refresh_from_db()
        self.client.force_login(self.operator)
        response = self.client.get(reverse('bmr_entry_detail', args=[self.entry.pk]))
        self.assertNotContains(response, self.entry.return_token)

    def _advance_to_verified(self):
        self._advance_to_returned()
        self.client.force_login(self.qa)
        self.client.post(reverse('bmr_verify_return', args=[self.entry.pk]))
        self.entry.refresh_from_db()

    def test_any_qa_user_can_receive_back_with_correct_token(self):
        self._advance_to_verified()
        self.client.force_login(self.qa2)
        response = self.client.post(
            reverse('bmr_receive_back', args=[self.entry.pk]), {'token': self.entry.return_token}
        )
        self.entry.refresh_from_db()
        self.assertRedirects(response, reverse('bmr_entry_detail', args=[self.entry.pk]))
        self.assertEqual(self.entry.status, BMRStatus.CLOSED)
        self.assertEqual(self.entry.received_back_by, self.qa2)
        self.assertFalse(self.entry.is_open)


class PrintViewTestCase(TestCase):
    def setUp(self):
        self.operator = User.objects.create_user('op1', password='pw-test-12345', role=Role.OPERATOR)
        self.client.force_login(self.operator)

    def test_print_without_batch_type_redirects_with_error(self):
        response = self.client.get(reverse('bmr_entry_list_print'), follow=True)
        self.assertRedirects(response, reverse('bmr_log'))
        self.assertContains(response, 'Select a batch type before printing')

    def test_print_with_batch_type_renders(self):
        response = self.client.get(
            reverse('bmr_entry_list_print'), {'batch_type': BatchType.COMMERCIAL}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Commercial')
