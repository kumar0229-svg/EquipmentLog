from django.contrib import admin

from .models import SoftwareIncidentEntry


@admin.register(SoftwareIncidentEntry)
class SoftwareIncidentEntryAdmin(admin.ModelAdmin):
    list_display = ['incident_no', 'system', 'logged_date', 'logged_by', 'status', 'category']
    list_filter = ['status', 'category', 'system']
    search_fields = ['incident_no', 'description']
    readonly_fields = ['logged_date', 'created_at']
