"""Cleaned-status validity: rules with a validity_days set on their
after_state (see ActivityRuleConfig, admin ▸ Activity Log ▸ Activity rule
configs) leave equipment in that state only so long — past that, the
equipment auto-reverts to the rule's expired_state.

There's no Celery/cron in this app, so this is invoked two ways:
- lazily, at the top of every view that reads or displays live equipment
  state (dashboard, equipment_list, start_activity) — self-healing, no ops
  setup required
- via `python manage.py expire_equipment_states`, for an admin who wants
  status to flip closer to the actual deadline than "whenever someone next
  loads a page" — wire it into Windows Task Scheduler/cron if that matters.
"""

from datetime import timedelta

from django.utils import timezone

from masters.models import Equipment

from . import rules


def expire_stale_equipment_states():
    """Move every equipment whose current state has outlived its rule's
    validity_days into that rule's expired_state. Returns the count updated.
    """
    expirable = {
        rule.after_state: rule for rule in rules.get_rules_dict().values() if rule.validity_days
    }
    if not expirable:
        return 0

    now = timezone.now()
    updated = 0
    for equipment in Equipment.objects.filter(state__in=expirable, state_changed_at__isnull=False):
        rule = expirable[equipment.state]
        if now >= equipment.state_changed_at + timedelta(days=rule.validity_days):
            equipment.state = rule.expired_state
            equipment.save(update_fields=['state'])
            updated += 1
    return updated
