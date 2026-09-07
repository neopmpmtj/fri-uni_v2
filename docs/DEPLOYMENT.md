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
4. `.venv/bin/pip install -r requirements.txt`
5. `.venv/bin/python manage.py migrate --noinput`
6. `.venv/bin/python manage.py collectstatic --noinput`
7. Install systemd unit from [`deploy/gunicorn.service`](../deploy/gunicorn.service) (edit paths).
8. Install nginx site from [`deploy/nginx.conf`](../deploy/nginx.conf) (edit domain + paths).
9. For PDF download (WeasyPrint), install Debian packages: `pango1.0-tools` / `libpango-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0`, and related fonts (e.g. `fonts-dejavu-core`).

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
