from django import forms
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import path, reverse

from masters.models import EquipmentState

from . import rules
from .models import ActivityLogEntry, ActivityRuleConfig


@admin.register(ActivityLogEntry)
class ActivityLogEntryAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'usage_type', 'start_date', 'status']
    list_filter = ['usage_type', 'status']
    search_fields = ['equipment__code', 'batch_no']


class ActivityRuleConfigForm(forms.ModelForm):
    # ArrayField's default form field renders as a bare comma-separated text
    # box; a checkbox list against the same EquipmentState choices is a lot
    # harder to fat-finger into an invalid status string.
    allowed_prior_states = forms.MultipleChoiceField(
        choices=EquipmentState.choices, widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = ActivityRuleConfig
        fields = '__all__'


@admin.register(ActivityRuleConfig)
class ActivityRuleConfigAdmin(admin.ModelAdmin):
    """Procedure/status-cycle values, not routine master data — same access
    rule as the Area hierarchy in masters/admin.py (QA or Admin), rather than
    the stricter Admin-only default most master data uses.
    """

    form = ActivityRuleConfigForm
    list_display = [
        'usage_type', 'code', 'label', 'during_state', 'after_state', 'validity_days', 'expired_state',
    ]
    list_filter = ['usage_type']
    search_fields = ['code', 'label']

    def _can_edit(self, request):
        return request.user.is_authenticated and (
            request.user.is_qa or request.user.is_admin_role
        )

    def has_add_permission(self, request):
        return self._can_edit(request)

    def has_change_permission(self, request, obj=None):
        return self._can_edit(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_edit(request)


@staff_member_required
def activity_rules_view(request):
    """Read-only reference view of rules.get_rules_dict() — the same table
    that drives Start Activity's status validation, laid out the way it's
    documented (Activity / Sub Activity / Status during / Status after /
    which statuses allow it), so admins can read the cycle at a glance.
    Edit the underlying rows under Activity Log ▸ Activity rules.
    """
    rows = [
        {
            'activity': usage_type_name,
            'sub_activity': rule.label,
            'during': EquipmentState(rule.during_state).label,
            'after': EquipmentState(rule.after_state).label,
            'allowed_from': sorted(EquipmentState(s).label for s in rule.allowed_prior_states),
            'validity_days': rule.validity_days,
            'expired_after': EquipmentState(rule.expired_state).label if rule.expired_state else '',
        }
        for (usage_type_name, code), rule in rules.get_rules_dict().items()
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
