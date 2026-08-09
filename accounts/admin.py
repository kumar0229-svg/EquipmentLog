from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'department', 'section', 'is_active']
    list_filter = ['role', 'department', 'section', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Equipment Log profile', {'fields': ('role', 'department', 'section')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Equipment Log profile', {'fields': ('role', 'department', 'section')}),
    )
