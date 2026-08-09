# Electronic Equipment Activity Log (eEAL)

Django implementation of the Equipment Activity Log described in [PROJECT.md](PROJECT.md).

This build covers the **MVP + basic login/roles** scope: log entry, master data, the cleaning
validity engine, and role-based access. Full 21 CFR Part 11 e-signature re-authentication and an
immutable audit-trail table are deferred — see [Not yet implemented](#not-yet-implemented).

## Requirements

- Python 3.12+
- PostgreSQL 14+

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # Linux/macOS
```

Create the database and role:

```sql
CREATE ROLE equipmentlog WITH LOGIN PASSWORD '<password>';
CREATE DATABASE equipmentlog OWNER equipmentlog ENCODING 'UTF8';
ALTER ROLE equipmentlog CREATEDB;   -- only needed to run the test suite
```

Copy `.env.example` to `.env` and fill in the values, then:

```bash
python manage.py migrate
python manage.py seed_masters     # equipment types, usage types, cleaning validity rules
python manage.py createsuperuser
python manage.py runserver
```

## Apps

| App | Responsibility |
| --- | --- |
| `accounts` | Custom `User` with a `role` field, plus the `role_required` view gate |
| `masters` | Area hierarchy, equipment/usage types, equipment, products, cleaning rules |
| `activitylog` | The log entry model, validity engine, and all operator-facing views |

## Roles

| Role | Can do |
| --- | --- |
| Operator | Start and end activities, view dashboard and entries |
| Engineer | Everything an operator can, plus set equipment state directly |
| QA Reviewer | Verify closed entries, filter/export entries, manage the Area hierarchy in the admin |
| Production Section Head | Read-only dashboard scoped to their `section`, plus line-clearance sign-off |
| Administrator | Full Django admin: equipment, products, masters, users |

Roles are enforced server-side by `accounts.permissions.role_required`, not just hidden in
templates. Administrators and superusers pass every role gate.

## Area snapshots

Each entry stores `area_snapshot` — the equipment's area path at the time of entry. Renaming or
restructuring the Area hierarchy later does not rewrite historical records.

## Graphics dashboard

`activitylog/dashboard.py` turns the same data behind the equipment table into a KPI row and
three charts, rendered as inline SVG/HTML in `templates/activitylog/dashboard.html` (P1 item
in PROJECT.md — "color-coded overview of all equipment by area"):

- **Cleaning validity** — a stacked bar over Valid / Expiring (≤2 days) / Expired / No record.
- **Equipment state by area** — one stacked bar per Area/Stream over In Use / Under Maintenance /
  Idle and the other cycle statuses.
- **Activity trend** — entries started per day, trailing 14 days.

Colors are the fixed status palette (good/warning/critical/neutral), never reused for anything
else, and every chart ships a visible legend plus a collapsible data-table twin — the warning
yellow is intentionally low-contrast against the light background, so labels (not color alone)
carry the meaning. Section Heads see the same dashboard scoped to their own section.

## Tests

```bash
python manage.py test
```

Covers the validity date math, area snapshotting, and role-based access for every view.

## Not yet implemented

Deferred from PROJECT.md's P0 list for this build:

1. E-signature re-authentication on submission and QA verification (currently a session-login
   button press).
2. An immutable append-only audit trail. Entries carry `created_by`/`updated_at`/`verified_by`,
   and Django admin's `LogEntry` records master-data edits, but per-field before/after history
   with a reason-for-change is not captured.
3. The Area hierarchy is managed through Django admin rather than a dedicated QA screen.
