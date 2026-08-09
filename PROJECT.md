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
cd /home/ubuntu/EquipmentLog
git pull origin main
```

That's the entire automated step — see [What the pipeline doesn't do](#what-the-pipeline-doesnt-do)
below for what still has to happen manually after that.

The SSH connection uses three **GitHub Actions repository secrets** (Settings → Secrets and
variables → Actions), not anything in this repo:

| Secret | Value |
| --- | --- |
| `EC2_HOST` | The instance's public IP or DNS name |
| `EC2_SSH_USER` | The SSH login user (e.g. `ubuntu`) |
| `EC2_SSH_KEY` | The private key for that user, PEM format |

## What the pipeline doesn't do

`git pull` is all the workflow runs. It does **not**:

- `pip install -r requirements.txt` — needed after any dependency change
- `python manage.py migrate` — needed after any model change
- `python manage.py collectstatic` — needed after any static asset change
- restart the gunicorn process/service

Any deploy that touches those has to be finished by hand on the box (or the workflow extended
to cover them) — pushing to `main` alone won't pick them up.

## First-time EC2 box setup (one-time, manual)

1. Provision the instance; install Python 3.12+, PostgreSQL client libraries, and git.
2. `git clone` this repo to `/home/ubuntu/EquipmentLog`.
3. Create a venv and `pip install -r requirements.txt`.
4. Create `.env` from `.env.example` with real production values (see above).
5. `python manage.py migrate`, `seed_masters`, `createsuperuser`, `collectstatic`.
6. Run gunicorn as a long-lived service (e.g. a systemd unit) and point a reverse proxy at it.
7. Add `EC2_HOST` / `EC2_SSH_USER` / `EC2_SSH_KEY` as GitHub Actions secrets so future pushes
   can reach the box (see CI/CD above).

None of steps 4–7 are captured in this repo, since they're either secrets or host-specific
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
