# Project plan (implementation playbook)

Stoppable phased build for the HVAC proforma staff app. Product scope lives in [`preliminary_project-plan.md`](preliminary_project-plan.md). Schema lives in [`data-points.md`](data-points.md). **Do not invent tables, fields, or product features that contradict those files.**

This file is the durable backlog **and** the instructions a new agent needs to implement one phase at a time until a working app exists.

## How to use

1. Read [`handoff.md`](handoff.md), then this file, then [`data-points.md`](data-points.md) before touching models.
2. Before any staff HTML/CSS/JS, read [`front-end-project-plan.md`](front-end-project-plan.md) (dashboard vs work layout, gear menu, list+drawer, language on dashboard only).
3. Implement **one phase**. Stop when that phase’s “Done when” is true and its tests pass.
4. On session-handoff: mark completed checkboxes `- [x] ... (completed YYYY-MM-DD)`. Leave unfinished items `[ ]`.
5. Do not start a later phase’s UI until earlier phases that it depends on are done.
6. Commands: `.venv/bin/python manage.py …` and `pytest`. No emoji in logs.

Already in the repo (do not rebuild): Django `conf/` settings, `accounts.User` (email login, unused Google OAuth flags), pytest-django, deploy stubs.

## Architecture (every phase)

```text
views / management commands  →  proformas/services.py  →  models.py
```

- New Django app **`proformas`** for all domain tables. Keep **`accounts`** for `User`.
- Plain Django templates + plain JavaScript. Project-level `templates/` and `static/` (add `DIRS` in `conf/settings/base.py`).
- Money math, numbering, issue/lock, snapshots: **`proformas/services.py` only** — not views, not templates, not admin `save_model` copies of the same logic.
- Issued proformas are frozen. Corrections = a new proforma. `cancelled` does not unlock.
- Tests: pytest-django, **2–6 tests per phase**. Prefer service tests. No Selenium, no coverage gates, no factory-boy unless it becomes painful.

**User model vs data-points:** extend `accounts.User` with `role` (`staff` | `admin`) only. Map `role=admin` → `is_staff=True` (Django contrib admin). `role=staff` → `is_staff=False`; staff get 403 on `/admin/`. Do **not** add always-on audit columns to `User`. Do **not** add a `language` column. All `proformas` entities get always-on columns from data-points (`created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`, `deleted_by`). Unique keys apply to **live** rows only (`deleted_at` is null).

## Locked decisions (implementation)

