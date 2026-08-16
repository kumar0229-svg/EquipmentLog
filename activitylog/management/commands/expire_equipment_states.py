from django.core.management.base import BaseCommand

from activitylog.expiry import expire_stale_equipment_states


class Command(BaseCommand):
    help = (
        'Revert equipment out of a lapsed cleaned status (past its rule\'s validity_days) into '
        'that rule\'s expired_state. This already runs lazily on every authenticated request '
        '(activitylog.middleware.ExpireCleaningValidityMiddleware) — schedule this command '
        '(e.g. every 15-30 min via Windows Task Scheduler or cron) only if you want status to '
        'flip closer to the actual deadline than "whenever someone next loads a page".'
    )

    def handle(self, *args, **options):
        updated = expire_stale_equipment_states()
        self.stdout.write(self.style.SUCCESS(f'Expired cleaning validity on {updated} equipment.'))
