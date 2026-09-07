#!/usr/bin/env bash
#
# bootstrap.sh — scaffold a new Django + Cursor project in the current directory.
#
# Usage:
#   ./bootstrap.sh
#   ./bootstrap.sh --force   # overwrite scaffold files if they already exist
#   BOOTSTRAP_AUTH=email ./bootstrap.sh   # non-interactive: poc | email
#
set -euo pipefail

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
elif [[ -n "${1:-}" ]]; then
  echo "Usage: $0 [--force]" >&2
  echo "  BOOTSTRAP_AUTH=poc|email  non-interactive auth choice" >&2
  exit 1
fi

PROJECT_NAME="$(basename "$PWD")"

write_file() {
  local path="$1"
  local parent
  parent="$(dirname "$path")"
  if [[ "$parent" != "." ]]; then
    mkdir -p "$parent"
  fi
  if [[ -f "$path" && "$FORCE" -eq 0 ]]; then
    echo "skip: $path"
    return 0
  fi
  cat >"$path"
  echo "write: $path"
}

write_empty() {
  local path="$1"
  local parent
  parent="$(dirname "$path")"
  if [[ "$parent" != "." ]]; then
    mkdir -p "$parent"
  fi
  if [[ -f "$path" && "$FORCE" -eq 0 ]]; then
    echo "skip: $path"
    return 0
  fi
  : >"$path"
  echo "write: $path"
}

echo "Bootstrapping project: $PROJECT_NAME"

# --- Auth mode: POC (default Django user) or email-based accounts app ---

choose_auth_mode() {
  if [[ -n "${BOOTSTRAP_AUTH:-}" ]]; then
    case "$BOOTSTRAP_AUTH" in
      poc|email) AUTH_MODE="$BOOTSTRAP_AUTH" ;;
      *)
        echo "Error: BOOTSTRAP_AUTH must be 'poc' or 'email'" >&2
        exit 1
        ;;
    esac
    echo "auth: $AUTH_MODE (BOOTSTRAP_AUTH)"
    return
  fi
  if [[ -d accounts && -f accounts/models.py ]]; then
    AUTH_MODE="email"
    echo "auth: email (existing accounts app)"
    return
  fi
  if [[ ! -t 0 ]]; then
    AUTH_MODE="poc"
    echo "auth: poc (non-interactive default)"
    return
  fi
  echo ""
  echo "Authentication setup:"
  echo "  1) POC / minimal — default Django user (username); no custom auth app"
  echo "  2) Email login — accounts app with email User (Google OAuth-ready fields)"
  read -r -p "Choice [1]: " auth_choice
  case "${auth_choice:-1}" in
    2) AUTH_MODE="email" ;;
    *) AUTH_MODE="poc" ;;
  esac
  echo "auth: $AUTH_MODE"
}

choose_auth_mode

