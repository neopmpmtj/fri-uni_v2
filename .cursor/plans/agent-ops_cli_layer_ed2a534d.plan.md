---
name: Agent-ops CLI layer
overview: Make fri-uni operable by a voice/bash agent through management commands that wrap existing services. Implement in the blueprint’s P0–P3 phases, but cut P0 to the lookup commands the voice loop actually needs, skip premature indexes and catalog CRUD, and keep the staff web UI untouched.
todos:
  - id: p0-kit
    content: "Add proformas/agent_cli.py: JSON envelope, pagination, money strings, CommandError mapping"
    status: completed
  - id: p0-commands
    content: Add list/show management commands (client, site, item, power, proforma, company; cheap extras if tiny)
    status: completed
  - id: p0-tests
    content: Add 2–6 integration tests in test_agent_cli_p0.py; pytest -q green
    status: completed
  - id: p0-docs
    content: Append Agent ops P0–P3 checkboxes to docs/project-plan.md; short pointers in AGENTS.md and handoff.md
    status: completed
  - id: p2-later
    content: "Later: --volume-m3, line/issue/pdf commands, migrate create_proforma to envelope"
    status: completed
  - id: p1-later
    content: "Later: client_save / site_save / admin-only deletes (not catalog CRUD)"
    status: completed
  - id: p3-later
    content: "Later: seed agent + agent-admin users; README voice usage; sync agent-ops.md to what shipped"
    status: completed
isProject: false
---

# Agent-ops CLI (bot-worthy, not overboard)

## What is already true

The product is already structured for an agent. The web UI is not the bottleneck.

```text
Human (voice) → agent (Neo) → manage.py commands → proformas/services.py → DB
```

- [proformas/services.py](proformas/services.py) already owns money, numbering, issue/freeze, NIF/phone, `power_for_volume`, `add_default_split`, accept/reject/change.
- [create_proforma.py](proformas/management/commands/create_proforma.py) already does split and multi via `--line` (indoor-first auto-pairs; outdoor-first attaches following indoors). Output is a bare number, not JSON.
- Staff UI stays. Commands must not bypass services or invent REST.

The agent fails today because it cannot **list/search/show** to resolve names → ids, then confirm, then write. That is P0.

## Pushback (do not build these now)

These items in [docs/agent-ops.md](docs/agent-ops.md) are ceremony or the wrong surface for a quoting bot:

- **Index migration + latency SLAs** — catalog and client counts are tiny; Django already indexes FKs. No `< 200 ms` tests (flaky). Revisit on Postgres if lists feel slow.
- **Catalog write CLI** (`family_save`, `vat_save`, `item_save`, `match_save`, `parameter_set`, …) — catalog is a setup page. Voice quoting does not maintain pricelists. Skip until someone actually asks the agent to add SKUs.
- **`--include-deleted`** — live manager is enough.
- **Exit codes 0/1/2** — Django `CommandError` already exits 1. The agent should parse JSON `ok`. Do not invent a three-way protocol.
- **JSON + human table on the same stdout** — hostile to parsers. **JSON only on stdout**; errors on stderr. Optional `--format table` later if a human is watching the terminal.
- **Auto-issue** — keep `--issue` on `create_proforma` for scripts, but the voice protocol never uses it without a second confirmation. No new auto-issue path.
- **Logo upload via CLI** — stays web UI.
- **REST API** — out of scope (blueprint is right).
- **`save_site` service rewrite + wiring views** — sites already save through `_save_audited`. P1 CLI can call `save_audited` (or a thin `save_site` alias). Do not refactor the staff site page as part of this.

Locked from you: **agent accounts option B** — `agent@fribila.dev` (staff) for day-to-day; `agent-admin@fribila.dev` only after a human approves a delete. Seed in P3, not P0.

## Phasing (update the plan as we go)

Each phase: commands + 2–6 pytest tests + tick checkboxes in [docs/project-plan.md](docs/project-plan.md). Stop when that phase’s “Done when” is true.

```mermaid
flowchart LR
  P0[P0 lookup JSON]
  P2[P2 quote lifecycle]
  P1[P1 client and site save]
  P3[P3 agent users and docs]
  P0 --> P2
  P2 --> P1
  P1 --> P3
```

**P0 this pass — lookup.** Shared envelope + list/show for the voice resolve loop.