- **Surfaces:** Django contrib admin for catalog, parameters, users, audit. Custom templates for clients, sites, proforma draft → issue → on-screen quote → PDF. Django admin is English (contrib).
- **Login:** email + password. Google OAuth fields stay unused.
- **i18n:** CentCompras / warehouse_V2 pattern, **not** Django gettext. Spec: [warehouse_V2 `docs/i18n-pattern.md`](https://github.com/neopmpmtj/warehouse_V2/blob/main/docs/i18n-pattern.md) and [`front-end-project-plan.md`](front-end-project-plan.md). English fallback in HTML; JS dictionaries + `data-i18n*`; `en` | `pt`; `localStorage` + cookie `fu-lang`. Language `<select>` **only on the dashboard**. Work pages read the stored value; they have no language control. No `.po` files, no `LocaleMiddleware` / `{% trans %}`, no dark/light theme unless asked later.
- **PDF language:** JS also sets a `fu-lang` cookie. On-screen quote chrome can use JS; WeasyPrint uses a small Python string dict keyed by that cookie (`en` default).
- **PDF:** visualize issued quote on screen; also `build_proforma_pdf(proforma) -> bytes` for download (later email can attach the same bytes). Do not store files. Do not send email.
- **Seed:** `seed_catalog` management command, idempotent, not auto-run in production.
- **CLI:** Phase 8. Flag contract is in data-points.

---

## Phase 1 — Login, roles, i18n, staff shell

**Goal:** Staff can sign in, land on a **dashboard**, set EN/PT once there, and use work-page chrome (topbar + gear). Staff cannot open Django admin.

**Done when:** login/logout work; dashboard language select persists via `fu-lang`; work pages have **no** language control; gear shows email + sign out; `role=staff` is 403 on `/admin/`; `role=admin` can open `/admin/`; pytest for this phase is green.

Layout details: [`front-end-project-plan.md`](front-end-project-plan.md).

### Files

- `accounts/models.py` — add `role` (`staff` | `admin`)
- `accounts/admin.py` — show/edit `role`; keep OAuth fields unused
- `accounts/migrations/` — one migration
- `conf/urls.py` — login, logout, dashboard as home; keep `admin/`
- `conf/settings/base.py` — `LOGIN_URL`, `LOGIN_REDIRECT_URL` (dashboard), `TEMPLATES["DIRS"]`, `STATICFILES_DIRS`
- `templates/registration/login.html`
- `templates/dashboard.html` — dashboard layout (language select + gear + card grid)
- `templates/work_base.html` (or equivalent) — work layout: eyebrow, `h1`, nav, gear; **no** language select
- `templates/includes/account_settings.html` — gear popover
- `static/js/i18n.js` — `normalizeLang`, `t()`, `applyStaticI18n()`, `safeGet`/`safeSet`; write `fu-lang` to **localStorage and cookie**
- `static/css/` — tokens + dashboard + topbar + settings popover (see front-end plan)

### Notes

- Use `django.contrib.auth` views for login/logout. Home **is** the dashboard.
- Keep `LANGUAGE_CODE = "en-gb"`. Templates ship English. `USE_I18N` may stay True; it is unused for UI.
- Early `<head>` script: read `fu-lang`, set `document.documentElement.lang` to `en` or `pt-PT` before paint (warehouse anti-flash).
- Language `<select>` **only on the dashboard** (warehouse `pref-language` / D38). Work pages read `fu-lang` only.
- One shared chrome dictionary in `i18n.js`. Later pages add keys or a page `*_i18n.js` if large. Normalize any value starting with `pt` to `pt`; alias `"pt-PT"` → `pt`.
- Work nav: Home (dashboard), Clients, Sites, Proformas. Dashboard cards: Clients, Sites, Proformas; Catalog/Admin card only if `role=admin`.
- Gear: Settings, signed-in email, Sign out. No Help, no “sign out other devices”, no theme.
- `created_by` on future proformas rows: the logged-in user.

### Tests (accounts / thin views)

- Anonymous request to home redirects to login.
- `role=staff` user gets 403 (or redirect-away) on `/admin/`.
- `normalizeLang("pt-PT") == "pt"` (tiny Python helper mirroring the JS rule). Optional: dashboard template contains the language `<select>`; work base does not.

### Checkboxes

- [x] Phase 1: `role` on `User`, login/logout, staff shell, `fu-lang` i18n (completed 2026-09-06)
- [x] Phase 1 tests (completed 2026-09-06)

---

## Phase 2 — Domain models, audit, parameters

**Goal:** All data-points tables exist and migrate. No staff CRUD UI yet (admin stubs ok).

**Done when:** `migrate` applies; live uniqueness and soft-delete reuse work; log helpers exist.

### Files

- `proformas/` — app: `models.py` (split modules only if `models.py` becomes unwieldy), `services.py`, `apps.py`, `admin.py` (empty or register without custom UI)
- `proformas/migrations/0001_initial.py`
- `conf/settings/base.py` — add `"proformas"` to `INSTALLED_APPS`

### Models (fields exactly as data-points)

`Parameter`, `Client`, `Site`, `Brand`, `Style`, `Model` (catalog machine; Django model name e.g. `EquipmentModel` if `Model` is too awkward — document the ORM name in a one-line comment), `TubingLength`, `Proforma`, `ProformaLine`, `ChangeLog`, `ActivityLog`.

Always-on columns on every proformas entity. Soft-delete manager: default queryset live rows only; `all_objects` (or similar) for including deleted.

`ChangeLog`: entity type, entity id, field, old, new, actor, actor type (`user` | `system`), time, reason (required only when the field is reason-required).

`ActivityLog`: actor, actor type, action, object type, object id, time, details.

`Parameter` known keys (seed in Phase 3): `currency`, `default_upfront_discount_percent`, `tubing_length_unit`.

### Notes

- `proformas/services.py`: `log_change(...)`, `log_activity(...)`. Views/CLI must not write log tables directly.
- Unique constraints: live `email` is already on `User`; live `clients.name`; live `brands.name`; live `styles.name` per brand; live `models` style+kind+btu; live `tubing_lengths.length`; live `parameters.key`; live `proformas.number`. Partial unique indexes (PostgreSQL) or equivalent live-only uniqueness. SQLite is local default — prefer constraints that work on both, or document that live uniqueness is enforced in services if a partial index is prod-only.
- Do not implement issue/lock behaviour yet beyond storing `status` and nullable snapshot/total fields.

### Tests

- Creating two live clients with the same name fails.
- Soft-deleted client name can be reused by a new live client.

### Checkboxes

- [x] Phase 2: `proformas` models + migrate + log helpers (completed 2026-09-06)
- [x] Phase 2 tests (completed 2026-09-06)

---

## Phase 3 — Catalog + parameters in Django admin + seed

**Goal:** Admin can maintain catalog and parameters. Demo data via command.

**Done when:** admin can CRUD brands → styles → models and tubing lengths; changing `list_price` or tubing `price` requires a reason and writes `change_logs`; `seed_catalog` is idempotent.

### Files

- `proformas/admin.py` — Brand, Style, EquipmentModel, TubingLength, Parameter, ChangeLog (read-only), ActivityLog (read-only)
- `proformas/services.py` — reason-required price updates
- `proformas/management/commands/seed_catalog.py`
- `accounts` admin already provisions users (Phase 1)

### Notes

- Reason-required fields: `models.list_price`, `tubing_lengths.price`. Admin form must collect `reason` on those changes. Creating a row does not need a reason.
- `seed_catalog`: Mitsubishi, LG, Nippon (style Split) plus Daikin PT air-to-air ranges (Sensira, Comfora, Perfera, Perfera Floor, Stylish, Emura, Ururu Sarara); indoor/outdoor models at 9k/12k/18k with demo list prices; a few tubing lengths; parameters `currency=EUR`, `default_upfront_discount_percent` (pick a number, e.g. 10), `tubing_length_unit=m`. Safe to run twice. Do not call it from production deploy.
- Staff still must not use `/admin/`. Catalog is admin-only by design.

### Tests

- Updating list price without reason fails; with reason writes a change log.
- `seed_catalog` twice does not duplicate live brands.

### Checkboxes

- [x] Phase 3: catalog/parameters admin + reason-required prices (completed 2026-09-06)
- [x] Phase 3: `seed_catalog` (completed 2026-09-06)
- [x] Phase 3 tests (completed 2026-09-06)

---

## Phase 4 — Clients and sites (custom UI)

**Goal:** Staff CRUD for customers and work locations.

**Done when:** staff can create/edit/list clients and sites; soft-deleted rows hidden; live client name unique.

### Files

- `proformas/views.py`, `proformas/forms.py`, `proformas/urls.py`
- `templates/proformas/client_list.html`, `site_list.html` (work layout)
- `templates/includes/drawer.html` (shared) — create/edit in the drawer, not separate full-page forms
- `static/js/` — drawer open/close + i18n keys (`data-i18n`; English fallback in HTML)
- Wire URLs into `conf/urls.py`

### Notes

- UX: list + drawer as in [`front-end-project-plan.md`](front-end-project-plan.md). Server-rendered tables. Sites are a first-class list page (do not nest sites inside the client drawer).
- Client: `name` required; `phone`, `email` optional.
- Site: `client` required; `alias_1` required; `alias_2`–`alias_4` optional; `street`, `postal_code`, `city`, `notes` optional. Four alias columns, not a list.
- Soft delete from the drawer (do not hard-delete). Lists use the live manager. **Only admin** may soft-delete; staff (demo manager) can create and edit but Delete is hidden and POSTs return 403.
- Login required. Both `staff` and `admin` may use these screens.

### Tests

- Authenticated staff can create a client and a site.
- Duplicate live client name is rejected.

### Checkboxes

- [x] Phase 4: clients and sites custom UI (completed 2026-09-06)
- [x] Phase 4 tests (completed 2026-09-06)

---

## Phase 5 — Draft proformas and lines

**Goal:** Staff build an editable draft quote for one site.

**Done when:** create draft on a site; add/remove lines; extra tubing per line; header discount, extra labour, observations; live totals on screen; number assigned on create.

### Files

- `proformas/services.py` — `create_draft`, `add_line` / `update_line` / `remove_line`, `recompute_draft_totals` (draft totals may be stored or derived; issued totals are Phase 6)
- `proformas/views.py` / forms / templates: proforma **list** + **work page** (header fields on the page; lines `.grid`; add/edit line in the shared drawer). See [`front-end-project-plan.md`](front-end-project-plan.md).
- i18n keys for the quoting screens

### Notes

- Number: `PF-YYYY-NNNN` (`YYYY` = create year, `NNNN` = 4-digit per-year sequence). Unique among live rows. Assign in the service, not the template.
- On create: copy `default_upfront_discount_percent` from parameters; overridable while `status=draft`.
- `extra_labour` default 0; `observations` optional.
- One machine per line. `unit_price` = current catalog list price at save. `extra_tubing` boolean; if true, `tubing_length` required and `tubing_amount` = that length’s price; else `tubing_amount=0`.
- `line_total = quantity × (unit_price + tubing_amount)`.
- Live header display (not frozen until issue):
  - `equipment_subtotal` = sum of `quantity × unit_price`
  - `tubing_total` = sum of `quantity × tubing_amount`
  - `discount_amount` = `equipment_subtotal × upfront_discount_percent / 100` (equipment only)
  - `grand_total` = `equipment_subtotal - discount_amount + tubing_total + extra_labour`
- Draft only in this phase. No PDF.

### Tests

- First draft of a year gets `PF-YYYY-0001` (or the next sequence if data exists).
- Line with tubing: formula matches data-points.
- Discount does not apply to tubing or extra labour.

### Checkboxes

- [x] Phase 5: draft proforma + lines + live totals (completed 2026-09-06)
- [x] Phase 5 tests (completed 2026-09-06)

---

## Phase 6 — Issue, freeze, cancel

**Goal:** Lock a quote. Catalog changes must not rewrite issued money or snapshot names.

**Done when:** issue snapshots and freezes; issued money updates are rejected; cancel retires without unlocking; activity log rows exist for issue and cancel.

### Files

- `proformas/services.py` — `issue_proforma`, `cancel_proforma`; refuse updates when `status != draft`
- Views: issue and cancel POST actions on the proforma page
- Snapshot field list: copy from data-points (`proformas` and `proforma_lines` snapshot sections)

### Notes

- At issue: fill snapshot fields (client name/phone/email; site aliases, address, notes; line brand/style/kind/btu/tubing_length_value); freeze `equipment_subtotal`, `tubing_total`, `discount_amount`, `grand_total` and line money; set `status=issued`.
- PDF/on-screen issued view (Phase 7) **reads snapshots**, not live catalog/client names.
- `cancelled`: status change only. Do not unlock or rewrite money.
- Soft-delete still hides mistakes from live lists.
- `activity_logs` actions include at least `issue_proforma` and `cancel_proforma`.

### Tests

- After issue, changing catalog `list_price` does not change line `unit_price` or frozen totals.
- After issue, renaming a client does not change `client_name` on the proforma.
- Service update of issued money fields raises / is rejected.
- Cancel does not set status back to draft.

### Checkboxes

- [x] Phase 6: issue snapshot/lock + cancel (completed 2026-09-06)
- [x] Phase 6 tests (completed 2026-09-06)

---

## Phase 7 — On-screen quote + PDF download

**Goal:** Staff can read an issued quote on screen and download a real PDF. Email is not sent.

**Done when:** issued HTML view shows snapshot data; Download PDF returns `application/pdf` with non-empty bytes; `fu-lang=pt` PDF/HTML contains a known Portuguese label; `build_proforma_pdf` is a service function later email can call.

### Files

- `proformas/services.py` (or `proformas/pdf.py` imported by services) — `build_proforma_pdf(proforma) -> bytes`
- `proformas/quote_i18n.py` — small EN/PT dict for quote labels (keep keys aligned with JS)
- Quote HTML template (on-screen) + print/PDF stylesheet
- Download view; `activity_logs` action `download_pdf` is optional but listed in data-points as typical
- `requirements.txt` — WeasyPrint
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — Debian packages for WeasyPrint (`pango` / `cairo` / related)

### Notes

- Generate on download. **Do not** save PDF files or add a file table.
- Do **not** implement email, Gmail, or local SMTP. The attachment seam is the `bytes` return value.
- On-screen visualization is the MVP staff experience; PDF exists so a later mailer can attach it.
- Language: cookie `fu-lang` (`en` default). Staff switch the header to English before download for a UK client.
- Draft preview PDF is out of scope (data-points: draft preview must not lock; we are not adding it).

### Tests

- Issued HTML contains snapshot `client_name`, not a later renamed live name.
- PDF response content-type `application/pdf` and body length > 0.
- With `fu-lang=pt`, rendered quote HTML or PDF text includes a known Portuguese label (e.g. a totals heading).

### Checkboxes

- [x] Phase 7: issued on-screen quote + WeasyPrint download (completed 2026-09-06)
- [x] Phase 7: `build_proforma_pdf` seam; WeasyPrint noted in DEPLOYMENT.md (completed 2026-09-06)
- [x] Phase 7 tests (completed 2026-09-06)

---

## Phase 8 — CLI

**Goal:** One management command creates a proforma the same way the website does (LLM/agent invocation).

**Done when:** flags match data-points; same validation and snapshots as web; `--issue` locks; invalid user/site fails.

### Files

- `proformas/management/commands/create_proforma.py`
- Calls `proformas/services.py` only (no duplicated math)

### Flags

Mandatory:

- `--user` — staff email → `created_by` (`actor_type=user`)
- `--site` — site id
- at least one `--line` — `model_id:qty` or `model_id:qty:tubing_length_id`

Optional:

- `--discount-percent`
- `--extra-labour`
- `--observations`
- `--issue`

### Tests

- Create draft with one line; number assigned; `created_by` is `--user`.
- `--issue` results in `status=issued` and frozen totals.
- Unknown user or site exits non-zero / raises a clear error.

### Checkboxes

- [x] Phase 8: `create_proforma` management command (completed 2026-09-06)
- [x] Phase 8 tests (completed 2026-09-06)

---

## Demo seed

**Goal:** One command fills a clickable demo: catalog, two users, clients, sites, and proformas in draft / issued / cancelled.

- [x] `seed_demo` users, clients, sites, sample quotes (completed 2026-09-06)
- [x] Manager (`staff`) cannot soft-delete clients or sites; admin can (completed 2026-09-06)

- [x] Catalog: family → sub-family → item + manufacturer; internal_code; is_default; optional max_volume_m3 (completed 2026-09-06)
- [x] Staff Items page (light) + setup cards/pages for Families, Sub-families, Manufacturers pricelist (completed 2026-09-06)
- [x] Line drawer cascade Family → Sub-family → Manufacturer → Item with defaults (completed 2026-09-06)
- [x] VAT rates (PT 23/13/6/Exempt) on items + Setup cards for VAT, Parameters, Tubing (completed 2026-09-06)
- [x] Optional manufacturer on sub-family; New item / line drawer lock when set (completed 2026-09-06)
- [x] Powers lookup (power + unit) replaces item BTU; setup card + line snapshots (completed 2026-09-06)

Do not run `seed_demo` from production deploy.

---

## Out of this build

Do not implement in these phases:

- Email send, mailer, Gmail vs local account, background workers
- Stored PDFs / media file table
- Google OAuth login
- Client portal, public site, mobile, shared HTTP API
- Official invoices, payments, tax, accounting export
- `model_default_matches` (indoor/outdoor auto-pair)
- Stock, supplier POs, install calendar
- Unlocking or revising issued proformas
- Dark/light theme (warehouse has it; skip unless asked)
- Django gettext `.po` / `LocaleMiddleware` UI translation

## Backlog (post-MVP slices)

- [x] Proforma `accepted_at`: mark issued quotes as accepted; cancel clears mark; list/detail UI (completed 2026-09-07)
- [x] Proforma list Edit/Change actions + supersede links (`superseded_by` / `replaces`) (completed 2026-09-07)
- [x] Drop `cancelled` status; `rejected_at` overlay on issued (sibling to `accepted_at`); Change blocked when rejected (completed 2026-09-07)
- [x] Crash/freeze review + H/M/L remediations from [`error-dead-ends-2026-09-07-1238.md`](reviews/error-dead-ends-2026-09-07-1238.md) (completed 2026-09-07)
- [x] Proforma list Accept / Reject / Clear so staff need not Change an issued quote to mark outcome (completed 2026-09-07)
- [x] Line drawer: hide tubing length until extra tubing; default shortest length; store `extra_tubing_metres` on the proforma (completed 2026-09-07)

## Tests policy

| Phase | What to prove |
| ----- | ------------- |
| 1 | Auth gate + staff cannot use `/admin/` + lang normalize |
| 2 | Live uniqueness + soft-delete reuse |
| 3 | Reason-required price + idempotent seed |
| 4 | Staff can create client/site |
| 5 | Numbering + tubing/discount math |
| 6 | Issue freeze + snapshot stability + cancel |
| 7 | Snapshot on screen + PDF bytes + PT label |
| 8 | CLI create / issue / bad user |

If a phase is done and tests fail, fix that phase before starting the next.
