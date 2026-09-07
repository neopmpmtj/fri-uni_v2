# Project plan

## Purpose

Internal back office for one HVAC company (this slice of “universe”). Staff create a **proforma invoice** the client can read: equipment to be installed and what it will cost, including a discount if they pay upfront. It is not an official finance document.

Working for the first slice means: staff sign in with email, complete that quoting workflow in the browser, and persist the data. Back-end first, then front-end.

## Users

- **staff** — prepare drafts, issue/lock, download the PDF
- **admin** — users, catalog, parameters, and anything staff must not do
- **clients** — do not log in; they receive the document outside the app

## Apps

### Staff web app

- Purpose: the only product surface in the first slice. Browser app where staff quote HVAC installs.
- Users: staff and admin (email login, admin-provisioned accounts). Django admin is superuser plumbing only.
- Owns (writes): users, clients, sites, equipment catalog (brand → style → model), tubing length prices, parameters, proformas and lines, audit/activity
- Reads: everything it owns
- Out of bounds: client login, payments, official invoices, email send, stock, supplier POs, install calendar

### CLI (later slice)

- Purpose: after the website path works, one Django management command that creates a proforma in a single invocation (mandatory and optional flags).
- Users: staff/operators on the machine; not a public interface
- Owns (writes): the same proforma workflow as the web app (same database)
- Reads: same as the web app
- Out of bounds: a second product, a second store, or a substitute for the web MVP

## Sharing

One shared database. The staff web app is source of truth for all writes in the first slice. The CLI later writes the same tables. No separate stores.

## In scope

- Email login (`accounts.User`); admin creates accounts; no public signup
- Clients as domain records; a client has many sites
- Site aliases: four generic columns (`alias_1` … `alias_4`), not a list
- Catalog: brand → style → model (start with Mitsubishi, LG, Nippon; models such as 9k / 12k / 18k BTU)
- Proforma belongs to exactly one site (and that site’s client)
- One proforma may have many equipment lines (e.g. five AC units for a house)
- Draft, then issue: snapshot and lock all values; catalog price changes never flow into issued proformas
- Company default upfront-payment discount (parameters); overridable on the draft
- Extra tubing **per line**: boolean; if needed, a length from a priced list (some units on the same invoice need it, some do not)
- Extra labour field (handy now; history for a possible later install follow-up)
- Observations: one text field on the proforma, on top of tubing/labour/lines
- PDF generated on download; not stored as files in the first slice
- Soft delete; non-admin must not see admin functions

## Out of scope

- Official tax invoices, payments, accounting export, finance-system duplication
- Client portal, mobile app, public marketing site, shared API
- Email send / mailer / background worker in the first slice
- Stock, supplier purchase orders, install scheduling (labour/tubing on the quote are not a jobs module)
- Unlocking or revising a locked proforma (create a new one)
- Storing generated PDFs
- Client login identities

## Decisions

- One organization, one Django staff app, one database
- Admin is a role inside that app, not a second product
- Clients are records, not users
- Issued proforma is a frozen snapshot; corrections = new proforma
- Extra tubing is per line, not per invoice
- Four site aliases are four columns, not a joined list
- Web MVP first; CLI is the next slice in this project, same database
- Default upfront % lives in parameters; changing it does not rewrite locked proformas
- Creating the first draft does not need a reason; locked values are not edited

## Open questions

None. See update below.

## Update 2026-09-06

Closed all remaining wrinkles so later slices do not require disruptive schema patches on a working app.

### What changed

- **Indoor/outdoor:** two catalog items; one machine per line when quoting. Default indoor+outdoor matching is **deferred** (later migration adds `model_default_matches`; not in MVP schema).
- **Currency:** one company currency in `parameters` (`currency`, e.g. EUR). All money fields use it.
- **Extra labour:** one money field on the **proforma** header, not per line.
- **Tubing list:** catalog-wide `tubing_lengths` table, not per model. Which lengths exist is operational data.
- **Proforma number:** format `PF-YYYY-NNNN` (`YYYY` = create year, `NNNN` = 4-digit per-year sequence). Assigned on create. Unique among live rows.
- **Client contact:** `phone` and `email` on `clients` (optional). No `contacts` table.
- **Site location:** `street`, `postal_code`, `city` on `sites` (optional). Aliases stay four columns. No `addresses` table.
- **Snapshot at issue:** issued PDFs must not change if client, site, or catalog rows are renamed or repriced. Copy client name, phone, email, site aliases, notes, address, and frozen money onto the proforma; copy brand, style, kind, btu, and line money onto each line. Keep FKs for navigation.
- **Tubing unit:** `tubing_lengths.length` is in **metres**. Parameter `tubing_length_unit` = `m`.
- **Line total:** extra tubing charged per machine: `line_total = quantity × (unit_price + tubing_amount)`. Equipment subtotal = sum of `quantity × unit_price`. Tubing total = sum of `quantity × tubing_amount`. Discount applies to equipment only.
- **CLI contract (documented now, implemented later):** same tables. Mandatory: `--user` (email), `--site` (id), at least one `--line` (`model_id:qty` or `model_id:qty:tubing_length_id`). Optional: `--discount-percent`, `--extra-labour`, `--observations`, `--issue`. `created_by` = `--user`. Intended for LLM agent invocation, not manual terminal use.

