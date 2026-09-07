# fri-uni

Internal HVAC back office for creating **proforma invoices** — client quotes for equipment installation and cost, including an upfront-payment discount. Not an official finance document.

> **Last updated:** 2026-09-07 12:50 WEST

## What it does

Staff sign in with email, pick language on the dashboard, then quote from a catalog (family → sub-family → item, plus manufacturer): client and site, equipment lines, optional extra tubing per line, extra labour and observations. **Issue** freezes a snapshot; staff can view the quote on screen and download a PDF. Clients do not log in.

A management command (`create_proforma`) can create a proforma in one shot (same database, mandatory `--user`).

## Quick start

```bash
source .venv/bin/activate
cp .env.example .env   # set SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
pytest
```

Demo logins (password `fribila-demo`):

- `proforma-admin@fribila.dev` — Django admin, can delete clients/sites
- `proforma-manager@fribila.dev` — quoting UI, cannot delete

`seed_catalog` is catalog-only. Do not run `seed_demo` in production.

## Documentation

| Doc | Role |
| --- | --- |
| [`docs/handoff.md`](docs/handoff.md) | Session snapshot — start here each chat |
| [`docs/project-plan.md`](docs/project-plan.md) | Phased implementation playbook (one phase at a time) |
| [`docs/front-end-project-plan.md`](docs/front-end-project-plan.md) | Staff UI chrome (dashboard, drawers, i18n) |
| [`docs/data-points.md`](docs/data-points.md) | Conceptual tables and fields (source for models) |
| [`docs/preliminary_project-plan.md`](docs/preliminary_project-plan.md) | Product scope, apps, decisions |
| [`docs/reviews/`](docs/reviews/) | In-progress audits |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | VPS deploy notes |
| [`AGENTS.md`](AGENTS.md) | Agent instructions |

## Stack

- Django (`conf/` settings split), plain templates + plain JavaScript
- Email login via `accounts.User`
- PostgreSQL in production; SQLite for local dev (see `.env.example`)

## Pick up from here

Staff web MVP and CLI are implemented (`proformas`). For a clickable demo run `seed_demo` and log in as the manager. See [`docs/handoff.md`](docs/handoff.md). Code review and remediations: [`docs/reviews/code-review-2026-09-07-0617.md`](docs/reviews/code-review-2026-09-07-0617.md).
