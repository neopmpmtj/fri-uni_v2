# fri-uni — Agent Operations Blueprint (voice-first)

**Project:** fri-uni (internal HVAC proforma back office) — repo `neopmpmtj/fri-uni_v2`
**Date:** 2026-09-08 (blueprint v1) · **rev 5: 2026-09-09** — P0–P3: CLI + seed_prod badges + pi-playbook
**Local copy:** `/home/pmpmt/app/fri-uni_v2` (main, **225 tests green**)
**Goal:** make the app 100% operable by an AI agent through **voice conversation** — the agent lists, filters, creates, edits and issues proformas exactly like a staff member, but faster, with no human needing to hold every detail in their head.

---

## 1. Operating model

```
Human (voice / chat)  →  agent (Neo)  →  management commands  →  services.py  →  models / DB
```

- The existing **staff web UI stays untouched** — commands call the *same* services the web views call.
- The human does **not** need to pre-know the data model. The agent asks, searches, proposes, **confirms with the human**, then executes.
- Iteration is expected: the agent may ask 2–5 clarifying questions before anything is written. The final "shall I create?" gate happens before any write or issue.

---

## 2. What already exists (foundation to build on)

| Asset | Where | Notes |
|---|---|---|
| Service layer (single source of truth) | `proformas/services.py` | All money math, numbering, validation, snapshots |
| Audit trail | `AuditedModel` + `ChangeLog` + `ActivityLog` | `created_by/updated_by`, `actor_type` |
| Soft delete | `deleted_at` + `LiveManager` | Live rows only unless deleted; parameters and company profile never delete |
| Role model | `accounts.User.role` (`staff`/`admin`) | `admin` → Django admin + delete rights |
| JSON lookup CLI | `client_list` / `client_show`, `site_*`, `item_*`, `power_list`, `proforma_*`, `company_show` | stdout JSON envelope (`proformas/agent_cli.py`) |
| Client/site write CLI | `client_save` / `site_save` / `client_delete` / `site_delete` | same services as the staff UI; delete is admin-only |
| Create CLI | `create_proforma` | JSON envelope. `--user --site` plus `--line item:qty[:tubing]` **or** `--volume-m3` (`--tubing` only with volume). Optional `--issue`, discounts, `--validity-days` |
| Quote lifecycle CLI | `proforma_add_line` / `update_line` / `remove_line`, `proforma_issue` / `change` / `accept` / `reject` / `unaccept` / `unreject`, `proforma_pdf --out` | same services as the staff UI; PDF is issued-only |
| Permission rules | `require_delete_permission` etc. | Only `admin` soft-deletes clients/sites/catalog; parameters never delete |
| Frozen issue snapshots | `issue_proforma` | Client/site/catalog display fields copied onto proforma + lines |
| Corrections | `change_proforma` (supersede), accept/reject overlays | No `cancelled` status |
| Tests | pytest, **225 passing** | 2–6 tests per phase convention; agent CLI + `test_seed_prod.py` |
| Company profile (issuer) | `proformas.models.Company` + `company_edit` staff page | Singleton (`uniq_live_company`); edited by staff/admin, **no create/delete**; quotes/PDF read it **live** (not snapshotted) |
| VAT on quotes | migrations `0023_vat_and_validity`, `0024_company_profile` | Line/quote IVA after discounts; `vat_amount`, `total_with_vat` frozen at issue |
| Quote validity | `validity_days` (default 7, from `default_validity_days` parameter) | Window starts at **issue**; `valid_until` frozen; expiry is display-only |
| Quote layout / letterhead | `quote_body.html`, `quote_styles.html`, `quote.html/quote_pdf.html` | Client-facing quote with IVA breakdown; live company letterhead |

### Key display conventions (for list output)
- Client: `name` (+ `tax_number`)
- Site: `alias_1` (of alias_1..4) under a client
- Item: `internal_code — <design> indoor <power>` / `internal_code — outdoor <N>-port <power>`
- Power: `"<power> <unit>"` e.g. `3.5 kW`; bands by `volume_from_m3..volume_to_m3`
- Sub-family (design line): `"<family> / <name>"`
- Proforma: `number` + `status` + client/site snapshot + `grand_total`

### Permission matrix (enforced in services — commands must not bypass)
| Action | staff | admin |
|---|---|---|
| Create/edit clients, sites, catalog, proformas | yes | yes |
| Issue / accept / reject / change proformas | yes | yes |
| Soft-delete clients, sites, catalog rows | no | yes |
| Delete parameters | never | never |
| Price changes (equipment, tubing) | yes, with **reason** | yes, with reason |

