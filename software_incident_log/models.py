from django.conf import settings
from django.db import models

from masters.models import ComputerizedSystem


class IncidentStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    CLOSED = 'CLOSED', 'Closed'


class IncidentCategory(models.TextChoices):
    CRITICAL = 'CRITICAL', 'Critical'
    MAJOR = 'MAJOR', 'Major'
    MINOR = 'MINOR', 'Minor'


class ValidationRequired(models.TextChoices):
    YES = 'YES', 'Yes'
    NO = 'NO', 'No'
    NA = 'NA', 'Not Applicable'


class SoftwareIncidentEntry(models.Model):
    """One row of the Incidence Log of Computerized System.

    Incident No is entered by hand (must not repeat) alongside the system
    and description — Logged Date and Logged By are stamped automatically.
    The entry stays Open until QA fills in the closeout fields (category,
    validation required) and verifies it.
    """

    incident_no = models.CharField(max_length=20, unique=True)
    system = models.ForeignKey(
        ComputerizedSystem, on_delete=models.PROTECT, related_name='incidents',
        verbose_name='Name of the Computerized System',
    )
    logged_date = models.DateField(auto_now_add=True)
    description = models.TextField('Brief Description of Issue')
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='incidents_logged',
    )

    status = models.CharField(max_length=10, choices=IncidentStatus.choices, default=IncidentStatus.OPEN)

    # Closeout fields — blank until QA closes the entry out.
    category = models.CharField(max_length=10, choices=IncidentCategory.choices, blank=True)
    validation_required = models.CharField(
        'Any Validation / Performance Required', max_length=5, choices=ValidationRequired.choices, blank=True,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='incidents_verified',
        null=True, blank=True,
    )
    closeout_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Software Incident Entry'
        verbose_name_plural = 'Software Incident Entries'

    def __str__(self):
        return self.incident_no

    @property
    def is_open(self):
        return self.status == IncidentStatus.OPEN
