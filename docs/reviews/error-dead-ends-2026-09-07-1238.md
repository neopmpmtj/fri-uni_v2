# Code review — crash / freeze dead ends

> **Date:** 2026-09-07 12:38 WEST (Europe/Lisbon)  
> **Scope:** Uncommitted working tree (rejected overlay, confirm dialog, new-draft form, list sort) plus older paths that can still HTTP 500, stall a worker, or dead-end staff in the UI.  
> **Method:** Independent read of `proformas/views.py`, `proformas/services.py`, `proformas/pdf.py`, `static/js/*.js`, templates, `seed.py`; Bugbot on uncommitted changes ([Bugbot](bf683718-8181-4a00-b359-733bc01cac74)).  
> **Baseline:** [`code-review-2026-09-07-0750.md`](code-review-2026-09-07-0750.md) (client billing slice). **126 tests** green per [`handoff.md`](../handoff.md).

This is an in-progress audit (living under `docs/reviews/`). It does not change product scope. **No application code was changed** in this review.

---

## Severity (this review)

| Level | Meaning |
| ----- | ------- |
| **High** | HTTP 500 or worker stall on a normal staff action |
| **Medium** | UI dead-end, silent no-op, or inconsistent data after a partial failure |
| **Low** | Rare race, CLI-only abort, or abrupt UX without a hang |

---

## What looks solid

- **Layering:** Business rules stay in `services.py`; views mostly catch `ValidationError` on the proforma detail POST path.
- **Detail POST:** Issue, accept, reject, unaccept, unreject, line save/delete, and header save on draft all sit inside a `try/except ValidationError` block (`proforma_detail`).
- **Forms:** `ProformaHeaderForm` bounds discount 0–100; `ProformaLineForm` enforces `quantity >= 1`; empty issue blocked in `issue_proforma`.
- **HQ reassignment 500** from the 07:50 review is **fixed** — `SiteForm` disables `client` on HQ and `clean_client` rejects reassignment.
- **Frontend scripts audited:** No `while True`, no `fetch()`, no recursive loops in `static/js/`. `new-draft-form.js` and `line-form.js` are finite select-sync only.
- **i18n:** `t()` falls back to English; confirm strings exist for accept/reject.
- **No-JS:** Mark accepted/rejected buttons submit natively (confirm JS is progressive enhancement only when the script loads).

---

## Findings

### High

**H1. PDF download can 500 or stall the worker**

| | |
| --- | --- |
| **Location** | [`proformas/views.py`](../../proformas/views.py) `proforma_pdf` (≈453–466) → [`proformas/pdf.py`](../../proformas/pdf.py) `build_proforma_pdf` |
| **Age** | Older (unchanged in rejected-overlay WIP) |
| **What happens** | `proforma_pdf` calls `build_proforma_pdf(proforma, lang=lang)` with **no try/except**. WeasyPrint or system library failure (`OSError`, missing pango/cairo, bad HTML) → uncaught **HTTP 500**. Sync `HTML(string=html).write_pdf()` has **no application timeout**; gunicorn uses `--timeout 120` ([`deploy/gunicorn.service`](../../deploy/gunicorn.service)). `log_activity` runs **after** PDF generation, so a hang or crash never reaches user-facing error handling. |
| **Staff trigger** | Download PDF on any issued proforma |
| **Tests** | `test_pdf_download` / `test_portuguese_quote_label` (phase7) assert happy path only |

**H2. New-draft POST can 500 on `ValidationError`**

| | |
| --- | --- |
| **Location** | [`proformas/views.py`](../../proformas/views.py) `proforma_list` (≈227–231) → `services.create_draft` |
| **Age** | Older path; list drawer is **WIP** (`NewDraftForm`, `new-draft-form.js`) |
| **What happens** | On valid `NewDraftForm`, `create_draft(...)` is called with **no** `except ValidationError`. Failures bubble as 500: (1) number allocation exhausted after retries (`services.py` ≈298); (2) `get_parameter("default_upfront_discount_percent")` returns a value that fails `discount_percent_value` — [`ParameterForm`](../../proformas/forms.py) is free-text with no format validation. |
| **Contrast** | `proforma_detail` catches `ValidationError` for issue/accept/reject/line actions |
| **Tests** | `test_create_draft_via_drawer` covers happy path; `test_discount_over_100_rejected` is service-level only |

---

### Medium

**M1. Confirm dialog can dead-end after canceling native submit**

