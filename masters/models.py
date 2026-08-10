from django.db import models


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


class EquipmentType(models.Model):
    name = models.CharField(max_length=100, unique=True)
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
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name_plural = 'equipment'

    def __str__(self):
        return f'{self.code} — {self.equipment_type.name}'


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


class ProductEquipment(models.Model):
    """Which equipment a product may run on, and the procedure it runs under there.

    Start Activity only offers an equipment's Process product choices from
    this mapping (masters.forms/views equipment_context_map) — an equipment
    with no rows here is left unrestricted rather than blocked, matching how
    unconfigured usage-type field maps behave elsewhere in the app.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='equipment_links')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='product_links')
    procedure_no = models.CharField('Procedure No', max_length=100, blank=True)

    class Meta:
        ordering = ['product__name', 'equipment__code']
        unique_together = [('product', 'equipment')]

    def __str__(self):
        return f'{self.product.name} on {self.equipment.code}'