write_accounts_app() {
  write_empty accounts/__init__.py
  write_empty accounts/migrations/__init__.py

  write_file accounts/apps.py <<'EOF'
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
EOF

  write_file accounts/models.py <<'EOF'
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_google_account = models.BooleanField(
        default=False,
        help_text="True once the user has authenticated via Google OAuth.",
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Set when email is verified (e.g. via Google OAuth).",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
EOF

  write_file accounts/admin.py <<'EOF'
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_superuser", "is_active", "is_google_account")
    list_filter = ("is_staff", "is_superuser", "is_active", "is_google_account")
    search_fields = ("email", "first_name", "last_name")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "OAuth",
            {"fields": ("is_google_account", "is_email_verified")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
EOF

  write_empty accounts/views.py
  write_empty accounts/tests.py
}

# --- Django ---

write_file manage.py <<'EOF'
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from decouple import config


def main():
    """Run administrative tasks."""
    if "test" in sys.argv:
        os.environ["DJANGO_SETTINGS_MODULE"] = "conf.settings.test"
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        config("DJANGO_SETTINGS_MODULE", default="conf.settings.dev"),
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
EOF

write_empty conf/__init__.py

write_file conf/urls.py <<'EOF'
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
EOF

write_file conf/wsgi.py <<'EOF'
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings.dev")

application = get_wsgi_application()
EOF

write_file conf/asgi.py <<'EOF'
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings.dev")

application = get_asgi_application()
EOF

write_empty conf/settings/__init__.py

if [[ "$AUTH_MODE" == "email" ]]; then
  write_accounts_app
  write_file conf/settings/base.py <<'EOF'
"""Shared Django settings."""

import sys
from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TESTING = "test" in sys.argv

SECRET_KEY = "django-insecure-dev-only-change-in-production"

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "conf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "conf.wsgi.application"

_database_url = config("DATABASE_URL", default="")
if _database_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=_database_url,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EOF
else
  write_file conf/settings/base.py <<'EOF'
"""Shared Django settings."""

import sys
from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TESTING = "test" in sys.argv

SECRET_KEY = "django-insecure-dev-only-change-in-production"

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "conf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "conf.wsgi.application"

_database_url = config("DATABASE_URL", default="")
if _database_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=_database_url,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EOF
fi

write_file conf/settings/dev.py <<'EOF'
"""Development settings — local machine (relaxed security)."""

from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = True

SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-change-in-production",
)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv(), default="localhost,127.0.0.1")

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EOF

write_file conf/settings/test.py <<'EOF'
"""Test settings — fast hasher (used automatically by manage.py test)."""

from .dev import *  # noqa: F401,F403

TESTING = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EOF

write_file conf/settings/prod.py <<'EOF'
"""Production settings — VPS (strict security).

Requires in server .env:
    DATABASE_URL, DJANGO_SECRET_KEY (or SECRET_KEY), ALLOWED_HOSTS
Set SECURE_SSL_REDIRECT=True only after TLS (certbot) is serving 443.
"""

from django.core.exceptions import ImproperlyConfigured

from decouple import Csv, config

from .base import *  # noqa: F401,F403

DEBUG = False

if not config("DATABASE_URL", default=""):
    raise ImproperlyConfigured("DATABASE_URL is required in production.")

SECRET_KEY = config("DJANGO_SECRET_KEY", default="") or config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_COOKIES = config("SECURE_COOKIES", default=SECURE_SSL_REDIRECT, cast=bool)
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = bool(SECURE_SSL_REDIRECT)
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv(), default="")
EOF

# --- Boilerplate ---

write_file requirements.txt <<'EOF'
Django>=5.0,<6
python-decouple>=3.8
dj-database-url>=2.1
psycopg[binary]>=3.1,<4
gunicorn>=21.2
whitenoise>=6.6
pytest>=8.0
pytest-django>=4.8
EOF

write_file .env.example <<'EOF'
# Local development (copy to .env)
DJANGO_SETTINGS_MODULE=conf.settings.dev
DJANGO_SECRET_KEY=change-me-dev-only
ALLOWED_HOSTS=localhost,127.0.0.1
DEBUG=True

# Optional: use PostgreSQL locally instead of SQLite
# DATABASE_URL=postgres://appuser:password@localhost:5432/myapp_db

# Production (server .env only — see docs/DEPLOYMENT.md)
# DJANGO_SETTINGS_MODULE=conf.settings.prod
# DATABASE_URL=postgres://user:pass@localhost:5432/myapp_db
# ALLOWED_HOSTS=example.com,www.example.com
# CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
# SECURE_SSL_REDIRECT=False
# SECURE_COOKIES=False
EOF

write_file .gitignore <<'EOF'
# Environment / secrets
.env
.env.*
!.env.example

# Virtual environments
.venv/
venv/
env/

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
dist/
build/
*.egg

# Django
*.sqlite3
db.sqlite3
media/
staticfiles/
local_settings.py
logs/

# Testing / coverage
.coverage
htmlcov/
.pytest_cache/
.tox/
.mypy_cache/
.ruff_cache/