| | |
| --- | --- |
| **Location** | [`static/js/proforma-detail.js`](../../static/js/proforma-detail.js) (≈19–41); [`templates/proformas/proforma_detail.html`](../../templates/proformas/proforma_detail.html) (≈71–90) |
| **Age** | **WIP** (untracked JS + template confirm attrs) |
| **What happens** | Mark accepted/rejected buttons use `data-confirm-i18n`. Click handler calls `event.preventDefault()`, then `t(...)`, `dialog.showModal()`, and on Yes `form.requestSubmit(btn)` with **no try/catch or fallback**. If `t` is undefined, `showModal` throws (`InvalidStateError` if already open), or `requestSubmit` is missing/ignores the submitter, staff see **no outcome** after confirming. Empty `issue-form` POST without `action` re-renders detail with no message. Clear accepted/rejected bypass confirm (native submit). |
| **Bugbot** | **Agree** — “Confirm Yes silent no-op” |
| **Fix direction** | Guard `typeof t`, wrap `showModal` / `requestSubmit`; on failure fall back to native submit or inject hidden `action` |

**M2. `issue_proforma` is not `transaction.atomic`**

| | |
| --- | --- |
| **Location** | [`proformas/services.py`](../../proformas/services.py) `issue_proforma` (≈651–699) |
| **Age** | Older |
| **What happens** | Header snapshot, per-line catalog snapshot loop, status flip, and activity log are **not** wrapped in one transaction. Process crash mid loop leaves a draft with **partial** snapshot fields populated. Views catch only `ValidationError`; `AttributeError` / `DoesNotExist` / mid-save DB errors → **500**. |
| **Contrast** | `create_draft`, `change_proforma`, `save_client` use `@transaction.atomic` or `with transaction.atomic()` |
| **Tests** | Phase6 asserts freeze at success; no partial-issue test |

**M3. Catalog delete has no “used on a proforma line” guard**

| | |
| --- | --- |
| **Location** | [`proformas/services.py`](../../proformas/services.py) `delete_item`, `delete_family`, `delete_brand`, `delete_sub_family` (≈449–466) |
| **Age** | Older |
| **What happens** | Soft-delete proceeds without checking `ProformaLine` references. Contrast `delete_vat_rate`, `delete_power`, `delete_tubing_length`, which guard usage. Soft-deleted catalog rows still referenced by draft/issued lines can break later issue, change, or line edit (choices hide live rows; `PROTECT` on FK prevents hard delete). Usually **ValidationError or broken UX**, not always immediate 500. |
| **Staff trigger** | Admin deletes catalog row still on a proforma line |

**M4. Change / accept / reject have no row lock**

| | |
| --- | --- |
| **Location** | `change_proforma`, `accept_proforma`, `reject_proforma` + matching views |
| **Age** | Change **older**; reject gate + confirm **WIP** |
| **What happens** | No `select_for_update`. Two concurrent Change posts can both pass `can_change`, then collide on `superseded_by` / number → uncaught `IntegrityError` or duplicate revision drafts. Double-click Yes on confirm usually yields second `ValidationError` (flashed message) — **not a freeze**, but duplicate activity logs possible under concurrency. |
| **Tests** | None for concurrency |

**M5. Legacy `cancelled` rows lose detail-page actions**

| | |
| --- | --- |
| **Location** | Migration [`0015_proforma_rejected_at.py`](../../proformas/migrations/0015_proforma_rejected_at.py); [`templates/proformas/proforma_detail.html`](../../templates/proformas/proforma_detail.html) (≈51–91) |
| **Age** | **WIP** (dropped `cancelled` status) |
| **What happens** | Migration alters `status` choices to `draft` \| `issued` only — it does **not** rewrite existing `status='cancelled'` rows. Detail quote/PDF and outcome controls are gated on `is_issued`. Legacy cancelled records remain listable but the work page shows **neither** draft nor issued actions. Direct quote/PDF URLs still work (`_issued_quote` 404s only drafts). |
| **Bugbot** | **Agree with caveat** — real data-migration gap; not a process crash. Local dev DB was wiped; production not deployed. |
| **Fix direction** | Data migration: map `cancelled` → `issued` (or delete demo rows); optional read-only quote/PDF branch for orphan statuses |

---

### Low

**L1. Activity log failure after successful PDF → 500**

`proforma_pdf` builds PDF bytes first; if `log_activity` then fails, staff get **500** after an expensive render (`views.py` ≈457–463). Older.

**L2. Numbering past 9999**

`next_proforma_number` uses string-max sequencing (`services.py` ≈218–230). Past `PF-YYYY-9999`, allocation logic can mis-order; retries soften collisions but logic stays fragile. Covered at service level in `test_review_fixes`; older.

**L3. Invalid Issue header re-renders without flash**

