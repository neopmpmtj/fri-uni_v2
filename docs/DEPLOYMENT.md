# Deploying fri-uni

Develop locally, push to origin, pull on the VPS, run [`scripts/deploy.sh`](../scripts/deploy.sh).

## Settings modules

| Environment | Module | How chosen |
|-------------|--------|------------|
| Local dev | `conf.settings.dev` | default in `manage.py` |
| Tests | `conf.settings.test` | `manage.py test` auto-selects |
| Production | `conf.settings.prod` | `DJANGO_SETTINGS_MODULE` in systemd |

Secrets live in `.env` (gitignored). Copy [`.env.example`](../.env.example) as the template.

## Local setup

```bash
cp .env.example .env
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## One-time VPS setup

1. Install PostgreSQL, nginx, Python venv support.
2. Clone repo to e.g. `/srv/fri-uni/`.
3. Create `.env` with at minimum:
   - `DJANGO_SETTINGS_MODULE=conf.settings.prod`
   - `DATABASE_URL=postgres://...`
   - `DJANGO_SECRET_KEY=...`
   - `ALLOWED_HOSTS=your.domain`
   - `AGENT_PASSWORD=…` and `AGENT_ADMIN_PASSWORD=…` (Pi CLI badges; never commit)
4. `.venv/bin/pip install -r requirements.txt`
5. `.venv/bin/python manage.py migrate --noinput`
6. `.venv/bin/python manage.py collectstatic --noinput`
7. One-time agent users (not part of every deploy):

```bash
.venv/bin/python manage.py seed_prod
# or override .env:
.venv/bin/python manage.py seed_prod --password '…' --admin-password '…'
```

Creates `agent@fribila.dev` (staff) and `agent-admin@fribila.dev` (admin, Django admin). Idempotent. Do **not** run `seed_demo` on the VPS (fake clients and quotes).
8. Install systemd unit from [`deploy/gunicorn.service`](../deploy/gunicorn.service) (edit paths).
9. Install nginx site from [`deploy/nginx.conf`](../deploy/nginx.conf) (edit domain + paths).
10. For PDF download (WeasyPrint), install Debian packages: `pango1.0-tools` / `libpango-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0`, and related fonts (e.g. `fonts-dejavu-core`). PDF render errors surface as a flash message on the proforma detail page (not HTTP 500). A hung WeasyPrint worker is mitigated by gunicorn `--timeout 120` in [`deploy/gunicorn.service`](../deploy/gunicorn.service); there is no application-level PDF timeout yet (see project-plan backlog).

## Every deploy

```bash
cd /srv/fri-uni
git pull
SERVICE_NAME=fri-uni-gunicorn ./scripts/deploy.sh
sudo systemctl restart fri-uni-gunicorn
```

Or run the steps in `scripts/deploy.sh` manually.

## Docs layout

- [`docs/handoff.md`](handoff.md) — session snapshot (living)
- [`docs/project-plan.md`](project-plan.md) — durable backlog (living)
- [`docs/reviews/`](reviews/) — in-progress review docs
- [`docs/archive/`](archive/) — concluded reviews and old material
