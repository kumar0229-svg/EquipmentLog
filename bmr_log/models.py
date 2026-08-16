import secrets

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from masters.models import Area, AreaType, Product


class BatchType(models.TextChoices):
    COMMERCIAL = 'COMMERCIAL', 'Commercial'
    VALIDATION = 'VALIDATION', 'Validation'
    RE_PROCESS = 'RE_PROCESS', 'Re-Process'
    ADDITIONAL = 'ADDITIONAL', 'Additional'
    TRIAL = 'TRIAL', 'Trial'
    REWORK = 'REWORK', 'Rework'
    BLENDING = 'BLENDING', 'Blending'
    PACKING = 'PACKING', 'Packing'


class BMRStatus(models.TextChoices):
    PREPARED = 'PREPARED', 'Prepared'
    RECEIVED = 'RECEIVED', 'Received by Production'
    ISSUED = 'ISSUED', 'Issued'
    RETURNED = 'RETURNED', 'Returned by Production'
    VERIFIED = 'VERIFIED', 'Verified'
    CLOSED = 'CLOSED', 'Received by QA'


batch_no_validator = RegexValidator(
    r'^[A-Z0-9]+$', 'Batch No must be alphanumeric, upper case, with no spaces.'
)
process_order_no_validator = RegexValidator(
    r'^[0-9]+$', 'Process Order No must be numeric only, with no spaces.'
)


def generate_token():
    """A 6-digit confirmation code, shown only to the identity meant to consume it."""
    return f'{secrets.randbelow(1_000_000):06d}'


class BMRIssuanceEntry(models.Model):
    """One BMR (Batch Manufacturing Record) issued to Production for a batch.

    Custody moves through a 6-step chain — Prepare (QA) -> Verify & Receive
    (the named Production user) -> Issued (QA) -> ... execution ... ->
    Returned (that same Production user) -> Verified (QA) -> Received back
    (any QA user). The two "receive" steps are token-gated: the token is
    revealed only to the identity authorized to consume it, never to the
    party who generated it, so it works as a forced conscious confirmation
    rather than a secret exchanged between the two sides.
    """

    batch_no = models.CharField(
        'Batch No', max_length=20, unique=True, validators=[batch_no_validator],
        help_text='Alphanumeric, upper case, no spaces. Must be unique — it cannot repeat.',
    )
    batch_type = models.CharField('Type of Batch', max_length=20, choices=BatchType.choices)
    process_order_no = models.CharField(
        'Process Order No', max_length=20, unique=True, validators=[process_order_no_validator],
        help_text='Numeric only, no spaces. Must be unique — it cannot repeat.',
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='bmr_issuances', verbose_name='Product Name'
    )
    master_document_no = models.CharField('Master Document No', max_length=100)
    production_block = models.ForeignKey(
        Area, on_delete=models.PROTECT, related_name='bmr_issuances',
        limit_choices_to={'area_type': AreaType.BLOCK}, verbose_name='Production Block',
    )

    issued_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_received',
        verbose_name='Issued To',
    )

    status = models.CharField(max_length=20, choices=BMRStatus.choices, default=BMRStatus.PREPARED)

    # Step 1 — Prepare (QA). Nullable only so the migration adding this column
    # doesn't need a fabricated default — always set at creation in the view.
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_prepared',
        null=True, blank=True,
    )
    receive_token = models.CharField(max_length=6, default=generate_token)

    # Step 2 — Verify & Receive (the named issued_to user)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_receive_confirmed',
        null=True, blank=True,
    )
    received_at = models.DateTimeField(null=True, blank=True)

    # Step 3 — Issued (QA)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_issued',
        null=True, blank=True,
    )
    issued_date = models.DateField(null=True, blank=True)
    issued_time = models.TimeField(null=True, blank=True)

    # Step 4 — Returned (the same issued_to user)
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_returned',
        null=True, blank=True,
    )
    returned_at = models.DateTimeField(null=True, blank=True)
    return_token = models.CharField(max_length=6, blank=True, default='')

    # Step 5 — Verified (QA)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_verified',
        null=True, blank=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    # Step 6 — Received back (any QA user)
    received_back_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_received_back',
        null=True, blank=True,
    )
    received_back_at = models.DateTimeField(null=True, blank=True)

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'BMR Issuance Entry'
        verbose_name_plural = 'BMR Issuance Entries'

    def __str__(self):
        return f'{self.batch_no} — {self.product.name}'

    @property
    def is_open(self):
        return self.status != BMRStatus.CLOSED
