import random
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from activitylog import rules
from activitylog.models import ActivityLogEntry, CleaningType, EntryStatus, ProcessSubType, YesNo
from masters.models import EquipmentState, EquipmentUsageType, Product, ProductEquipment

User = get_user_model()

DEMO_MARKER = '[Demo data — generate_demo_activity]'

# Roughly how long each kind of activity runs, in hours (min, max) — just
# enough spread that a printed history doesn't look robotically uniform.
DURATION_HOURS = {
    ('Process', ProcessSubType.REACTION): (10, 20),
    ('Process', ProcessSubType.OTHER_EQUIPMENT): (6, 14),
    ('Cleaning', CleaningType.A): (2, 5),
    ('Cleaning', CleaningType.B): (3, 6),
    ('Cleaning', CleaningType.Q): (1, 3),
}

def _preference_for(equipment):
    """Preference order when several activities are startable from the
    equipment's current state — run the product's batches whenever possible,
    only falling back to whatever cleaning/QA step is needed to unblock the
    next run. REACTION is reactor-only (see ProcessSubType label), so the
    other process code for this equipment is excluded outright rather than
    merely deprioritised — both are simultaneously startable from every
    CLEANED_* state, and picking the wrong one would tag a centrifuge or
    ANFD run as a reaction.
    """
    is_reactor = equipment.equipment_type.name == 'Reactor'
    process_key = ('Process', ProcessSubType.REACTION if is_reactor else ProcessSubType.OTHER_EQUIPMENT)
    excluded_key = ('Process', ProcessSubType.OTHER_EQUIPMENT if is_reactor else ProcessSubType.REACTION)
    order = [process_key, ('Cleaning', CleaningType.A), ('Cleaning', CleaningType.Q), ('Cleaning', CleaningType.B)]
    return order, excluded_key