# IDE / OS
.idea/
.vscode/
*.swp
*.swo
.DS_Store
Thumbs.db
EOF

write_file pytest.ini <<'EOF'
[pytest]
DJANGO_SETTINGS_MODULE = conf.settings.test
python_files = tests.py test_*.py *_tests.py
EOF

write_file .cursorignore <<'EOF'
.venv/
venv/
__pycache__/
*.sqlite3
.env
.env.*
media/
staticfiles/
htmlcov/
.coverage
logs/
EOF

write_empty README.md

write_file new_project_workflow_readme.md <<'EOF'
# New project workflow

1. Copy `bootstrap.sh` into an empty folder.
2. Make it executable (see below) and run:
   ```bash
   ./bootstrap.sh
   ```
   You will be prompted:
   - **1) POC / minimal** — default Django user (username); no `accounts` app
   - **2) Email login** — `accounts` app with email `User` (OAuth-ready fields)

   Non-interactive: `BOOTSTRAP_AUTH=poc ./bootstrap.sh` or `BOOTSTRAP_AUTH=email ./bootstrap.sh`
   Or without the execute bit:
   ```bash
   bash bootstrap.sh
   ```
3. `cp .env.example .env`
4. `.venv/bin/python manage.py migrate`
5. `manage.py startapp` when you're ready for your first app (POC mode only; email mode already includes `accounts`).

## Do I need `chmod +x` first?

**Sometimes.** Copying the file may or may not keep the executable bit, depending on how you copy it (`cp`, drag-and-drop, zip, etc.).

- If `./bootstrap.sh` says "Permission denied", run once:
  ```bash
  chmod +x bootstrap.sh
  ```
- Or skip that and use `bash bootstrap.sh` — no execute bit required.

After a successful run, `bootstrap.sh` sets `chmod +x` on itself in that folder, so later runs can use `./bootstrap.sh`.

## Reset and re-bootstrap

To recreate the scaffold from scratch in this folder, delete everything **except** `bootstrap.sh`, then run `./bootstrap.sh` again (or `bash bootstrap.sh`). That restores all files the script generates: Django `conf/`, `.cursor/`, docs, `.venv` (recreated), and `git init` if `.git` was removed.

You will **not** get back: `.env`, `db.sqlite3`, manual edits, or anything not defined inside `bootstrap.sh` (e.g. `.cursor/plans/` from a prior session).
EOF

HANDOFF_UPDATED="$(TZ=Europe/Lisbon date '+%Y-%m-%d %H:%M %Z')"

write_file docs/handoff.md <<EOF
# Session handoff

