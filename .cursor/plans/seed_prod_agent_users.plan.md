---
name: seed-prod agent users
overview: Add seed_prod that creates agent@ (staff) and agent-admin@ (full admin, like proforma-admin@). Passwords from .env with CLI override. seed_demo also creates those emails locally. One Pi playbook in the same pass.
todos:
  - id: seed-helper
    content: Add AGENT emails + seed_agent_users() / seed_prod() in proformas/seed.py; seed_demo calls the helper
    status: pending
  - id: seed-prod-cmd
    content: seed_prod reads AGENT_PASSWORD / AGENT_ADMIN_PASSWORD from env, flags override; seed_demo refuses DEBUG=False
    status: pending
  - id: tests
    content: "Integration tests: idempotent seed_prod, staff vs admin delete, seed_demo creates agent emails"
    status: pending
  - id: docs-playbook
    content: DEPLOYMENT + .env.example keys + docs/pi-playbook.md; tick P3 checkbox
    status: pending
isProject: false
---

# seed_prod + agent badges

## Locked decisions (2026-09-09)

- **Passwords:** `AGENT_PASSWORD` and `AGENT_ADMIN_PASSWORD` from the server `.env`; `--password` / `--admin-password` override. Missing both env and flag → `CommandError`. Never commit values. Document the keys in `.env.example` (empty/commented) and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
- **Local:** `seed_demo` also creates `agent@fribila.dev` and `agent-admin@fribila.dev` with the demo password so Pi can practice against fake clients using the same `--user` emails as prod.
- **Playbook:** this pass includes [`docs/pi-playbook.md`](docs/pi-playbook.md) — the one file you give Pi. Not a second `AGENTS.md`.
- **`agent-admin@`:** `role=admin` like `proforma-admin@` — can soft-delete **and** open Django admin (including `is_superuser`, same `_ensure_user` path as the demo admin).

## Answer: two seeds, not one

Keep **both**. They do different jobs.

| Command | Where | What it creates |
|---------|--------|-----------------|
| `seed_demo` | Local / clickable demo **only** | Catalog extras, fake clients/sites/quotes, `proforma-manager@` + `proforma-admin@`, **plus the two agent emails** |
| `seed_prod` | Production (and staging), **once** | The two Pi badges only. No fake clients, no demo quotes, no demo catalog dump |

`migrate` already seeds lookup tables and the Fribila company row. Real catalog and real clients stay staff-entered in prod.

Do **not** run `seed_demo` on the VPS. Do **not** add `seed_prod` to [`scripts/deploy.sh`](scripts/deploy.sh) — it needs secrets and is a one-time operator step, not every git pull.

```mermaid
flowchart LR
  subgraph local [Local]
    demo[seed_demo]
    demo --> fake[Fake clients and quotes]
    demo --> badges[agent@ and agent-admin@]
  end
  subgraph prod [Production]
    env[".env AGENT_PASSWORD / AGENT_ADMIN_PASSWORD"]
    prodSeed[seed_prod]
    env --> prodSeed
    prodSeed --> badgesOnly[Same emails, prod passwords]
    migrate[migrate] --> company[Company / VAT / parameters]
  end
  pi[One Pi Agent] -->|"--user agent@"| badges
  pi -->|"delete after you confirm: --user agent-admin@"| badges
```

Still **one Pi**, **one playbook**, **two Django users**. The second user is a delete/admin badge, not a second bot.

## What `seed_prod` will do

New [`proformas/management/commands/seed_prod.py`](proformas/management/commands/seed_prod.py) wrapping `seed_prod()` in [`proformas/seed.py`](proformas/seed.py).

- Idempotent via existing `_ensure_user`.
- Creates:
  - `agent@fribila.dev` — `role=staff` (cannot delete)
  - `agent-admin@fribila.dev` — `role=admin`, superuser (same as `proforma-admin@`)
- Password resolution per user: CLI flag if passed, else `decouple.config` env var. Both required after that.
- `--reset-password` same meaning as `seed_demo`.
- `seed_demo` refuses when `DEBUG` is False.
- `seed_prod` refuses passwords equal to `DEMO_PASSWORD` when `DEBUG` is False.

Print the two emails after success. Do not print secrets.

## What `seed_demo` will also do

Call `seed_agent_users(..., password=DEMO_PASSWORD)` so local Pi uses the same emails. Still creates manager/admin for the staff UI.

## Files

- [`proformas/seed.py`](proformas/seed.py) — `AGENT_EMAIL`, `AGENT_ADMIN_EMAIL`; `seed_agent_users()`; `seed_prod()`; `seed_demo()` calls the helper
- **New** [`proformas/management/commands/seed_prod.py`](proformas/management/commands/seed_prod.py)
- [`proformas/management/commands/seed_demo.py`](proformas/management/commands/seed_demo.py) — list agent emails; refuse when `DEBUG` is False
- **New** [`proformas/tests/test_seed_prod.py`](proformas/tests/test_seed_prod.py) — idempotent; staff cannot delete; admin can; `seed_demo` creates agent emails; env/flag password resolution
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — one-time `seed_prod`; `.env` keys; never `seed_demo`
- `.env.example` — `AGENT_PASSWORD=` and `AGENT_ADMIN_PASSWORD=` empty (if that file is in the tree)
- [`README.md`](README.md), [`docs/handoff.md`](docs/handoff.md), [`docs/project-plan.md`](docs/project-plan.md), [`docs/agent-ops.md`](docs/agent-ops.md) §6
- **New** [`docs/pi-playbook.md`](docs/pi-playbook.md) — default `--user agent@fribila.dev`; deletes only after confirm with `--user agent-admin@fribila.dev`; command list + voice gates

## Out of scope

- Wiring `seed_prod` into `deploy.sh`
- Catalog/client data in `seed_prod`
- Two playbooks or two Pi agents
- Storing production passwords in git

## Done when

- `seed_prod` creates the two users from env and/or flags; safe to run twice
- `seed_demo` still green and has those emails locally
- `docs/pi-playbook.md` exists and is the file you give Pi
- `pytest` green; deploy script unchanged