Invalid `ProformaHeaderForm` on Issue falls through to re-render with field errors but no `messages.error` (`proforma_detail` ≈354–368). Not a crash; easy to miss. Older.

**L4. Staff delete → 403, not message**

`require_delete_permission` raises `PermissionDenied` (`services.py` ≈386–388). Django returns **403**; no flash. Correct denial, abrupt UX. Older.

**L5. Unique-create races → 500**

Concurrent duplicate creates on catalog entities can raise `IntegrityError` not converted to `ValidationError` in drawer save paths. Rare. Older.

**L6. `seed_demo` can abort on missing catalog or bad change**

[`proformas/seed.py`](../../proformas/seed.py): `_catalog_item` / `_tubing` use bare `.get()` → `DoesNotExist` kills command; end-of-seed `change_proforma(cascais, …)` uncaught if Cascais is not changeable. Dev/CLI only; **WIP** touched seed for rejected demo.

---

## Explicit non-findings

- No infinite loops, busy-wait, or `fetch()` error paths in audited JS.
- Accept/reject/issue **business rules** raise `ValidationError` and are caught on the detail view.
- Empty-issue and unbounded discount from the 2026-09-07 06:17 review remain **fixed**.
- HQ site client reassignment 500 from the 07:50 review remains **fixed**.
- Confirm `<dialog>` itself does not deadlock the browser; risk is **uncaught JS after `preventDefault`**.
- `new-draft-form.js` disabling site until client is selected is intentional; server `NewDraftForm.clean` still validates client/site pairing.

---

## Bugbot comparison

Bugbot wrapper reported “found no bugs”; the [Bugbot](bf683718-8181-4a00-b359-733bc01cac74) transcript contains **2 medium** findings on the uncommitted diff. Independent review uses H/M/L numbering above.

| Bugbot | Severity | Verdict | Maps to |
| ------ | -------- | ------- | ------- |
| Confirm Yes silent no-op (`static/js/proforma-detail.js:29–41`) | medium | **Agree** | M1 |
| Cancelled rows lose detail actions (`templates/proformas/proforma_detail.html:51–91`) | medium | **Agree with caveat** — data migration gap, not worker crash; mitigated by fresh DB | M5 |

**Bugbot did not report (diff-only scope):** H1 PDF 500/hang; H2 create-draft ValidationError 500; M2 non-atomic issue; M3 catalog delete guards; M4 concurrency; L1–L6.

**Independent pass found; Bugbot missed:** All high findings and most medium/low items — expected because Bugbot reviews **introduced** diff bugs, not pre-existing crash paths.

**Net:** Two real medium issues in the WIP (confirm JS + cancelled status migration). Two high crash/hang paths remain in older code (PDF, create-draft). Several medium/low hardening items for a stable staff app under error and concurrency.

---

## Suggested remediations (not implemented here)

1. **H1:** Wrap `build_proforma_pdf` in view or service; catch WeasyPrint/OSError → message + redirect; document WeasyPrint system deps ([`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)).
2. **H2:** `except ValidationError` in `proforma_list` create path → re-open drawer with message; validate `Parameter.value` in `ParameterForm.clean`.
3. **M1:** Harden `proforma-detail.js` (try/catch, `requestSubmit` fallback, hidden `action` field).
4. **M2:** `@transaction.atomic` on `issue_proforma`.
5. **M3:** “In use on proforma line” guards on catalog deletes (mirror tubing/VAT).
6. **M5:** Data migration for `cancelled` → `issued` or explicit orphan-status UI.
7. **M4 / L1–L5:** Optional — row locks, activity log ordering, numbering cap, form flashes, `IntegrityError` → validation messages.

---

## Suggested tests (not implemented here)

- PDF view: mock `build_proforma_pdf` to raise `OSError` → redirect/message, not 500.
- List POST create with corrupt `default_upfront_discount_percent` parameter → drawer re-render with error, not 500.
- Confirm JS: integration or documented manual check — No cancels, Yes applies accept/reject.
- Partial issue: simulate failure mid snapshot loop → draft unchanged or fully rolled back.
- Migration: if any `cancelled` rows exist post-0015, assert detail shows quote/PDF or status normalized.

---

## Out of scope (not bugs)

- Production deploy, letterhead, VAT on quote math, contact fields on issued PDFs (see [`handoff.md`](../handoff.md)).
- Browser E2E (out of policy).
- Object-level permissions between staff users.
- WeasyPrint render quality / letterhead layout.

---

## Operator note

After pulling rejected-overlay WIP, reset local data if migrations or seed changed:

```bash
rm -f db.sqlite3
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
```

Hard-refresh issued proforma detail and exercise Mark accepted / Mark rejected confirm (No must cancel, Yes must apply).