**P2 next — quoting.** `--volume-m3` on existing `create_proforma`; line add/update/remove; issue/change/accept/reject; PDF. This is when the agent can finish a quote without the browser.

**P1 after that — missing master data.** `client_save` / `site_save` / `client_delete` / `site_delete` so “0 search hits → offer create” works. Catalog writes stay out.

**P3 last — identity and docs.** Seed the two agent users; README / AGENTS.md / voice dialogues. [docs/agent-ops.md](docs/agent-ops.md) already exists; sync it to what we actually shipped (cut the overboard bits).

`--volume-m3` on `create_proforma` (not a second command). Surface `expired` on `proforma_list`; never auto-extend.

## P0 design (implement after you confirm)

**Shared kit** — new [proformas/agent_cli.py](proformas/agent_cli.py) (not a new Django app):

- Envelope: `{"ok": true, "entity": "...", "count", "limit", "offset", "items": [...]}` for lists; `{"ok": true, "entity", "item": {...}}` for show.
- Money as decimal strings (`"1234.50"`); dates ISO-8601.
- `--limit` default 25, max 200; `--offset`.
- `--search` = icontains; `--nif` / `--code` / `--number` exact.
- Wrap `ValidationError` / missing PK as `CommandError` with `{"ok": false, "error": "..."}` on stderr (or stdout with `ok: false` — pick **stdout JSON always**, including errors, plus `CommandError` so exit is 1; that is what a bash agent actually consumes).
- `select_related` for labels; `.live` / default manager only.

**Thin commands** (one file each, named as the spec so `manage.py help` is the contract):

Must-have:

- `client_list` / `client_show`
- `site_list` / `site_show` (`--client`)
- `item_list` / `item_show` (`--kind`, `--search`, `--code`, `--default`)
- `power_list` (`--volume` → `power_for_volume` or band filter; on overlap/none return the service error, do not guess)
- `proforma_list` / `proforma_show` (grouped lines via `grouped_proforma_lines`; include `vat_amount`, `total_with_vat`, `valid_until`, `expired`)
- `company_show` → `get_company()` (logo: boolean present, not bytes)

Same helper, cheap extras (do these in P0 if they stay tiny; drop if they bloat the PR):

- `family_list`, `sub_family_list`, `brand_list`, `vat_list`, `tubing_list`, `match_list`

Leave `create_proforma` output as the number in P0 so [proformas/tests/test_phase8.py](proformas/tests/test_phase8.py) stays stable. Envelope that command in P2.

**Tests** (`@pytest.mark.integration` + `django_db`, `call_command`, 2–6 tests in e.g. `proformas/tests/test_agent_cli_p0.py`):

- `client_list --search` envelope + pagination fields
- unknown `client_show` id → `CommandError` / `ok: false`
- `item_list --kind indoor` + money strings
- `proforma_list` includes `expired` for an issued row past `valid_until`
- `power_list --volume` happy path (reuse existing volume-band fixtures from add-default tests)

Do not add a test per entity.

**Docs this phase:** append an **Agent ops** section to [docs/project-plan.md](docs/project-plan.md) with P0–P3 checkboxes; tick P0 when green. One-line pointer in [AGENTS.md](AGENTS.md) and [docs/handoff.md](docs/handoff.md). Do not rewrite the whole blueprint until P3.

## Later phases (not this PR)

**P2** — `--volume-m3` / `--tubing` on `create_proforma` calling `add_default_split` (make `--line` optional when volume is set); `proforma_add_line` / `update_line` / `remove_line`; `proforma_issue` / `change` / `accept` / `reject` / `unaccept` / `unreject`; `proforma_pdf --out` via `build_proforma_pdf`. Then migrate `create_proforma` to the JSON envelope and update phase 8 tests.

**P1** — `client_save` → `save_client` (NIF/phone via existing validators); `site_save` → `save_audited`; deletes require `--user` of an admin (agent-admin in P3). Price-change commands stay out.

**P3** — seed `agent@fribila.dev` (staff) and `agent-admin@fribila.dev` (admin) in [proformas/seed.py](proformas/seed.py) with the existing demo password locally; production accounts stay Django-admin provisioned (no agent password in git). README “Voice / agent usage” + the three dialogues from the blueprint.

## Out of scope for the whole agent-ops track

Staff HTML/CSS/JS, REST, heating expansion, production deploy, WeasyPrint timeout, company logo CLI, mixing with the current uncommitted quote-letterhead diff.