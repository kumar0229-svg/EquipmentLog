# EquipmentLog — Deployment

How this app gets from a `git push` to running on EC2, and where every piece of deployment
configuration actually lives. **No credentials are recorded in this file, or anywhere in this
repo** — see [Credentials](#credentials--where-they-actually-live) for why, and where they are.

## Architecture

- **App server**: [gunicorn](https://gunicorn.org/) serving `config.wsgi:application`.
  `config/wsgi.py` reads an `X-Script-Name` header from the reverse proxy so the app can be
  served under a URL subpath (e.g. `/equipmentlog/`) instead of only at the domain root.
- **Reverse proxy**: not part of this repo — whatever sits in front of gunicorn on the EC2 box
  (nginx, etc.) is configured directly on the instance.
- **Database**: PostgreSQL, via `psycopg`.
- **Static files**: collected to `STATIC_ROOT` (`staticfiles/`) and served from `STATIC_URL`,
  which defaults to `static/` but can be overridden with `DJANGO_STATIC_URL` for subpath
  deployments.

## Environment variables

Read from a `.env` file at the project root (loaded by `python-dotenv`, never committed —
see `.gitignore`). `.env.example` documents the shape without real values:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django's `SECRET_KEY` — required, no default |
| `DJANGO_DEBUG` | `True`/`False`; must be `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames the app will answer for |
| `DJANGO_STATIC_URL` | Optional override for `STATIC_URL` (subpath deployments) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection |

## CI/CD — `.github/workflows/deploy.yml`

Triggers on every push to `main`, or manually via `workflow_dispatch`. It SSHes into the EC2
host and runs:

```bash
set -euo pipefail
cd /home/ubuntu/EquipmentLog
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
deactivate
sudo systemctl restart equipmentlog
```

So a push to `main` fully deploys itself: code, dependencies, migrations, static files, and a
gunicorn restart, with no manual step on the box afterward. `set -euo pipefail` is load-bearing —
without it, a failed step (e.g. a missing venv) is silently swallowed as long as the final
`systemctl restart` succeeds, and the workflow reports green despite nothing having actually
deployed. This requires the box's venv to already exist at `/home/ubuntu/EquipmentLog/venv`, a
systemd service named `equipmentlog` running gunicorn, and the SSH user to have passwordless
`sudo` for `systemctl restart equipmentlog` (see [First-time EC2 box
setup](#first-time-ec2-box-setup-one-time-manual)).

The SSH connection uses three **GitHub Actions repository secrets** (Settings → Secrets and
variables → Actions), not anything in this repo:

| Secret | Value |
| --- | --- |
| `EC2_HOST` | The instance's public IP or DNS name |
| `EC2_SSH_USER` | The SSH login user (e.g. `ubuntu`) |
| `EC2_SSH_KEY` | The private key for that user, PEM format |

## First-time EC2 box setup (one-time, manual)

1. Provision the instance; install Python 3.12+, PostgreSQL client libraries, and git.
2. `git clone` this repo to `/home/ubuntu/EquipmentLog`.
3. Create a venv at `venv` (must be this exact path — the deploy workflow activates it by
   name, and the systemd unit's `ExecStart` points at `venv/bin/gunicorn`) and
   `pip install -r requirements.txt`.
4. Create `.env` from `.env.example` with real production values (see above).
5. `python manage.py migrate`, `seed_masters`, `createsuperuser`, `collectstatic`.
6. Run gunicorn as a systemd service named `equipmentlog` (must be this exact name — the deploy
   workflow restarts it by name) and point a reverse proxy at it.
7. Grant the deploy SSH user passwordless `sudo` for `systemctl restart equipmentlog` only
   (e.g. a `visudo` entry scoped to that one command), so the workflow can restart gunicorn
   without a broader sudo grant.
8. Add `EC2_HOST` / `EC2_SSH_USER` / `EC2_SSH_KEY` as GitHub Actions secrets so future pushes
   can reach the box (see CI/CD above).

None of steps 4–8 are captured in this repo, since they're either secrets or host-specific
service configuration — this list exists so the setup can be reproduced on a replacement
instance, not to store the values themselves.

## Credentials — where they actually live

- **EC2 SSH access** (host, user, private key): GitHub Actions repository secrets. Not
  retrievable from this repo, its history, or by asking an assistant with repo access — only
  from GitHub's Settings → Secrets and variables → Actions page (or wherever your team records
  them, e.g. a password manager).
- **`DJANGO_SECRET_KEY`, database password**: the `.env` file on the EC2 instance itself.
  `.env` is git-ignored — it has never been committed and shouldn't be.

Nothing here is an oversight: a git-tracked file is the wrong place for either category, since
this repo has a GitHub remote and anything committed becomes part of its history.