---

## 3. Design principles for the agent layer

1. **No REST API.** The agent runs on the same machine with bash → *management commands are the doors*. (REST/JSON HTTP only later if a remote/other-machine agent ever appears.)
2. **Software owns state.** Invoice/proforma **numbers** (`next_proforma_number`), totals, discount math — computed in services, never by the agent, never passed in.
3. **Never guess.** Every name → resolved to an **id** through list/search commands before any write. No hardcoded ids, no schema guessing: contract doc + `--help` on every command.
4. **Deterministic output.** All commands print a stable JSON envelope plus a human table; exit codes 0/1/2; errors on stderr.
5. **Every write carries an actor.** Commands require `--user` (a dedicated agent account, see §6).
6. **Commands wrap services only** — no raw ORM writes inside commands.
7. **Human confirms anything irreversible** (issue = frozen snapshot; delete = soft but admin-only; change = supersede).

---

## 4. Command set specification

### 4.1 Conventions

- Naming: `<entity>_<action>` (e.g. `client_list`, `item_show`, `proforma_issue`).
- JSON envelope for lists:
```json
{"ok": true, "entity": "client", "count": 3, "limit": 25, "offset": 0,
 "items": [{"id": 1, "label": "Acme, Lda", "tax_number": "123456789", "city": "Porto"}]}
```
- All money as decimal strings (`"1234.50"`); timestamps ISO-8601 UTC; live rows only unless `--include-deleted` (admin).
- Search flags: `--search` = case-insensitive substring; NIF/exact codes match exactly when the flag is `--nif`/`--code`.
- Pagination on every list: `--limit` (default 25, max 200) and `--offset`.

### 4.2 Lookup & fast lists (the "list and filtered list" core)

| Command | Filters / sort | Returns |
|---|---|---|
| `client_list` | `--search --nif --country-code --sort name|tax_number` | id, name, tax_number, city, email |
| `client_show <id>` | — | full client + sites count + last proforma |
| `site_list` | `--client <id> --search --sort alias_1` | id, alias_1, city, client id/name |
| `site_show <id>` | — | full site incl. address, contacts |
| `item_list` | `--kind indoor\|outdoor --family <id> --design-line <id> --brand <id> --power <id> --search --default` | id, internal_code, kind, power, list_price, is_default |
| `item_show <id>` | — | item + vat + price history + matches |
| `family_list` / `sub_family_list` / `brand_list` | `--search --default` | id + name (+ family for sub_family) |
| `power_list` | `--volume <m3>` (band match), `--has-default` | id, power, unit, band, default indoor code |
| `vat_list` / `tubing_list` / `contact_position_list` | `--search --default` | id, code/length, rate/price |
| `match_list` | `--outdoor <id>` or `--indoor <id>` or `--default` | outdoor↔indoor pairing rows (id) |
| `proforma_list` | `--status draft\|issued --client <id> --site <id> --number --from --to --sort` | number, status, client, site, grand_total, valid_until |
| `proforma_show <id>` | — | grouped lines (outdoor → indoor children), discounts, net totals, `vat_amount`, `total_with_vat`, snapshots, validity |
| `company_show` | — | live issuer profile: name, NIF, street/postal/city, phone, email, IBAN, logo present? (read from `get_company()`) |
| `company_save --user <email> [--name --tax-number --street --postal-code --city --phone --email --iban]` | `save_company` | staff/admin edit; no create/delete (singleton); logo via web UI for now |
| `proforma_pdf <id> --out <path>` | — | bytes → file |

**Speed notes for lists (DB level):**
- Add indexes (new migration) for the hot filter columns: `client(name)`, `client(tax_number)`, `site(client_id)`, `item(kind)`, `item(brand_id)`, `item(sub_family_id)`, `item(power_id)`, `itemmatch(outdoor_id)`, `itemmatch(indoor_id)`, `proforma(site_id)`, `proforma(status)`, `proforma(number)`, `proforma(created_at)`.
- Use `.live` manager, `select_related` for label fields, and paginate server-side.
- Target: local SQLite < 200 ms; prod Postgres < 50 ms on any filtered list.

### 4.3 Write commands (CRUD via services)

