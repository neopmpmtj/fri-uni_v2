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
