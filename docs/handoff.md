# Session handoff

> **Last updated:** 2026-09-08 08:04 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including an upfront-payment discount. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog is staff pages (Items daily; Families / Design lines / Manufacturers / VAT / Parameters / Tubing setup). CLI: `create_proforma`.

## Start here (new agent)

Staff app is **`proformas`** (`accounts` is User/login only). Playbook: [`docs/project-plan.md`](project-plan.md). Schema: [`docs/data-points.md`](data-points.md). Chrome: [`docs/front-end-project-plan.md`](front-end-project-plan.md).

**NIF and phone validation:** [`.cursor/rules/portuguese-nif-and-phone.mdc`](../.cursor/rules/portuguese-nif-and-phone.mdc) — reuse `validate_tax_number`, `validate_phone_number`, `configure_nine_digit_form_field` in `proformas/services.py`.

Catalog: **family → indoor design line (`sub_families`) → indoor item**; outdoor items have **no** design line (brand + power + `max_indoor_ports` + code). Pairing is **`item_matches`**. Quote lines group under the outdoor (`parent_line`). Sales price is edited only on the manufacturer pricelist (reason required). Django admin is users and audit only.

Do not run `seed_demo` in production. Fresh local DB: `rm -f db.sqlite3`, then `migrate` and `seed_demo`. Restart `runserver` after schema changes. After pulling this tree, run **`migrate`** (migration `0021`).

**Two tables vs one:** `clients` / `sites` are different nouns (quote → site). Indoor/outdoor stay one `items` table + `item_matches`. See [`data-points.md`](data-points.md) and preliminary-plan update 2026-09-07.

**Proforma document life:** `draft` | `issued` only. **Accepted** and **rejected** are overlays (`accepted_at` / `rejected_at`), mutually exclusive (clear one before marking the other). **Change** is blocked when accepted or rejected (or already superseded). There is no `cancelled` status (legacy rows mapped to `issued` in `0016`).

**AC systems:** **Split** = 1 outdoor (`ports=1`) + 1 indoor (staff start from the indoor; default match auto-adds the outdoor). **Default** = type room m³ → `powers` band → that row’s default indoor + matched 1-port outdoor (qty 1). **Multi** = 1 outdoor (`ports≥2`) + 2+ indoors (staff start from the outdoor, then Add indoor). Extra tubing stays on indoor runs. Editing a 1-port outdoor line uses the outdoor drawer (not indoor/design-line). **Override checks** on the draft header skips multi indoor-count rules (add past ports; issue without 2..ports). Split stays exact-one indoor.

## Done (this session)

- **Add default:** draft work-page action; room m³ picks a `powers` band and inserts that row’s default indoor + matched 1-port outdoor (qty 1). Optional extra tubing checkbox + length (same as split). Migration `0021`. Dropped `items.max_volume_m3`. Seed: 0–20 / 21–35 / 36–50 m³; Daikin Perfera defaults.
- **Tests:** **163 passing** (`pytest`)

## Done (earlier)

- Override checks on multi occupancy
- Migration `0019` lookup seeds; pairing leftover cleanup; two-tables-vs-one docs; 1-port split outdoor edit/delete
- AC pairing model; seed rewrite; migration `0018`; crash/freeze audit; rejected overlay; Phases 1–8; catalog slice; VAT; client/site identity; Change/supersede

## Not done

- Production deploy
- Company letterhead on PDF
- Real catalog prices
- Indoor BTU vs outdoor capacity math
- VAT on proforma line math / snapshots / PDF
- Proforma snapshot fields for site/client contact on issued PDFs
- Email send / stored PDFs / Google OAuth / dark theme
- Enable non-PT phone countries in UI (table seeded; PT only disabled selector)

## Next

1. VAT on quote math / PDF — product backlog
2. Production deploy when ready

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
rm -f db.sqlite3   # only when resetting local dev DB
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
pytest
```