| Command | Service used | Notes |
|---|---|---|
| `client_save --user <email> [--id] --name --nif --street --postal-code --city --phone --email` | `save_client` | NIF/phone validated PT rules |
| `client_delete --user <admin> --id` | `delete_client` | blocked if sites have proformas |
| `site_save` / `site_delete` | `save_client`-adjacent / `delete_site` | under a client |
| `contact_position_save/delete` | — | |
| `family_save/delete`, `sub_family_save/delete`, `brand_save/delete` | service validators | delete = admin |
| `item_save --user ... --internal-code --kind --family --brand --power --ports --vat --list-price [--reason]` | `save_item`, `update_equipment_list_price` | price change **requires reason** |
| `vat_save/delete`, `power_save/delete` (bands + default indoor), `tubing_save/delete` (price change reason) | `save_power`, `save_tubing_length` … | |
| `parameter_set --user --key --value` | `save_parameter` | no delete |
| `match_save/delete` | `sync_item_matches` | pairing outdoor↔indoor |

### 4.4 Proforma lifecycle commands

| Command | Service | Gate |
|---|---|---|
| `create_proforma` (exists) + new mode flags below | `create_draft`, `add_line`, `issue_proforma` | `--validity-days` added (defaults to `default_validity_days` param) |
| `proforma_add_line --proforma <id> --item <id> [--qty] [--parent <line-id>] [--tubing <id>]` | `add_line` | draft only |
| `proforma_update_line` / `proforma_remove_line` | `update_line` / `remove_line` | draft only |
| `proforma_issue --user <email> --proforma <id>` | `issue_proforma` | **confirms freeze**; validates systems |
| `proforma_change --user --proforma <id>` | `change_proforma` | issued → new draft superseding (copies client/site/discounts) |
| `proforma_accept / reject / unaccept / unreject` | matching services | overlays, mutually exclusive |
| `proforma_pdf --proforma <id> --out <file>` | PDF builder | issued only |

---

## 5. The three proforma creation modes (voice scenarios)

