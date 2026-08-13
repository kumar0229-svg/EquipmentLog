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


batch_no_validator = RegexValidator(
    r'^[A-Z0-9]+$', 'Batch No must be alphanumeric, upper case, with no spaces.'
)
process_order_no_validator = RegexValidator(
    r'^[0-9]+$', 'Process Order No must be numeric only, with no spaces.'
)


class BMRIssuanceEntry(models.Model):
    """One BMR (Batch Manufacturing Record) issued to Production for a batch."""

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
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bmr_entries_issued',
    )
    issued_date = models.DateField()
    issued_time = models.TimeField()

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_date', '-issued_time', '-id']
        verbose_name = 'BMR Issuance Entry'
        verbose_name_plural = 'BMR Issuance Entries'

    def __str__(self):
        return f'{self.batch_no} — {self.product.name}'
