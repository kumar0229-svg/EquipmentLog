from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import path, reverse

from masters.models import EquipmentState

from . import rules
from .models import ActivityLogEntry


@admin.register(ActivityLogEntry)
class ActivityLogEntryAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'usage_type', 'start_date', 'status']
    list_filter = ['usage_type', 'status']
    search_fields = ['equipment__code', 'batch_no']


@staff_member_required
def activity_rules_view(request):
    """Read-only reference view of rules.ACTIVITY_RULES — the same table that
    drives Start Activity's status validation, laid out the way it's
    documented (Activity / Sub Activity / Status during / Status after /
    which statuses allow it), so admins can read the cycle without reading
    Python.
    """
    rows = [
        {
            'activity': usage_type_name,
            'sub_activity': rule.label,
            'during': EquipmentState(rule.during_state).label,
            'after': EquipmentState(rule.after_state).label,
            'allowed_from': sorted(EquipmentState(s).label for s in rule.allowed_prior_states),
        }
        for (usage_type_name, code), rule in rules.ACTIVITY_RULES.items()
    ]
    context = {
        **admin.site.each_context(request),
        'title': 'Activity Rules',
        'rows': rows,
    }
    return render(request, 'admin/activitylog/activity_rules.html', context)


# Django's admin has no built-in slot for a non-model reference page, so it's
# wired in the two documented extension points: a URL under admin.site, and
# an entry in get_app_list so it actually shows up on the admin index instead
# of being a hidden URL.
_default_get_urls = admin.site.get_urls


def _get_urls_with_activity_rules():
    return [
        path('activity-rules/', admin.site.admin_view(activity_rules_view), name='activity_rules'),
    ] + _default_get_urls()


admin.site.get_urls = _get_urls_with_activity_rules

_default_get_app_list = admin.site.get_app_list


def _get_app_list_with_activity_rules(request, app_label=None):
    app_list = _default_get_app_list(request, app_label=app_label)
    app_list.append(
        {
            'name': 'Activity Rules',
            'app_label': 'activity_rules_reference',
            'app_url': reverse('admin:activity_rules'),
            'has_module_perms': True,
            'models': [
                {
                    'name': 'Status cycle reference',
                    'object_name': 'ActivityRules',
                    'admin_url': reverse('admin:activity_rules'),
                    'view_only': True,
                }
            ],
        }
    )
    return app_list


admin.site.get_app_list = _get_app_list_with_activity_rules