### Apps added/removed

None.

### Decisions

- Snapshot-at-issue is required for PDF stability.
- `model_default_matches` is explicitly deferred, not an open question.

### Open questions still open

None.

## Update 2026-09-06 — implementation surfaces

Decisions for how the staff app is built (not schema). Implementation order is [`project-plan.md`](project-plan.md).

### What changed

- **Admin vs custom UI:** Django contrib admin for catalog, parameters, users, and audit. Custom templates for clients, sites, and the proforma draft → issue → on-screen quote → PDF workflow. Staff (`role=staff`) must not use `/admin/`. Django admin UI stays English.
- **Login:** email + password only. Google OAuth fields on `accounts.User` stay unused.
- **i18n:** two languages, one app (`en` | `pt`). Copy CentCompras / [warehouse_V2](https://github.com/neopmpmtj/warehouse_V2) [`docs/i18n-pattern.md`](https://github.com/neopmpmtj/warehouse_V2/blob/main/docs/i18n-pattern.md): English fallback in HTML, vanilla JS dictionaries, `data-i18n*` attributes, preference in `localStorage` (`fu-lang`). No Django gettext `.po` files, no `LocaleMiddleware` UI switching, no `User.language` column. Dark/light theme from warehouse is not in this slice.
- **PDF / visualization:** MVP shows the issued quote on screen. Also generate a real PDF on download (`build_proforma_pdf` → bytes) so a later email feature can attach it. Do not store PDF files. Do not send email in this slice (Gmail vs local mail is a future enhancement).
- **PDF language:** WeasyPrint cannot read `localStorage`. Language JS also writes a `fu-lang` cookie; quote HTML/PDF uses a small server-side EN/PT dict. Switch the UI to English before download for a UK client.
- **Seed:** optional idempotent `seed_catalog` management command (demo brands/models/tubing/parameters). Not run automatically in production.
- **CLI:** last implementation phase; same services as the web; flag contract unchanged in data-points.

### Apps added/removed

None.

### Decisions

- UI translation is client-side JS (warehouse_V2), not gettext.
- Email send is out of scope; PDF bytes are the attachment seam.
- Catalog maintenance is Django admin; quoting is custom UI.

### Open questions still open

None.

## Update 2026-09-06 — staff UI chrome

Visual/chrome spec: [`front-end-project-plan.md`](front-end-project-plan.md). Copied from warehouse_V2; not a second product.

### What changed

- **Two layouts:** dashboard (card grid) and work page (topbar + table). Language `<select>` **only on the dashboard**; work pages read `fu-lang` and do not offer a switcher.
- **Gear (Settings):** top right on dashboard and work pages. Shows signed-in email and Sign out. No Help manuals, no “sign out other devices”, no dark theme.
- **List + drawer:** clients, sites, and proforma **lines** create/edit in a right-hand drawer (warehouse Items pattern). Sites stay a first-class list page (not nested under clients like warehouse Suppliers).
- **Proforma:** work page with header fields on the page and a lines table; not a Django form wizard.
- **Catalog console:** do not copy warehouse manager catalog; Django admin remains.

### Apps added/removed

None.

### Decisions

- Server-rendered tables + JS drawer; no warehouse `/api/manage/` clone for MVP.
- To issue an English PDF, staff switch language on the dashboard first, then download.

### Open questions still open

None.

## Update 2026-09-06 — Django domain app name

The staff domain app is **`proformas`**, not `office`. `accounts` remains the User/login app. Implementation order is unchanged ([`project-plan.md`](project-plan.md)).

### What changed

- **App package:** `proformas` (`INSTALLED_APPS`, services, models, admin, management commands, staff templates).

### Apps added/removed

- Named: `proformas`.
- Rejected name: `office`.

### Decisions

- Django-style plural of the main entity.

### Open questions still open

None.

## Update 2026-09-06 — Daikin catalog seed

Demo `seed_catalog` now includes **Daikin** in addition to Mitsubishi, LG, and Nippon.

### What changed

- **Daikin styles** come from the Portugal air-to-air heat-pump page (bombas de calor ar-ar): Sensira, Comfora, Perfera, Perfera Floor, Stylish, Emura, Ururu Sarara. Each style still gets indoor/outdoor 9k/12k/18k BTU with round demo prices.
- **Not seeded as styles:** Multi / Multi+ / pair (system layouts, not named indoor ranges). Ducted/concealed ceiling is listed as a form factor on that page but has no named consumer series there, so it is omitted until a real range name is supplied.
- Prices remain placeholders, not live Daikin list prices.

### Apps added/removed

None.

### Decisions

- Seed styles follow Daikin PT named ranges, not generic “Split”.

### Open questions still open

None.

## Update 2026-09-06 — Demo seed and manager delete

Local/demo `seed_demo` fills a clickable suite. `seed_catalog` stays catalog-only.

### What changed

- **Users:** `proforma-admin@fribila.dev` (`admin`, Django admin, may soft-delete) and `proforma-manager@fribila.dev` (`staff`, quoting UI, may not delete). Shared demo password documented in README. Manager maps to existing `staff` role; no third role.
- **Delete:** only `admin` may soft-delete clients and sites. Staff/manager do not see Delete in the drawer; POST delete is 403. Removing a line from a **draft** quote is still allowed (editing, not retiring a client/site). Cancel is not delete.
- **Demo records:** three clients, five sites, five proformas (two issued, two drafts, one cancelled). Idempotent. Not for production.

### Apps added/removed

None.

### Decisions

- Demo manager is `role=staff`. Only admin deletes clients/sites.

### Open questions still open

None.

## Update 2026-09-06 — catalog families, items, setup cards

Catalog is a staff workspace, not Django admin. Family is a product category; styles become sub-families; models become items.

### What changed

- **Family:** Air conditioners (default), Underfloor heating, Domestic hot water. Not a Daikin range name.
- **Sub-family:** former style (Sensira, Split, …) belongs to a family, not a brand. The same sub-family can be used by any manufacturer.
- **Item:** former catalog model. `brand` (manufacturer) + `sub_family` + `internal_code` (uppercase, uniqueness compared case-insensitive) + `kind` + `btu` + optional `max_volume_m3` (e.g. 9000 BTU indoor until 20 m³) + `list_price` (sales price).
- **Defaults:** `is_default` on family, sub-family, brand, and item. New proforma lines pre-select the cascade (AC first).
- **Surfaces:** dashboard **daily** cards (Clients, Sites, Proformas, Items) and **setup** cards (Families, Sub-families, Manufacturers). Manufacturers hold the sales pricelist. Items page has no price field. Django admin is not the catalog UI.
- **CLI:** `--line` is `item_id:qty` (optional tubing id).
- **Deferred:** volume-based auto-pick; indoor/outdoor `model_default_matches`. Field `max_volume_m3` is stored only.

### Apps added/removed

None.

### Decisions

- Extra catalog layer vs warehouse is manufacturer on the item.
- Extra layer vs the previous HVAC schema is family (product category).
- Sales price is edited only on the manufacturer pricelist, with a reason.

### Open questions still open

None.

## Update 2026-09-06 — VAT on items + setup from dashboard

Warehouse VAT lookup copied onto catalog items. Remaining operational config moves off Django admin onto dashboard Setup cards.

### What changed

- **VAT rates:** lookup table (`code`, `label`, `rate` as 0–1, `is_default`). Portugal IVA seed: 23% (default), 13%, 6%, Exempt. Required FK on each item. Staff enter percent; stored as a fraction.
- **Items:** identity includes VAT (drawer + list column). Sales price still only on the manufacturer pricelist. Quoting/PDF do **not** apply VAT yet.
- **Surfaces:** dashboard Setup cards now also include VAT rates, Parameters, and Tubing lengths. Django admin remains users and audit only.
- **Parameters:** staff edit known keys only; no create/delete. Changing default discount does not rewrite issued proformas.
- **Tubing lengths:** staff list+drawer; price change still needs a reason.

### Apps added/removed

None.

### Decisions

- Copy warehouse VAT *system*, not Mozambique 16% rates.
- Catalog IVA is not an official tax invoice.

### Open questions still open

None.

## Update 2026-09-06 — optional manufacturer on sub-family

Sub-families may optionally point at one manufacturer so New item can lock that field.

### What changed

- **Sub-family:** optional `brand`. Named Daikin ranges (Perfera, Sensira, …) are seeded with Daikin. Split stays shared (no manufacturer).
- **New/Edit item:** choosing a sub-family with a manufacturer fills Manufacturer and disables the control. Split still requires staff to pick a manufacturer.
- **Line drawer:** same lock when the sub-family has a manufacturer.
- Item still has its own required manufacturer FK.

### Apps added/removed

None.

### Decisions

- Manufacturer on sub-family is optional, not required. Do not split Split into per-brand rows.

### Open questions still open

None.

## Update 2026-09-06 — power ratings lookup

Replace raw BTU on items with a `powers` setup lookup (`power` + `unit`).

### What changed

- **Powers:** setup page + dashboard card. Seed: 9000 / 12000 / 18000 BTU.
- **Items:** required FK to `powers`; New item uses a dropdown.
- **Issued lines:** snapshot `power_value` + `power_unit` instead of `btu`.

### Apps added/removed

None.

### Decisions

- kW and other units can be added later via the same lookup table.

### Open questions still open

None.

## Update 2026-09-07 — client billing identity and HQ site

### What changed

- **Clients:** `kind` (`person` | `company`), required unique NIF (`tax_number`), billing address (`street`, `postal_code` `NNNN-NNN`, `city`, `country_code` default `PT`). Still optional `phone` / `email`.
- **Sites:** `is_headquarters` flag; `street`, `postal_code`, `city` required (GPS-ready install address). At most one live HQ per client.
- **Create client:** auto-creates HQ site (`alias_1` = client name, billing address copied once; later edits independent).
- **Delete:** admin soft-deletes client only when no live site has proformas (sites deleted with client). HQ site cannot be deleted alone.
- **Issue snapshot:** proforma stores client billing fields (kind, NIF, address, country) in addition to name/phone/email.

### Apps added/removed

None.

### Decisions

- Billing on client; install/GPS on site. No `alias_0`; HQ is a boolean flag.
- Maps/nav UI deferred to next sites slice; address validation is in place now.

### Open questions still open

None.

## Update 2026-09-07

### Proforma acceptance (not a fourth status)

- Document life stays `draft` → `issued` → `cancelled`; money frozen after issue.
- **Went through** is `proformas.accepted_at` (datetime, null = not yet). Staff mark an issued quote when the client accepts or the job is done; they can clear the mark. Cancel clears `accepted_at`.
- No jobs/install table; no stats or graphs in this slice — the column exists so win-rate reporting can be added later.

### Proforma Change (supersede links)

- **Change** on issued (not accepted, not superseded): new draft on same site; `replaces` on draft, `superseded_by` on source; source stays issued with frozen PDF.
- List **Actions**: Edit (draft), Change (issued eligible), none (cancelled / accepted / superseded).

## Update 2026-09-07 — rejected overlay (no cancelled status)

### What changed

- Dropped `cancelled` as a document status. Life is `draft` → `issued` only; money still frozen after issue.
- **Rejected** is `proformas.rejected_at` (datetime, null = not rejected), sibling to `accepted_at`. Staff mark an issued quote when the client declined; they can clear the mark. Mutually exclusive with accepted (clear one before marking the other).
- **Change** is blocked when accepted or rejected (or already superseded).
- Demo Ala Norte quote is issued + rejected. Fresh DB: migrate then `seed_demo`.

### Apps added/removed

None.

### Decisions

- Outcomes (accepted / rejected) are not filter statuses. List filter is `draft` / `issued`; pills distinguish outcomes.
- No auto-clear: switching accepted ↔ rejected requires clearing first.

### Open questions still open

None.

## Update 2026-09-07 — list Accept / Reject / Clear

### What changed

- Proforma **list** Actions now mark outcomes without opening the issued work page (so staff do not have to **Change**, which supersedes immediately).
- `issued` (not accepted, not rejected, not superseded): **Change** on the left; thumbs-up / thumbs-down icons (green/red, hover label) for accept/reject.
- `issued` + accepted or `issued` + rejected: only **Clear accepted** or **Clear rejected**.
- Draft stays **Edit**. Superseded stays no action. Detail page actions are unchanged.

### Apps added/removed

None.

### Decisions

- Accept/reject from the list uses the same services and confirm dialog as the issued work page.
- Clear from the list does not use a confirm dialog (same as detail).

### Open questions still open

None.

## Update 2026-09-07 — extra tubing metres on the proforma

### What changed

- Line drawer: tubing length is hidden until Extra tubing is checked; then the shortest catalog length is selected (no blank dashes).
- New header field `extra_tubing_metres` = sum of `quantity × length` on extra-tubing lines. Frozen at issue. Shown on the work page and issued quote/PDF next to money Tubing when non-zero.
- Demo Cascais quote has two extra-tubing runs (5 m + 3 m → 8 m).

### Apps added/removed

None.

### Decisions

- Metres are stored on the proforma header (same write path as money totals), not derived in templates.
- Do not hardcode 3 m; default is the shortest live `tubing_lengths` row.

### Open questions still open

None.
