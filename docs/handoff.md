# Session handoff

> **Last updated:** 2026-09-09 10:11 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including commercial and financial discounts and IVA. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog is staff pages (Items daily; Families / Design lines / Manufacturers / VAT / Parameters / Company / Tubing setup). CLI: `create_proforma`.

## Start here (new agent)

Staff app is **`proformas`** (`accounts` is User/login only). Playbook: [`docs/project-plan.md`](project-plan.md). Schema: [`docs/data-points.md`](data-points.md). Chrome: [`docs/front-end-project-plan.md`](front-end-project-plan.md).

**NIF and phone validation:** [`.cursor/rules/portuguese-nif-and-phone.mdc`](../.cursor/rules/portuguese-nif-and-phone.mdc) — reuse `validate_tax_number`, `validate_phone_number`, and `configure_nine_digit_form_field` in `proformas/services.py`. Portuguese IBAN: `validate_iban` in the same module.

Catalog: **family → indoor design line (`sub_families`) → indoor item**; outdoor items have **no** design line (brand + power + `max_indoor_ports` + code). Pairing is **`item_matches`**. Quote lines group under the outdoor (`parent_line`). Sales price is edited only on the manufacturer pricelist (reason required). Django admin is users and audit only.

Do not run `seed_demo` in production. Fresh local DB: `rm -f db.sqlite3`, then `migrate` and `seed_demo`. Restart `runserver` after schema changes. After pulling this tree, run **`migrate`** (migrations `0023` then `0024`).

**Two tables vs one:** `clients` / `sites` are different nouns (quote → site). Indoor/outdoor stay one `items` table + `item_matches`. See [`data-points.md`](data-points.md) and preliminary-plan update 2026-09-07.

**Proforma document life:** `draft` | `issued` only. **Accepted** and **rejected** are overlays (`accepted_at` / `rejected_at`), mutually exclusive (clear one before marking the other). **Change** is blocked when accepted or rejected (or already superseded). There is no `cancelled` status (legacy rows mapped to `issued` in `0016`).

**Money:** list prices and `grand_total` are net (sem IVA). `vat_amount` / `total_with_vat` are the IVA layer; the list and quote payable is `total_with_vat`. Extra labour IVA uses the default `vat_rates` row.

**Validity:** company default `parameters.default_validity_days` (7). Draft `validity_days` is overridable. Issue freezes `issued_at` and `valid_until` (Lisbon date + days). Display only.

**Issuer:** singleton `company` row (Fribila). Staff setup page at `/company/`. Always live — not snapshotted onto issued proformas. Quote HTML/PDF still shows hardcoded `fri-uni` until the letterhead slice.

**AC systems:** **Split** = 1 outdoor (`ports=1`) + 1 indoor (staff start from the indoor; default match auto-adds the outdoor). **Default** = type room m³ → `powers` band → that row’s default indoor + matched 1-port outdoor (qty 1). **Multi** = 1 outdoor (`ports≥2`) + 2+ indoors (staff start from the outdoor, then Add indoor). Extra tubing stays on indoor runs. Editing a 1-port outdoor line uses the outdoor drawer (not indoor/design-line). **Override checks** on the draft header skips multi indoor-count rules (add past ports; issue without 2..ports). Split stays exact-one indoor.

**Reviews:** [`reviews/code-review-2026-09-08-0818.md`](reviews/code-review-2026-09-08-0818.md) (concluded). Error-dead-ends audit archived: [`archive/error-dead-ends-2026-09-07-1238.md`](archive/error-dead-ends-2026-09-07-1238.md).

## Done (this session)

- **Company singleton:** `Company` model, migration `0024` seeds one Fribila row (address, phone, phone note, email; NIF/IBAN/contact/logo blank for staff to fill later). `get_company()` / `save_company()`; Portuguese IBAN validator. Setup page (form on the page, multipart logo, no delete). Dashboard Setup card. Staff and admin may edit.
- **Tests:** **198 passing** (`pytest`), including company seed, singleton, IBAN, staff GET/POST, NIF/phone length.
- Pillow added to `requirements.txt` for `ImageField` uploads.

## Done (earlier)

- VAT on quotes; validity window; financial vs commercial discounts; code review 2026-09-08; M1 stale `default_indoor`; error-dead-ends audit; PDF/seed hardening; Add default volume split + extra tubing; override checks; AC pairing; Phases 1–8; catalog slice; VAT rates on items; client/site identity; Change/supersede

## Not done

- Quote/PDF letterhead from the live company row (still hardcoded `fri-uni`)
- Production deploy
- Real catalog prices
- Indoor BTU vs outdoor capacity math
- Proforma snapshot fields for site contact on issued PDFs
- Email send / stored PDFs / Google OAuth / dark theme
- Enable non-PT phone countries in UI (table seeded; PT only disabled selector)
- Heating expansion (backlog in project-plan)
- PDF application-level timeout; confirm-dialog E2E; concurrency stress tests (backlog)

## Next

1. Quote/PDF letterhead reads live `get_company()` — name, address, phone + note, email, contact, IBAN, logo
2. Production deploy when ready

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
rm -f db.sqlite3   # only when resetting local DB
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
pytest
```
