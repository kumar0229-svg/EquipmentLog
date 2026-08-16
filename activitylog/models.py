import datetime

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from masters.models import Equipment, EquipmentState, EquipmentUsageType, Product


class EntryStatus(models.TextChoices):
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'


class MaintenanceFrequency(models.TextChoices):
    QUARTERLY = 'QUARTERLY', 'Quarterly'
    HALF_YEARLY = 'HALF_YEARLY', 'Half Yearly'
    ANNUAL = 'ANNUAL', 'Annual'
    BIANNUAL = 'BIANNUAL', 'Biannual'
    OTHERS = 'OTHERS', 'Others'


class CleaningType(models.TextChoices):
    A = 'A', 'Type A'
    B = 'B', 'Type B'
    Q = 'Q', 'QA Certification'
    G = 'G', 'Type G'


class YesNo(models.TextChoices):
    YES = 'YES', 'Yes'
    NO = 'NO', 'No'


class ProcessSubType(models.TextChoices):
    REACTION = 'REACTION', 'Reaction (Reactor Only)'
    OTHER_EQUIPMENT = 'OTHER_EQUIPMENT', 'Equipment Other Than Reactor'
    HOLDING = 'HOLDING', 'Holding of Mother Liquor / Distilled Solvent'


class MaintenanceType(models.TextChoices):
    BREAKDOWN = 'BREAKDOWN', 'Breakdown / Repair'
    PREVENTIVE = 'PREVENTIVE', 'Preventive Maintenance'


class ActivityRuleConfig(models.Model):
    """Admin-editable version of what rules.ACTIVITY_RULES used to hardcode:
    the equipment status an (usage type, sub-activity code) requires to
    start, what it shows while running, and what it leaves behind on
    completion.

    `code` must match the sub-activity code produced by
    rules.sub_activity_code_from_values() — i.e. a ProcessSubType,
    CleaningType, or MaintenanceType value, or 'QUALIFICATION' for
    Qualification. That mapping is still code (start_activity.html's JS and
    the model field choices it's built from), so this table lets an admin
    revise *where a known activity is allowed to run*, not invent an
    entirely new kind of activity.
    """

    usage_type = models.ForeignKey(
        EquipmentUsageType, on_delete=models.PROTECT, related_name='activity_rules'
    )
    code = models.CharField(
        max_length=20,
        help_text=(
            'Must match the sub-activity code used in code — e.g. REACTION, '
            'OTHER_EQUIPMENT, HOLDING, A, B, Q, G, BREAKDOWN, PREVENTIVE, QUALIFICATION.'
        ),
    )
    label = models.CharField(max_length=150)
    during_state = models.CharField(max_length=32, choices=EquipmentState.choices)
    after_state = models.CharField(max_length=32, choices=EquipmentState.choices)
    allowed_prior_states = ArrayField(
        models.CharField(max_length=32, choices=EquipmentState.choices),
        help_text='Equipment statuses this activity can be started from.',
    )
    validity_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=(
            'How many days after_state remains valid before it automatically expires into '
            'expired_state. Blank means after_state never expires on its own.'
        ),
    )
    expired_state = models.CharField(
        max_length=32, choices=EquipmentState.choices, blank=True,
        help_text='Equipment state to move to once validity_days has elapsed. Required if validity_days is set.',
    )

    class Meta:
        ordering = ['usage_type__name', 'code']
        unique_together = [('usage_type', 'code')]
        verbose_name = 'Activity Rule'

    def __str__(self):
        return f'{self.usage_type.name} — {self.label}'

    def clean(self):
        from django.core.exceptions import ValidationError

        if bool(self.validity_days) != bool(self.expired_state):
            raise ValidationError('validity_days and expired_state must be set together, or both left blank.')


class ActivityLogEntry(models.Model):
    """One start-to-stop run of an activity on a piece of equipment.

    Every field below (besides the auto-stamped start/end bookkeeping) is
    filled once, when the activity is started — Stop Activity closes the
    entry without asking for anything further.
    """

    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name='log_entries')
    area_snapshot = models.CharField(
        max_length=200,
        help_text='Area path captured at entry time so later hierarchy edits do not rewrite history.',
    )
    usage_type = models.ForeignKey(EquipmentUsageType, on_delete=models.PROTECT)

    # Common to every usage type
    sap_document_no = models.CharField('SAP Document No', max_length=100, blank=True)

    # Process
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    batch_no = models.CharField('Batch No', max_length=100, blank=True)
    process_sub_type = models.CharField(
        'Process Sub Activity', max_length=20, choices=ProcessSubType.choices, blank=True
    )

    # Cleaning
    cleaning_sop_no = models.CharField('Cleaning SOP No', max_length=100, blank=True)
    cleaning_type = models.CharField(
        'Type of Cleaning', max_length=1, choices=CleaningType.choices, blank=True
    )
    adhered_material_removed = models.CharField(
        'Adhered Material Removed Within 24 Hours', max_length=3, choices=YesNo.choices, blank=True
    )

    # Maintenance
    equipment_maintenance_sop_no = models.CharField(
        'Maintenance SOP No', max_length=100, blank=True
    )
    maintenance_type = models.CharField(
        'Maintenance Type', max_length=20, choices=MaintenanceType.choices, blank=True
    )
    maintenance_frequency = models.CharField(
        max_length=20, choices=MaintenanceFrequency.choices, blank=True
    )
    pm_process_order_no = models.CharField('PM Process Order No', max_length=100, blank=True)

    # Qualification
    qualification_protocol_no = models.CharField(
        'Qualification Protocol No', max_length=100, blank=True
    )

    remarks = models.TextField(blank=True)

    start_date = models.DateField()
    start_time = models.TimeField()
    start_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='started_entries'
    )

    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    end_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='ended_entries',
    )

    status = models.CharField(
        max_length=20, choices=EntryStatus.choices, default=EntryStatus.IN_PROGRESS
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-start_time', '-id']
        verbose_name_plural = 'activity log entries'

    def __str__(self):
        return f'{self.equipment.code} — {self.start_date} {self.get_status_display()}'

    def save(self, *args, **kwargs):
        if not self.area_snapshot:
            self.area_snapshot = self.equipment.area.full_path
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.end_date is None

    @property
    def duration(self):
        """Elapsed time from start to end, or None while the entry is still open."""
        if not self.end_date or not self.end_time:
            return None
        start = datetime.datetime.combine(self.start_date, self.start_time)
        end = datetime.datetime.combine(self.end_date, self.end_time)
        return end - start

    @property
    def duration_display(self):
        """'1d 6h 17m'-style rendering of duration, or '' while still open."""
        delta = self.duration
        if delta is None:
            return ''
        total_minutes = int(delta.total_seconds() // 60)
        days, minutes_in_day = divmod(total_minutes, 24 * 60)
        hours, minutes = divmod(minutes_in_day, 60)
        parts = [f'{days}d'] if days else []
        if days or hours:
            parts.append(f'{hours}h')
        parts.append(f'{minutes}m')
        return ' '.join(parts)

    @property
    def equipment_status_at_entry(self):
        """The equipment status this entry represents at its own point in
        time — the rule's during-state while it's open, its after-state once
        completed. Not the equipment's *current* status, which may have moved
        on through later entries. None if no rule resolves (e.g. a legacy
        entry with no sub-activity recorded).
        """
        from masters.models import EquipmentState

        from . import rules

        rule = rules.get_rule_for_entry(self)
        if rule is None:
            return None
        return EquipmentState(rule.during_state if self.is_open else rule.after_state)
