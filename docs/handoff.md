# Session handoff

> **Last updated:** 2026-09-07 12:50 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including an upfront-payment discount. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog is staff pages (Items daily; Families / Sub-families / Manufacturers / VAT / Parameters / Tubing setup). CLI: `create_proforma`.

## Start here (new agent)

Staff app is **`proformas`** (`accounts` is User/login only). Playbook: [`docs/project-plan.md`](project-plan.md). Schema: [`docs/data-points.md`](data-points.md). Chrome: [`docs/front-end-project-plan.md`](front-end-project-plan.md).

**NIF and phone validation:** [`.cursor/rules/portuguese-nif-and-phone.mdc`](../.cursor/rules/portuguese-nif-and-phone.mdc) — reuse `validate_tax_number`, `validate_phone_number`, `configure_nine_digit_form_field` in `proformas/services.py`.

Catalog: **family → sub-family → item**, plus **manufacturer** (`Brand`) and **VAT rate** on the item. Sales price is edited only on the manufacturer pricelist (reason required). Django admin is users and audit only.

Do not run `seed_demo` in production. Fresh local DB: `rm -f db.sqlite3`, then `migrate` and `seed_demo`. Restart `runserver` after schema changes. After pulling this tree, run **`migrate`** (migrations `0015` + `0016`).

**Proforma document life:** `draft` | `issued` only. **Accepted** and **rejected** are overlays (`accepted_at` / `rejected_at`), mutually exclusive (clear one before marking the other). **Change** is blocked when accepted or rejected (or already superseded). There is no `cancelled` status (legacy rows mapped to `issued` in `0016`).

## Done (this session)

- **Crash/freeze audit:** [`docs/reviews/error-dead-ends-2026-09-07-1238.md`](reviews/error-dead-ends-2026-09-07-1238.md) (independent review + Bugbot comparison)
- **H fixes:** PDF build errors → redirect + message (not 500); new-draft create catches `ValidationError`; `ParameterForm` validates default discount percent
- **M fixes:** Hardened accept/reject confirm JS (`proforma-detail.js`); `issue_proforma` atomic + row lock; catalog delete guards when used on lines; `select_for_update` on accept/reject/unaccept/unreject/change; migration `0016` maps legacy `cancelled` → `issued`
- **L fixes:** PDF activity log failure no longer blocks download; Issue header validation flash; staff delete → message not bare 403; drawer `IntegrityError` → form error; `seed_demo` tolerates failed demo change
- **Rejected overlay (same tree):** `rejected_at`, migrations `0015`/`0016`, list/detail pills, confirm before mark accepted/rejected, tests in `test_rejected.py`
- **New-draft form + list sort (same tree):** client-then-site drawer, sortable proforma list, tests in `test_new_draft_form.py` / `test_proforma_list_sort.py`
- **Tests:** **133 passing** (`pytest`); new `test_error_dead_ends.py`

## Done (earlier)

- Phases 1–8, catalog slice, VAT on items, setup cards, line cascade, `seed_demo`, client/site NIF+phone+contact, `accepted_at`, Change/supersede links, client billing identity (see prior handoff / git history)

## Not done

- Production deploy
- Company letterhead on PDF
- Real catalog prices
- Volume auto-pick; indoor/outdoor auto-pair
- VAT on proforma line math / snapshots / PDF
- Proforma snapshot fields for site/client contact on issued PDFs
- Email send / stored PDFs / Google OAuth / dark theme
- Enable non-PT phone countries in UI (table seeded; PT only disabled selector)
- **Git commit** of this working tree

## Next

1. Run `migrate` locally if not already (`0015`, `0016`); hard-refresh issued detail — confirm Mark accepted / Mark rejected (No cancels, Yes applies)
2. Commit when ready (rejected overlay + error-dead-end fixes + new-draft/sort in one or split PRs)
3. VAT on quote math / PDF — unchanged product backlog

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
