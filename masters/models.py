from django.db import models
from django.utils import timezone


class AreaType(models.TextChoices):
    BLOCK = 'BLOCK', 'Production Block'
    STREAM = 'STREAM', 'Area / Stream'
    LOCATION = 'LOCATION', 'Floor Location'
    CUBICLE = 'CUBICLE', 'Cubicle'


class Area(models.Model):
    name = models.CharField(max_length=100)
    area_type = models.CharField(max_length=10, choices=AreaType.choices)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.PROTECT, related_name='children'
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'parent')]

    def __str__(self):
        return self.full_path

    @property
    def full_path(self):
        return f'{self.parent.full_path} / {self.name}' if self.parent else self.name

    def descendant_ids(self):
        """This area's id plus every descendant's id, at any depth."""
        ids = [self.id]
        frontier = [self.id]
        while frontier:
            frontier = list(Area.objects.filter(parent_id__in=frontier).values_list('id', flat=True))
            ids.extend(frontier)
        return ids


class UnitOfMeasurement(models.Model):
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=20, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'unit of measurement'
        verbose_name_plural = 'units of measurement'

    def __str__(self):
        return f'{self.name} ({self.symbol})' if self.symbol else self.name


class EquipmentType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    capacity_uom = models.ForeignKey(
        UnitOfMeasurement, null=True, blank=True, on_delete=models.PROTECT, related_name='+',
        verbose_name='Capacity UOM',
        help_text='Unit of measurement for Capacity across all equipment of this type.',
    )
    surface_area_uom = models.ForeignKey(
        UnitOfMeasurement, null=True, blank=True, on_delete=models.PROTECT, related_name='+',
        verbose_name='Total Surface Area UOM',
        help_text='Unit of measurement for Total Surface Area across all equipment of this type.',
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class EquipmentUsageType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class EquipmentState(models.TextChoices):
    IN_PROCESS = 'IN_PROCESS', 'In-Process'
    IN_USE = 'IN_USE', 'In Use'
    TO_BE_PRESERVED = 'TO_BE_PRESERVED', 'To Be Preserved'
    UNDER_CLEANING = 'UNDER_CLEANING', 'Under Cleaning'
    TO_BE_CLEANED = 'TO_BE_CLEANED', 'To Be Cleaned'
    TO_BE_CLEANED_AFTER_MAINTENANCE = (
        'TO_BE_CLEANED_AFTER_MAINTENANCE', 'To Be Cleaned (After Maintenance)'
    )
    CLEANED_TYPE_A = 'CLEANED_TYPE_A', 'Cleaned Type A'
    CLEANED_READY_FOR_QA = 'CLEANED_READY_FOR_QA', 'Cleaned and Ready for QA Certification'
    UNDER_QA_CERTIFICATION = 'UNDER_QA_CERTIFICATION', 'Under QA Certification'
    CLEANED_AND_QA_CERTIFIED = 'CLEANED_AND_QA_CERTIFIED', 'Cleaned and QA Certified'
    CLEANED_AFTER_MAINTENANCE = 'CLEANED_AFTER_MAINTENANCE', 'Cleaned After Maintenance'
    UNDER_MAINTENANCE = 'UNDER_MAINTENANCE', 'Under Maintenance'
    UNDER_QUALIFICATION = 'UNDER_QUALIFICATION', 'Under Qualification'
    NOT_IN_USE = 'NOT_IN_USE', 'Idle'


class Equipment(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150, blank=True)
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.PROTECT)
    department = models.CharField(max_length=100, blank=True)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='equipment')
    is_movable = models.BooleanField(default=False)
    state = models.CharField(
        max_length=32, choices=EquipmentState.choices, default=EquipmentState.NOT_IN_USE
    )
    state_changed_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When `state` last changed — the anchor point for cleaning validity expiry.',
    )
    active = models.BooleanField(default=True)

    capacity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    material_of_construction = models.CharField('Material of Construction', max_length=100, blank=True)
    total_surface_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_oq_date = models.DateField('Last Major Qualification (OQ) Date', null=True, blank=True)

    class Meta:
        ordering = ['code']
        verbose_name_plural = 'equipment'

    def __str__(self):
        return f'{self.code} — {self.equipment_type.name}'

    def save(self, *args, **kwargs):
        """Stamp state_changed_at whenever `state` actually changes — the
        anchor cleaning-validity expiry (activitylog.expiry) counts from.
        Handles both `update_fields=['state']` saves (activitylog.views
        start_activity/stop_activity) and full-form admin saves without
        every call site having to remember to set it.
        """
        update_fields = kwargs.get('update_fields')
        is_new = self.pk is None
        state_may_change = update_fields is None or 'state' in update_fields
        if not is_new and state_may_change:
            old_state = Equipment.objects.filter(pk=self.pk).values_list('state', flat=True).first()
            state_may_change = old_state is not None and old_state != self.state
        if is_new or state_may_change:
            self.state_changed_at = timezone.now()
            if update_fields is not None and 'state_changed_at' not in update_fields:
                kwargs['update_fields'] = list(update_fields) + ['state_changed_at']
        super().save(*args, **kwargs)

    def _with_uom(self, value, uom):
        if value is None:
            return ''
        return f'{value} {uom.symbol}' if uom and uom.symbol else str(value)

    @property
    def capacity_display(self):
        return self._with_uom(self.capacity, self.equipment_type.capacity_uom)

    @property
    def total_surface_area_display(self):
        return self._with_uom(self.total_surface_area, self.equipment_type.surface_area_uom)


class Product(models.Model):
    name = models.CharField(max_length=150, unique=True)
    streams = models.ManyToManyField(
        Area,
        blank=True,
        related_name='products',
        limit_choices_to={'area_type': AreaType.STREAM},
        help_text='Streams this product is manufactured in.',
    )
    equipment = models.ManyToManyField(
        Equipment, through='ProductEquipment', blank=True, related_name='products',
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SiteSetting(models.Model):
    """Site-wide values that show up on printed output (e.g. the Equipment
    Activity Log printout header). Only one row is expected to ever exist —
    the admin restricts adding a second one — so callers just take the first.
    """

    location = models.CharField(
        max_length=150,
        default='Bommasandra',
        help_text='Printed under the logo on report headers, e.g. "Bommasandra".',
    )

    class Meta:
        verbose_name = 'Site Setting'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return self.location

    @classmethod
    def get_location(cls):
        setting = cls.objects.first()
        return setting.location if setting else cls._meta.get_field('location').default


class ProductEquipment(models.Model):
    """Which equipment a product may run on, and the SOP that governs both
    running that product on the equipment and cleaning it afterwards — one
    number covers both.

    Start Activity only offers an equipment's Process product choices from
    this mapping, and suggests a Cleaning SOP No from it based on the
    product last processed on the equipment (activitylog.forms
    equipment_context_map) — an equipment with no rows here is left
    unrestricted rather than blocked, matching how unconfigured usage-type
    field maps behave elsewhere in the app.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='equipment_links')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='product_links')
    cleaning_sop_no = models.CharField(
        'Cleaning SOP No', max_length=100, blank=True,
        help_text='SOP for running this product on this equipment and for cleaning it afterwards.',
    )

    class Meta:
        ordering = ['product__name', 'equipment__code']
        unique_together = [('product', 'equipment')]

    def __str__(self):
        return f'{self.product.name} on {self.equipment.code}'


