from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    OPERATOR = 'OPERATOR', 'Operator'
    ENGINEER = 'ENGINEER', 'Engineer'
    QA = 'QA', 'QA Reviewer'
    SECTION_HEAD = 'SECTION_HEAD', 'Production Section Head'
    ADMIN = 'ADMIN', 'Administrator'


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)
    department = models.CharField(max_length=100, blank=True)
    section = models.CharField(max_length=100, blank=True)
    default_stream = models.ForeignKey(
        'masters.Area', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        help_text='Stream the Dashboard opens to by default — set automatically when a stream is picked there.',
    )

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_qa(self):
        return self.role == Role.QA

    @property
    def is_operator(self):
        return self.role == Role.OPERATOR

    @property
    def is_engineer(self):
        return self.role == Role.ENGINEER

    @property
    def is_section_head(self):
        return self.role == Role.SECTION_HEAD

    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN or self.is_superuser