Mode rules (from the app's own docs, `handoff.md`):
- **Split** = 1 outdoor (`ports=1`) + **exactly one** indoor; staff start from the indoor; default match auto-adds the outdoor.
- **Default** = room **volume m³** → `powers` band → that power row's **default indoor** + its matched 1-port outdoor (qty 1).
- **Multi** = 1 outdoor (`ports ≥ 2`) + **2..ports** indoor units; start from the outdoor, then add indoors. Extra tubing stays on indoor runs. `override_checks` may relax multi count rules (never for split's "exactly one").

Issue validation (`_validate_systems_for_issue`): every indoor must belong to an outdoor line; outdoor lines never have a parent; split outdoor = exactly 1 indoor; multi outdoor = between 2 and `ports` indoors (unless override).

### Mode 1 — SPLIT (indoor-first, auto-paired outdoor)

**Voice example**
```
Human:  "Create a proforma for the Porto office: a split with indoor unit
         BTU-09-FR, one unit."
Agent:  (resolves client "Porto office" → site id; item → indoor id)
        "I'll quote: site X, 1× BTU-09-FR indoor, auto-paired 1-port outdoor
         (default match). Extra tubing? [no] Shall I create the draft?"
Human:  "Yes."
Agent:  (create_proforma --user agent@... --site 12 --line 305:1)
        "Draft #2026/0041 ready — net €1.240,00 + IVA, valid 7 days once
         issued. Issue it?"
```

**CLI**
```bash
.venv/bin/python manage.py create_proforma \
  --user agent@fribila.dev --site 12 --line 305:1
# indoor line with no preceding outdoor → auto-pair split outdoor (ports=1)
# add --line 305:1:7 for extra tubing length id 7
# add --issue to create+freeze in one step (only after human says go)
```

### Mode 2 — DEFAULT (room volume → power band → default indoor + matched outdoor)

**New CLI flag proposed:** `--volume-m3` (reuses `power_for_volume` + `add_default_split`).

**Voice example**
```
Human:  "Quote a default system for a 30 m³ bedroom at the Porto office."
Agent:  (resolves site; 30 m³ → power band → default indoor + default outdoor)
        "30 m³ falls in band 3.5 kW. Default indoor: FRI-09-FR; matched
         outdoor: single-port 3.5 kW. Add extra tubing? [no] Shall I create?"
Human:  "Go."
Agent:  (create_proforma --site 12 --volume-m3 30)
        "Draft created — line added via default split."
```

**CLI (proposed)**
```bash
.venv/bin/python manage.py create_proforma \
  --user agent@fribila.dev --site 12 --volume-m3 30 \
  [--tubing 7] [--issue]
```

### Mode 3 — MULTI (outdoor-first, 2+ indoors)

**Voice example**
```
Human:  "New quote: three rooms on one multi outdoor, 5-port, at Porto."
Agent:  (resolves outdoor item; asks for the 3 indoor items one by one)
        "Outdoor 5-port FRI-36-M, indoors: BTU-09, BTU-12, BTU-09.
         3 ≤ 5 ports — valid. Extra tubing per indoor? None. Create?"
Human:  "Yes."
Agent:  (create_proforma --site 12 --line 501:1 --line 305:1 --line 306:1 --line 305:1)
        "Draft #2026/0042 — 1 outdoor + 3 indoor lines."
```

**CLI**
```bash
.venv/bin/python manage.py create_proforma \
  --user agent@fribila.dev --site 12 \
  --line 501:1 --line 305:1 --line 306:1 --line 305:1
# first line = outdoor (opens system); following indoors attach to it
```

### Mode summary table

| Mode | Trigger | Data the agent must get | Auto/default | Validation at issue |
|---|---|---|---|---|
| Split | "split for room X" | indoor item, site, qty | 1-port outdoor default match | exactly 1 indoor |
| Default | "default for 30 m³" | **volume m³**, site | band → default indoor + matched outdoor | same as split |
| Multi | "multi, 5-port, 3 rooms" | outdoor item, N indoor items, site | — | 2..ports indoors unless override |

---

## 6. Agent identity, environment & audit

- **One Pi Agent.** Two Django badges created by `seed_demo` (local) and `seed_prod` (production):
  - `agent@fribila.dev` — `role=staff`. Default `--user` for list/create/issue/PDF.
  - `agent-admin@fribila.dev` — `role=admin` (Django admin, can delete). Use only after the human confirms a delete.
- Production passwords: `AGENT_PASSWORD` and `AGENT_ADMIN_PASSWORD` in server `.env`; `seed_prod` flags override. Never committed. See [`docs/DEPLOYMENT.md`](DEPLOYMENT.md).
- **Playbook to give Pi:** [`docs/pi-playbook.md`](pi-playbook.md). [`AGENTS.md`](../AGENTS.md) is for Cursor coding, not Pi quoting.
- Environment: local `.venv/bin/python manage.py …`; production later via the deploy pipeline (same commands, Postgres). `.env` never committed. No emoji in logs (repo rule).
- Do not run `seed_demo` in production.

---

## 7. Voice conversation protocol (the human does not need to hold it all)

**Flow (state machine for the agent):**

1. **Intake** — ask one open question at a time: client/site first, then system mode, then the mode-specific detail (indoor item / volume m³ / outdoor + indoors).
2. **Resolve** — every name → `*_list --search`; if >1 result, show 3–5 compact rows (`id | label`) and ask "which one?"; if 0 results, say so and offer creation of the missing master data (client/site/item) as a separate step.
3. **Fill** — ask only what the mode needs (§5). Defaults (discounts from parameters, qty 1, no extra tubing) are assumed but **echoed** in the summary.
4. **Optional extras** — extra tubing per indoor run, extra labour, observations, discounts: one question each, only if the human mentioned them.
5. **Read-back** — compact summary: site, mode, lines (codes + qty), total (computed by the draft), "draft only, not issued".
6. **Gate** — "Shall I create?" → on "yes/go/ahead" run the command.
7. **Report** — proforma number, status, grand total; ask "issue it?" only after creation succeeds. Issuing freezes — confirm once more.
8. **Error recovery** — read the service error (e.g. "more than one power band covers 30 m³") and translate to a question ("which band: 3.5 or 5.0 kW?"). Never retry blindly.

**Rules:** one question at a time; never invent ids, prices, or items; never create clients/sites silently as a side effect; list-then-act for everything; when in doubt about money → confirm.

---

## 8. Test & rollout plan

Phases (each: commands + pytest 2–6 tests + docs):
- **P0** — list/search/show commands for core entities + JSON envelope. **Done 2026-09-09.**
- **P1** — `client_save` / `site_save` / admin-only deletes. **Done 2026-09-09.** Catalog write commands still out of scope.
- **P2** — `--volume-m3`, line add/update/remove, issue/change/accept/reject/unaccept/unreject, `proforma_pdf`. **Done 2026-09-09.** `create_proforma` now prints the JSON envelope.
- **P3** — `seed_prod` + agent badges + [`docs/pi-playbook.md`](pi-playbook.md). **Done 2026-09-09.** One Pi, two Django users.
- Full suite stays ≥ 225 green (current baseline); dry-run demos with `seed_demo` data before any real data.

---

## 9. Open decisions for Pedro

1. ~~Confirm `fri-uni_v2` is the canonical repo~~ → **settled by activity**: all PRs #1–#7 landed on `fri-uni_v2`. v1 `fri-uni` still to be archived by Pedro on GitHub (cosmetic).
2. ~~Agent accounts A vs B~~ → **B**: `agent@` staff + `agent-admin@` for confirmed deletes. `seed_prod` / `seed_demo`.
3. Should the agent ever auto-issue without an explicit second confirmation? (Recommend: no.)
4. New mode flag name: `--volume-m3` on `create_proforma` vs a separate `create_proforma_default` command. (Recommend the flag.)
5. ~~VAT math is product-backlog~~ → **RESOLVED (landed)**: VAT math + quote validity now live in services (`quote_vat_breakdown`, `_apply_line_and_labour_vat`, `total_with_vat`) and CLI `--validity-days` — agent layer needs no command changes; totals read net + IVA.
6. NEW — quote expiry: display-only today. Should the agent flag (or auto-extend on change) proformas whose `valid_until` has passed when listing/searching? (Recommend: surface `expired` in `proforma_list` output; no auto-action.)
7. NEW — agent + company logo/letterhead: keep logo upload web-UI-only for now? (Recommend: yes — binary upload stays a staff page action.)

---

## Appendix A — Field cheat sheet (list/display essentials)

- **Company** (singleton issuer): name, tax_number (9), street, postal_code, city, country_code, phone (+ phone_country FK, phone_note), email, contact_name, contact_position FK, iban (validated), logo (file, optional), `singleton=True`
- **Client**: name, tax_number (9, PT), street, postal_code, city, country_code, phone, email, contact_name, contact_position
- **Site**: client FK, is_headquarters, alias_1..4, street/postal/city, phone/email, contact, notes
- **Item**: sub_family FK (indoor only), brand FK, vat_rate FK, internal_code, kind (indoor|outdoor), power FK, max_indoor_ports (outdoor), list_price, is_default
- **Power**: power, unit (e.g. kW), volume_from_m3, volume_to_m3, default_indoor FK
- **ItemMatch**: outdoor FK, indoor FK, is_default
- **SubFamily**: family FK, brand FK, name, is_default — display `family / name`
- **Proforma**: site FK, number, status (draft|issued), discounts (commercial %, financial %), extra_labour, observations, override_checks, **validity_days (default 7)**, **issued_at / valid_until (frozen at issue)**, totals — net: equipment_subtotal, tubing_total, discount amounts, grand_total; **IVA: vat_amount, total_with_vat (payable)** — snapshot client_*/site_* fields
- **ProformaLine**: proforma FK, item FK, parent_line FK (indoor→outdoor), quantity, extra_tubing, tubing_length FK, unit_price, tubing_amount, line_total, **vat_code/vat_label/vat_rate/vat_amount snapshots (frozen at issue)**, snapshot brand/family/code/kind/power fields
- **Always-on (audit)**: created_at/updated_at/created_by/updated_by/deleted_at/deleted_by — live rows only unless deleted

## Appendix B — Existing service index (commands must call these)

`create_draft, update_draft, add_line (incl. default split auto-pair), update_line, remove_line, add_default_split (volume→band→default indoor), issue_proforma (now freezes IVA + validity), change_proforma (copies validity_days), accept/unaccept/reject/unreject_proforma, save_client, delete_client, delete_site, save_item (price w/ reason), sync_item_matches, save_vat_rate, save_power (bands + default indoor), save_tubing_length (price w/ reason), save_parameter, save_company, get_company, quote_vat_breakdown, quote_template_context, _apply_line_and_labour_vat, validity_days_value, validate_iban, display_iban, next_proforma_number, recompute_draft_totals, grouped_proforma_lines, power_for_volume, validators (NIF, phone, codes, IBAN)`

## Appendix C — Example end-to-end agent session (voice)

```
Human:  "I need a quote for the Lisbon shop — one of those default systems,
         the room is about 45 square... I mean cubic metres."
Agent:  "I'll search sites: Lisbon shop — is it 'FRI-Store Lisboa, Av. da
         Liberdade'? (id 7) [yes]  45 m³ → power band 5.0 kW. Default indoor
         FRI-12-FR + matched outdoor. Extra tubing? [no] Create draft?"
Human:  "Yes, and issue it."
Agent:  "Created + issued: proforma 2026/0043 — net €1.980,00, IVA €455,40,
         total com IVA €2.435,40, valid until <issue + 7 days>. PDF ready:
         proforma_pdf --proforma <id> --out quote.pdf"
```
