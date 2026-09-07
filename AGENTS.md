# fri-uni — Agent instructions

Django project with settings in `conf/`. Email auth via `accounts` app. Domain models live in **`proformas`** — follow [`docs/data-points.md`](docs/data-points.md).

**Read [`docs/handoff.md`](docs/handoff.md) first** — session snapshot (done / not done / next).  
**Read [`docs/preliminary_project-plan.md`](docs/preliminary_project-plan.md)** — product scope and decisions.  
**Read [`docs/data-points.md`](docs/data-points.md)** — conceptual model before adding tables.  
**Read [`docs/project-plan.md`](docs/project-plan.md)** — durable backlog of pending work across chats.  
**Read [`docs/front-end-project-plan.md`](docs/front-end-project-plan.md)** — staff UI chrome (dashboard, drawers, i18n) before HTML/CSS/JS.

## Architecture

```text
views / management commands  →  proformas/services.py  →  models.py
```

- Business logic in `services.py`, not views or templates
- Plain Django templates + plain JavaScript — no React/Vue unless requested
- Minimize scope — focused diffs; match existing patterns
- Issued proformas are frozen snapshots; do not edit locked money fields
- `docs/project-plan.md` is the checkbox backlog — do not write product scope there; use `docs/preliminary_project-plan.md`

## Do

- Read `docs/handoff.md`, `docs/preliminary_project-plan.md`, `docs/data-points.md`, `docs/project-plan.md`, `docs/front-end-project-plan.md`, and `README.md` before large changes
- When you notice new plans, features, or follow-ups not yet in the backlog, **ask**: "Should I add this to `docs/project-plan.md`?"
- When the user says **"put this in the plan"** (or similar), append to `docs/project-plan.md` immediately — do not rely on chat memory
- Use `.venv/bin/python` for `manage.py` and tests (or activate the venv first)
- Portuguese **NIF and phone** fields: follow [`.cursor/rules/portuguese-nif-and-phone.mdc`](.cursor/rules/portuguese-nif-and-phone.mdc); reuse `validate_tax_number`, `validate_phone_number`, and `configure_nine_digit_form_field` in `proformas/services.py`
- Put secrets in root `.env` only; use `.env.example` as the committed template
- End substantive sessions with `/session-handoff` or skill `session-handoff`

## Do not

- Commit `.env`, API keys, `db.sqlite3`, or `media/`
- Over-engineer: no extra abstractions, queues, or auth unless requested
- Edit `.cursor/plans/` unless the user asks
- Use emoji in logs or prints
- Invent schema that contradicts `docs/data-points.md` without updating that doc first

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
pytest
```

## Documentation conventions

**Living documents** (updated throughout the project, not one-off archives):

| File | Role | How it changes |
|------|------|----------------|
| [`docs/handoff.md`](docs/handoff.md) | Session snapshot | Rewritten each session-handoff — done / not done / next |
| [`docs/preliminary_project-plan.md`](docs/preliminary_project-plan.md) | Product scope | Append `## Update YYYY-MM-DD`; do not rewrite earlier sections |
| [`docs/data-points.md`](docs/data-points.md) | Conceptual data model | Rewritten in place when the model changes; no SQL/ORM in this file |
| [`docs/project-plan.md`](docs/project-plan.md) | Durable backlog | Appended when you ask; checkboxes updated on session-handoff |
| [`docs/front-end-project-plan.md`](docs/front-end-project-plan.md) | Staff UI chrome | Rewritten in place when layout/chrome rules change |

**Project plan format** when appending to `docs/project-plan.md`:

```markdown
- [ ] Short description (added YYYY-MM-DD)
```

Mark complete during session-handoff: `- [x] ... (completed YYYY-MM-DD)`

- **Reviews:** in-progress audits under [`docs/reviews/`](docs/reviews/); move concluded docs to [`docs/archive/`](docs/archive/)
- **Deploy:** see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and [`scripts/deploy.sh`](scripts/deploy.sh)
- Review/audit filenames: `topic-YYYY-MM-DD-HHMM.md` when adding docs under `docs/`

## Cursor project config

| Path | Use |
|------|-----|
| [`.cursor/rules/`](.cursor/rules/) | Project rules (`.mdc`); includes `portuguese-nif-and-phone` for NIF and phone validation |
| [`.cursor/skills/`](.cursor/skills/) | Project skills (`session-handoff`, `eliciting-project-model`) |
| [`.cursor/agents/`](.cursor/agents/) | Custom subagents |
| [`.cursor/commands/`](.cursor/commands/) | Slash commands |
| [`.cursor/hooks/`](.cursor/hooks/) | Hook scripts + `hooks.json` |

## Session

**Done:** Crash/freeze review [`docs/reviews/error-dead-ends-2026-09-07-1238.md`](docs/reviews/error-dead-ends-2026-09-07-1238.md) + H/M/L remediations (PDF/create-draft errors, confirm JS, atomic issue, catalog delete guards, row locks, `0016` cancelled→issued). Rejected overlay + new-draft form + list sort in same tree. **133 tests** green.

**Not done:** Production deploy; letterhead; real prices; volume auto-pick; indoor/outdoor auto-pair; VAT on quote math/PDF; contact fields on issued-quote snapshots/PDF; git commit.

**Next:** `migrate` + manual confirm-dialog check; commit when ready; VAT-on-quote backlog. Read [`docs/handoff.md`](docs/handoff.md).