class Command(BaseCommand):
    help = (
        'Backfill a demo activity history for every equipment mapped to a product, so its usage '
        'over the last N days shows up in the Activity Log. Safe to re-run: equipment with entries '
        'already inside the window picks up from wherever its last entry left off, rather than '
        'duplicating or overwriting anything.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--product', default='Product-1', help='Product name (default: Product-1).')
        parser.add_argument(
            '--days', type=int, default=10, help='How many days of history to backfill (default: 10).'
        )
        parser.add_argument(
            '--user', default=None,
            help='Username to attribute generated entries to (default: first superuser).',
        )
        parser.add_argument(
            '--dry-run', action='store_true', help='Report what would be created without writing anything.'
        )

    def handle(self, *args, **options):
        product = self._resolve_product(options['product'])
        actor = self._resolve_user(options['user'])
        process_type, cleaning_type = self._resolve_usage_types()
        dry_run = options['dry_run']

        # Naive local wall-clock datetimes throughout — start_date/start_time
        # are plain (non-timezone-aware) fields populated from
        # timezone.localtime() everywhere else in this app (see
        # activitylog.views._server_date_and_time), so history built here
        # must line up with that same clock, not UTC.
        now = timezone.localtime().replace(tzinfo=None)
        window_start = now - timedelta(days=options['days'])

        cleaning_sop_by_equipment = {
            link.equipment_id: link.cleaning_sop_no
            for link in ProductEquipment.objects.filter(product=product)
        }
        equipment_list = list(product.equipment.select_related('equipment_type').order_by('code'))
        if not equipment_list:
            self.stdout.write(self.style.WARNING(f'No equipment mapped to "{product.name}" — nothing to do.'))
            return

        created_total = 0
        touched = 0
        blocked = []

        for equipment in equipment_list:
            last_entry = (
                ActivityLogEntry.objects.filter(equipment=equipment)
                .order_by('-start_date', '-start_time')
                .first()
            )
            if last_entry and last_entry.end_date is None:
                blocked.append(equipment.code)  # currently mid-activity — nothing new can start
                continue

            history_start = window_start
            if last_entry and last_entry.end_date:
                last_end = datetime.combine(last_entry.end_date, last_entry.end_time)
                history_start = max(history_start, last_end)

            entries, final_state = self._build_history(
                equipment, product, process_type, cleaning_type,
                cleaning_sop_by_equipment.get(equipment.id, ''), history_start, now, actor,
            )
            if not entries:
                continue  # already caught up to now

            created_total += len(entries)
            touched += 1
            if dry_run:
                self.stdout.write(f'{equipment.code}: would create {len(entries)} entries, ending {final_state}')
                continue

            with transaction.atomic():
                for entry in entries:
                    entry.save()
                equipment.state = final_state
                equipment.save(update_fields=['state'])
            self.stdout.write(f'{equipment.code}: created {len(entries)} entries, now {final_state}')

        verb = 'Would create' if dry_run else 'Created'
        self.stdout.write(self.style.SUCCESS(f'{verb} {created_total} demo entries across {touched} equipment.'))
        if blocked:
            self.stdout.write(self.style.WARNING(
                f'Skipped (currently mid-activity, no valid next step): {", ".join(blocked)}'
            ))

    def _resolve_product(self, product_name):
        try:
            return Product.objects.get(name=product_name)
        except Product.DoesNotExist:
            raise CommandError(f'No product named "{product_name}".')

    def _resolve_user(self, username):
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'No user named "{username}".')
        actor = (
            User.objects.filter(is_superuser=True).order_by('id').first()
            or User.objects.filter(is_active=True).order_by('id').first()
        )
        if actor is None:
            raise CommandError('No users exist to attribute generated entries to — pass --user.')
        return actor

    def _resolve_usage_types(self):
        usage_types = {ut.name: ut for ut in EquipmentUsageType.objects.filter(name__in=['Process', 'Cleaning'])}
        if 'Process' not in usage_types or 'Cleaning' not in usage_types:
            raise CommandError('Process/Cleaning usage types not seeded — run `manage.py seed_masters` first.')
        return usage_types['Process'], usage_types['Cleaning']

    def _pick_action(self, state, preference_order, excluded_key):
        """(usage_type_name, code, rule) to run next from `state`, preferring
        `preference_order` and never returning `excluded_key`. Falls back to
        any other startable activity, and to None if nothing can start
        (equipment is already mid-activity).
        """
        available = {
            (usage_type_name, code): rule for usage_type_name, code, rule in rules.next_actions_for_state(state)
            if (usage_type_name, code) != excluded_key
        }
        for key in preference_order:
            if key in available:
                return key[0], key[1], available[key]
        if available:
            (usage_type_name, code), rule = next(iter(available.items()))
            return usage_type_name, code, rule
        return None

    def _build_history(self, equipment, product, process_type, cleaning_type, cleaning_sop_no, start, now, actor):
        """Walk the equipment's current state forward through valid rule
        transitions from `start` to `now`, alternating product batches with
        the cleaning/QA steps needed between them. Returns (unsaved
        ActivityLogEntry list, state equipment should end up in).
        """
        state = equipment.state or EquipmentState.NOT_IN_USE
        preference_order, excluded_key = _preference_for(equipment)
        cursor = start
        entries = []
        batch_seq = 1

        while cursor < now:
            action = self._pick_action(state, preference_order, excluded_key)
            if action is None:
                break
            usage_type_name, code, rule = action

            low, high = DURATION_HOURS.get((usage_type_name, code), (4, 8))
            end = cursor + timedelta(hours=random.uniform(low, high))

            entry = ActivityLogEntry(
                equipment=equipment,
                usage_type=process_type if usage_type_name == 'Process' else cleaning_type,
                remarks=DEMO_MARKER,
                start_date=cursor.date(), start_time=cursor.time().replace(second=0, microsecond=0),
                start_by=actor, created_by=actor,
            )
            if usage_type_name == 'Process':
                entry.product = product
                entry.process_sub_type = code
                entry.batch_no = f'{product.name}-DEMO-{equipment.code}-{batch_seq:02d}'
                batch_seq += 1
            else:
                entry.cleaning_type = code
                entry.cleaning_sop_no = cleaning_sop_no
                entry.adhered_material_removed = YesNo.YES

            if end >= now:
                entries.append(entry)  # left open — this is equipment's current, live activity
                state = rule.during_state
                break

            entry.end_date, entry.end_time = end.date(), end.time().replace(second=0, microsecond=0)
            entry.end_by = actor
            entry.status = EntryStatus.COMPLETED
            entries.append(entry)
            state = rule.after_state
            cursor = end

        return entries, state