> **Last updated:** ${HANDOFF_UPDATED} (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Brief description of what this project does.

Durable backlog: [\`docs/project-plan.md\`](project-plan.md) — **living file** (pending work across sessions; status updated on session-handoff).

## Done

- Bootstrap scaffold: Django \`conf/\` package, \`.cursor/\` rules, \`AGENTS.md\`
- Auth mode: ${AUTH_MODE}

## Not done

- First Django app
- \`migrate\` / \`createsuperuser\`
- Production deployment

## Next

1. \`cp .env.example .env\` and set \`SECRET_KEY\`
2. \`.venv/bin/python manage.py migrate\`
3. Add your first app with \`manage.py startapp\`

## Commands

\`\`\`bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
pytest
\`\`\`
EOF

write_empty docs/project-plan.md

write_empty docs/archive/.gitkeep
write_empty docs/reviews/.gitkeep
write_empty scripts/.gitkeep

write_file scripts/deploy.sh <<'EOF'
#!/usr/bin/env bash
# Run on the VPS after git pull. Adjust SERVICE_NAME below.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-CHANGE_ME-gunicorn}"

cd "$ROOT"
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
echo "Deploy complete. Restart: sudo systemctl restart ${SERVICE_NAME}"
EOF

write_file docs/DEPLOYMENT.md <<EOF
# Deploying ${PROJECT_NAME}

Develop locally, push to origin, pull on the VPS, run [\`scripts/deploy.sh\`](../scripts/deploy.sh).

## Settings modules

| Environment | Module | How chosen |
|-------------|--------|------------|
| Local dev | \`conf.settings.dev\` | default in \`manage.py\` |
| Tests | \`conf.settings.test\` | \`manage.py test\` auto-selects |
| Production | \`conf.settings.prod\` | \`DJANGO_SETTINGS_MODULE\` in systemd |

Secrets live in \`.env\` (gitignored). Copy [\`.env.example\`](../.env.example) as the template.

## Local setup

\`\`\`bash
cp .env.example .env
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
\`\`\`

## One-time VPS setup

1. Install PostgreSQL, nginx, Python venv support.
2. Clone repo to e.g. \`/srv/${PROJECT_NAME}/\`.
3. Create \`.env\` with at minimum:
   - \`DJANGO_SETTINGS_MODULE=conf.settings.prod\`
   - \`DATABASE_URL=postgres://...\`
   - \`DJANGO_SECRET_KEY=...\`
   - \`ALLOWED_HOSTS=your.domain\`
4. \`.venv/bin/pip install -r requirements.txt\`
5. \`.venv/bin/python manage.py migrate --noinput\`
6. \`.venv/bin/python manage.py collectstatic --noinput\`
7. Install systemd unit from [\`deploy/gunicorn.service\`](../deploy/gunicorn.service) (edit paths).
8. Install nginx site from [\`deploy/nginx.conf\`](../deploy/nginx.conf) (edit domain + paths).

## Every deploy

\`\`\`bash
cd /srv/${PROJECT_NAME}
git pull
SERVICE_NAME=${PROJECT_NAME}-gunicorn ./scripts/deploy.sh
sudo systemctl restart ${PROJECT_NAME}-gunicorn
\`\`\`

Or run the steps in \`scripts/deploy.sh\` manually.

## Docs layout

- [\`docs/handoff.md\`](handoff.md) — session snapshot (living)
- [\`docs/project-plan.md\`](project-plan.md) — durable backlog (living)
- [\`docs/reviews/\`](reviews/) — in-progress review docs
- [\`docs/archive/\`](archive/) — concluded reviews and old material
EOF

write_file deploy/gunicorn.service <<EOF
[Unit]
Description=${PROJECT_NAME} Django app — gunicorn
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=CHANGE_ME
Group=CHANGE_ME
WorkingDirectory=/srv/${PROJECT_NAME}
EnvironmentFile=/srv/${PROJECT_NAME}/.env
Environment=DJANGO_SETTINGS_MODULE=conf.settings.prod
ExecStart=/srv/${PROJECT_NAME}/.venv/bin/gunicorn conf.wsgi:application \\
    --bind 127.0.0.1:8000 \\
    --workers 3 \\
    --timeout 120 \\
    --max-requests 2000 \\
    --max-requests-jitter 200
Restart=always
RestartSec=5
KillSignal=SIGQUIT

[Install]
WantedBy=multi-user.target
EOF

write_file deploy/nginx.conf <<EOF
# ${PROJECT_NAME} — nginx site template
# Copy to /etc/nginx/sites-available/${PROJECT_NAME} and symlink sites-enabled.
# Replace example.com and /srv/${PROJECT_NAME} paths.

server {
    listen 80;
    server_name example.com;

    client_max_body_size 10M;

    location /static/ {
        alias /srv/${PROJECT_NAME}/staticfiles/;
    }

    location /media/ {
        alias /srv/${PROJECT_NAME}/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# --- Cursor ---

write_file .cursor/README.md <<'EOF'
# Cursor project configuration

Project-level Cursor settings live here. User-global config remains in `~/.cursor/`.

| Path | Purpose |
|------|---------|
| [`rules/`](rules/) | Persistent AI rules (`.mdc` files with YAML frontmatter) |
| [`skills/`](skills/) | Project Agent Skills (`skill-name/SKILL.md`) |
| [`agents/`](agents/) | Custom subagent definitions (`.md` files) |
| [`commands/`](commands/) | Slash commands (`.md` files) |
| [`hooks/`](hooks/) | Hook scripts referenced by `hooks.json` |
| [`hooks.json`](hooks.json) | Hook event configuration |
| [`cli.json`](cli.json) | Optional CLI overrides for this project |

## Quick start

- **Rule**: add `rules/my-rule.mdc` — see [Cursor rules docs](https://cursor.com/docs/context/rules)
- **Skill**: add `skills/my-skill/SKILL.md`
- **Agent**: add `agents/my-agent.md`
- **Command**: add `commands/my-command.md`
- **Hook**: add a script under `hooks/` and register it in `hooks.json`

Starter rules: [`rules/core.mdc`](rules/core.mdc) and [`rules/django-python.mdc`](rules/django-python.mdc).

[`AGENTS.md`](../AGENTS.md) at the project root provides agent instructions.

Commit this folder to share conventions with the team.
EOF

write_file .cursor/cli.json <<'EOF'
{}
EOF

write_file .cursor/hooks.json <<'EOF'
{
  "version": 1,
  "hooks": {}
}
EOF

write_file .cursor/rules/core.mdc <<'EOF'
---
description: Core working agreements for all work in this project
alwaysApply: true
---

# Core conventions

- **Minimize scope** — smallest correct change; avoid unrelated edits.
- **Match the codebase** — follow existing naming, structure, and patterns.
- **No secrets in repo** — never commit credentials, `.env`, or API keys.
- **Plain frontend** — Django templates + plain JavaScript; no React or Vue unless explicitly requested.
- **Read first** — check [`docs/handoff.md`](docs/handoff.md) and [`docs/project-plan.md`](docs/project-plan.md) before large changes.
- **Project plan** — when you spot new plans or follow-ups not yet captured, ask: "Should I add this to `docs/project-plan.md`?" If the user says "put this in the plan" (or similar), append it there immediately.
- **Incremental work** — no large application dumps; one concept at a time.
- **No emoji in logs** — keep terminal output plain.
- **Plans** — do not edit `.cursor/plans/` unless the user asks.
- **End of session** — after substantive work, run `/session-handoff` or skill `session-handoff`.
EOF

write_file .cursor/rules/django-python.mdc <<'EOF'
---
description: Django and Python conventions
globs: **/*.py
alwaysApply: false
---

# Django / Python

## Layering

```text
views / management commands  →  services.py  →  models.py
```

- Put reusable business logic in `services.py`, not duplicated in views or CLI
- Project package: `conf/` with split settings under `conf/settings/`

## Habits

- Migrations: one logical change per migration
- Use `.venv/bin/python` for `manage.py` and tests (or activate the venv first)
- Tests only when requested or they cover meaningful behaviour

## Imports

- Cross-app: absolute from app package (`from myapp.models import Thing`)
- Same app: absolute or single-dot relative (`from .models import Thing`)
- Never use multi-level relative imports across apps (`from ..otherapp import ...`)
EOF

write_file .cursor/skills/session-handoff/SKILL.md <<'EOF'
---
name: session-handoff
description: >-
  End-of-session documentation sync. Updates docs/handoff.md, docs/project-plan.md
  status, AGENTS.md session block, and README.md last-updated. Use when the user
  says session handoff, wrap up, end session, update living docs, or before
  stopping work.
disable-model-invocation: true
---

# Session handoff

Sync **living documents** at end of session so the next chat can start from `docs/handoff.md` and `docs/project-plan.md` without re-briefing.

| Living file | Rhythm |
|-------------|--------|
| `docs/handoff.md` | Session snapshot — refresh fully each handoff |
| `docs/project-plan.md` | Long-running backlog — append on request; tick status each handoff |

## When to run

- User says: "session handoff", "wrap up", "update living docs", "we're done for today"
- Before ending a coding session with meaningful changes

## Do not

- Commit or push unless explicitly requested
- Invent work that was not done — derive "landed" from conversation + `git diff`
- Edit `.cursor/plans/` unless the user asked
- Add items to `docs/project-plan.md` unless the user asked or confirmed during the session

## Workflow

### 1. Gather session facts

- Scan conversation for completed work, decisions, and explicit "next" task
- Run `git status` and `git diff` (or review unstaged changes)
- Run tests if the project has them: `pytest` or `.venv/bin/python manage.py test`

### 2. Update living documents

**Timestamp format** (required at top of `docs/handoff.md`):

\`\`\`markdown
> **Last updated:** YYYY-MM-DD HH:MM TZ (Europe/Lisbon)
> Replace with the current date and time whenever you edit this file.
\`\`\`

Example: \`> **Last updated:** 2026-09-05 08:52 WEST (Europe/Lisbon)\`

| File | Update |
|------|--------|
| `docs/handoff.md` | **Primary.** Refresh the **Last updated** block (real date + time). **Done**, **Not done**, **Next** sections. Commands block if changed. |
| `docs/project-plan.md` | Mark completed items (`[x]`), keep pending visible (`[ ]`). Append new items only when the user asked or confirmed during the session. |
| `AGENTS.md` | Session block: **Done**, **Not done**, **Next** (concise bullets). |
| `README.md` | "Last updated" line and quick-start pick-up point if the project uses README for onboarding. |

### 3. Reply to user

Short summary:

1. **Landed** — 3–6 bullets
2. **Next session** — one line
3. **Docs touched** — file list
4. **Tests** — count or "not run"
EOF

write_file .cursor/commands/session-handoff.md <<'EOF'
Run the `session-handoff` skill (`.cursor/skills/session-handoff/SKILL.md`) to sync `docs/handoff.md`, `docs/project-plan.md`, `AGENTS.md`, and `README.md` at end of session.
EOF

mkdir -p .cursor/agents .cursor/hooks
if [[ ! -f .cursor/agents/.gitkeep ]]; then
  : >.cursor/agents/.gitkeep
  echo "write: .cursor/agents/.gitkeep"
elif [[ "$FORCE" -eq 1 ]]; then
  : >.cursor/agents/.gitkeep
  echo "write: .cursor/agents/.gitkeep"
else
  echo "skip: .cursor/agents/.gitkeep"
fi

if [[ ! -f .cursor/hooks/.gitkeep ]]; then
  : >.cursor/hooks/.gitkeep
  echo "write: .cursor/hooks/.gitkeep"
elif [[ "$FORCE" -eq 1 ]]; then
  : >.cursor/hooks/.gitkeep
  echo "write: .cursor/hooks/.gitkeep"
else
  echo "skip: .cursor/hooks/.gitkeep"
fi

# Remove obsolete .gitkeep in rules/skills/commands if real files exist
for dir in rules skills commands; do
  if [[ -d ".cursor/$dir" ]] && find ".cursor/$dir" -mindepth 1 -not -name '.gitkeep' | grep -q .; then
    rm -f ".cursor/$dir/.gitkeep" 2>/dev/null || true
  fi
done

# --- AGENTS.md (project name substituted) ---

AGENTS_PATH="AGENTS.md"
if [[ -f "$AGENTS_PATH" && "$FORCE" -eq 0 ]]; then
  echo "skip: $AGENTS_PATH"
else
  cat >"$AGENTS_PATH" <<EOF
# ${PROJECT_NAME} — Agent instructions

Django project with settings in \`conf/\`. No apps scaffolded yet.

**Read [\`docs/handoff.md\`](docs/handoff.md) first** — session snapshot (done / not done / next).  
**Read [\`docs/project-plan.md\`](docs/project-plan.md)** — durable backlog of pending work across chats.

## Architecture

\`\`\`text
views / management commands  →  services.py  →  models.py
\`\`\`

- Business logic in \`services.py\`, not views or templates
- Plain Django templates + plain JavaScript — no React/Vue unless requested
- Minimize scope — focused diffs; match existing patterns

## Do

- Read \`docs/handoff.md\`, \`docs/project-plan.md\`, and \`README.md\` before large changes
- When you notice new plans, features, or follow-ups not yet in the plan, **ask**: "Should I add this to \`docs/project-plan.md\`?"
- When the user says **"put this in the plan"** (or similar), append to \`docs/project-plan.md\` immediately — do not rely on chat memory
- Use \`.venv/bin/python\` for \`manage.py\` and tests (or activate the venv first)
- Put secrets in root \`.env\` only; use \`.env.example\` as the committed template
- End substantive sessions with \`/session-handoff\` or skill \`session-handoff\`

## Do not

- Commit \`.env\`, API keys, \`db.sqlite3\`, or \`media/\`
- Over-engineer: no extra abstractions, queues, or auth unless requested
- Edit \`.cursor/plans/\` unless the user asks
- Use emoji in logs or prints

## Commands

\`\`\`bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
pytest
\`\`\`

## Documentation conventions

**Living documents** (updated throughout the project, not one-off archives):

| File | Role | How it changes |
|------|------|----------------|
| [\`docs/handoff.md\`](docs/handoff.md) | Session snapshot | Rewritten each session-handoff — done / not done / next |
| [\`docs/project-plan.md\`](docs/project-plan.md) | Durable backlog | Appended when you ask; checkboxes updated on session-handoff |

**Project plan format** when appending:

\`\`\`markdown
- [ ] Short description (added YYYY-MM-DD)
\`\`\`

Mark complete during session-handoff: \`- [x] ... (completed YYYY-MM-DD)\`

- **Reviews:** in-progress audits under [\`docs/reviews/\`](docs/reviews/); move concluded docs to [\`docs/archive/\`](docs/archive/)
- **Deploy:** see [\`docs/DEPLOYMENT.md\`](docs/DEPLOYMENT.md) and [\`scripts/deploy.sh\`](scripts/deploy.sh)
- Review/audit filenames: \`topic-YYYY-MM-DD-HHMM.md\` when adding docs under \`docs/\`

## Cursor project config

| Path | Use |
|------|-----|
| [\`.cursor/rules/\`](.cursor/rules/) | Project rules (\`.mdc\`) |
| [\`.cursor/skills/\`](.cursor/skills/) | Project skills |
| [\`.cursor/agents/\`](.cursor/agents/) | Custom subagents |
| [\`.cursor/commands/\`](.cursor/commands/) | Slash commands |
| [\`.cursor/hooks/\`](.cursor/hooks/) | Hook scripts + \`hooks.json\` |
EOF
  echo "write: $AGENTS_PATH"
fi

# --- git init ---

if [[ ! -d .git ]]; then
  git init
  echo "git init: done"
else
  echo "skip: git init (already a repo)"
fi

# --- venv + pip ---

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  echo "venv: created .venv"
else
  echo "skip: .venv (already exists)"
fi

.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [[ "$AUTH_MODE" == "email" ]]; then
  if [[ ! -f accounts/migrations/0001_initial.py ]] || [[ "$FORCE" -eq 1 ]]; then
    .venv/bin/python manage.py makemigrations accounts --noinput
  else
    echo "skip: accounts migrations (already exist)"
  fi
fi

write_file .bootstrap-auth <<EOF
${AUTH_MODE}
EOF

chmod +x manage.py 2>/dev/null || true
chmod +x bootstrap.sh 2>/dev/null || true
chmod +x scripts/deploy.sh 2>/dev/null || true

echo ""
echo "Bootstrap complete for: $PROJECT_NAME (auth: $AUTH_MODE)"
if [[ "$AUTH_MODE" == "email" ]]; then
  echo "Next: cp .env.example .env && .venv/bin/python manage.py migrate"
  echo "      .venv/bin/python manage.py createsuperuser   # enter email as login"
else
  echo "Next: cp .env.example .env && .venv/bin/python manage.py migrate"
fi
