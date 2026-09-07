# Data points

Conceptual model only. Not SQL, not ORM, not seeds.

## Conventions

Always-on columns on every entity table: `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at` (null = live), `deleted_by`.

Unique keys apply to live rows only.

Audit defaults: `change_logs` (field-level), `activity_logs` (actions). Per-entity history and entity-specific activity only where listed below.

`created_by` / `updated_by` may be null for `actor_type = system`. The LLM/CLI path is not anonymous: the command takes a **mandatory user**; that user is `created_by` and `actor_type = user`.

Draft proformas may be edited. **Issued** proformas are frozen in place: no value updates on that row. **Change** creates a new draft copy and links the old issued row via `superseded_by` / `replaces` (see `proformas`). **Accepted** and **rejected** are outcomes on an issued row (`accepted_at` / `rejected_at`), not extra document statuses. Soft-delete hides mistakes from live lists.

At **issue**, snapshot client, site, and catalog display fields onto the proforma and lines so issued PDFs do not change if live rows are renamed or repriced. FKs remain for navigation; PDF and locked values read the snapshots.

## Apps this model serves

Shared core in one database.

- Staff web app (MVP) writes all tables below. Catalog identity and setup (families, sub-families, manufacturers, items, VAT rates, parameters, tubing lengths) are staff pages. Django admin is not the catalog UI (users and audit only).
- **CLI** (later slice) writes the same proforma workflow so an LLM agent can create a proforma in one shot. Not a separate store.

### CLI contract (later slice; no extra schema)

Mandatory flags:

- `--user` — staff email; becomes `created_by`
- `--site` — site id
- at least one `--line` — `item_id:qty` or `item_id:qty:tubing_length_id`

Optional flags:

- `--discount-percent`
- `--extra-labour`
- `--observations`
- `--issue` — issue immediately after create

Same validation and snapshot rules as the web app. Intended for LLM agent invocation, not manual terminal use.

## Tables

### users

- Purpose: login identities for staff and admin
- Written by (apps): staff web app (admin)
- Fields (plus always-on):
  - `email` — text, required
  - `first_name` — text, optional
  - `last_name` — text, optional
  - `role` — enum `staff` | `admin`, required
  - `is_active` — boolean, required
- Uniqueness: live `email`
- Notes: maps to existing `accounts.User` (email login). Admin-provisioned; no public signup. Clients are not users. Demo manager (`staff`) may create and edit clients, sites, catalog (families, sub-families, manufacturers, items, VAT rates, sales prices, tubing lengths), parameters, and proformas, and may issue / mark accepted or rejected; only `admin` may soft-delete clients, sites, and catalog rows. Parameters have no delete.
- Extra history table: no
- Extra activity table: no

### change_logs

- Purpose: field-level old/new
- Fields: entity type, entity id, field, old value, new value, actor, actor type (`user` | `system`), time, reason (required only for reason-required fields)
- Reason-required fields elsewhere:
  - `items.list_price`
  - `tubing_lengths.price`
- Notes: issued proforma money fields are not edited, so they are not reason-required (the edit is forbidden). Creating a draft does not need a reason.

### activity_logs

- Purpose: actions that are not a single field write
- Fields: actor, actor type, action, object type, object id, time, details
- Typical actions: issue proforma, download PDF, create proforma via agent/CLI

### parameters

- Purpose: settings editable without a deploy
- Written by (apps): staff web app (setup page, not Django admin)
- Fields (plus always-on):
  - `key` — text, required
  - `value` — text, required
- Known keys:
  - `currency` — company currency (e.g. EUR); all money fields use this
  - `default_upfront_discount_percent` — number as text; default for new drafts; changing it does not rewrite locked proformas
  - `tubing_length_unit` — `m` (metres); documents the unit for `tubing_lengths.length`
- Uniqueness: live `key`
- Reason-required: no
- Extra history table: no
- Extra activity table: no
- Notes: staff may edit `value` on known keys only. No create or delete of parameter rows from the setup page.

### countries

- Purpose: dial-code lookup for phone national numbers (billing address `country_code` on clients stays a separate field for now)
- Written by (apps): migration seed (staff web app reads only for now)
- Fields:
  - `code` — text, required (ISO 3166-1 alpha-2, primary key; e.g. `PT`)
  - `name` — text, required
  - `dial_code` — text, required (digits only, no `+`; e.g. `351`)
  - `phone_national_digits` — integer, required (expected national number length for that country)
- Seed set (initial): Portugal (`PT`, 9), Spain (`ES`, 9), France (`FR`, 9), Germany (`DE`, 10), Belgium (`BE`, 9)
- Uniqueness: `code`
- Notes: UI currently defaults phone country to Portugal and disables the selector; validation uses the row’s `phone_national_digits`.

### contact_positions

- Purpose: contact role / job title for client and site contacts (UI label: position / cargo)
- Written by (apps): staff web app (setup page)
- Fields (plus always-on):
  - `name` — text, required (e.g. CEO, Manager)
- Uniqueness: live `name` (case-insensitive)
- Seed set (initial): CEO, CFO, Manager, Director, Other
- Notes: optional on clients and sites; referenced by fk from `clients.contact_position` and `sites.contact_position`

### clients

- Purpose: customer for invoicing (private person or company)
- Written by (apps): staff web app
- Fields (plus always-on):
  - `kind` — enum `person` | `company`, required
  - `name` — text, required (invoice name)
  - `phone_country` — fk → `countries`, required (default `PT`; UI disabled for now)
  - `phone` — text, required (national digits only, 9 for Portugal; no `+` prefix stored)
  - `email` — text, required
  - `contact_name` — text, optional
  - `contact_position` — fk → `contact_positions`, optional
  - `country_code` — text, required (billing address country; default `PT`)
  - `tax_number` — text, optional (Portuguese NIF, 9 digits when set, live unique among non-blank)
  - `street` — text, optional (billing / legal address)
  - `postal_code` — text, optional (`NNNN-NNN` when set)
  - `city` — text, optional
- Relationships: has many `sites`; on create the app auto-creates one headquarters site (`is_headquarters`, `alias_1` = client name, billing address copied once)
- Uniqueness: live `name`; live non-blank `tax_number`
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes: not a login. No contacts table, no separate addresses table. Billing address lives on the client; install/GPS address lives on each site.

### sites

- Purpose: a work / install location of a client (GPS navigation uses site address)
- Written by (apps): staff web app
- Fields (plus always-on):
  - `client` — fk → `clients`, required
  - `is_headquarters` — boolean, required, default false; at most one live HQ per client
  - `alias_1` — text, required
  - `alias_2` — text, optional
  - `alias_3` — text, optional
  - `alias_4` — text, optional
  - `street` — text, required
  - `postal_code` — text, required (`NNNN-NNN`)
  - `city` — text, required
  - `phone_country` — fk → `countries`, required (default `PT`; UI disabled for now)
  - `phone` — text, required (national digits only, 9 for Portugal)
  - `email` — text, required
  - `contact_name` — text, optional
  - `contact_position` — fk → `contact_positions`, optional
  - `notes` — text, optional
- Relationships: belongs to one `client`; has many `proformas`
- Uniqueness: at most one live `is_headquarters` per client
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no

### brands

- Purpose: manufacturer (start: Mitsubishi, LG, Nippon, Daikin). UI label: manufacturer.
- Written by (apps): staff web app (setup page, not Django admin)
- Fields (plus always-on):
  - `name` — text, required
  - `is_default` — boolean, required, default false
- Relationships: has many `items`; may own named `sub_families`; owns the **sales pricelist** (each item’s `list_price`)
- Uniqueness: live `name`; at most one live row with `is_default` true
- Reason-required fields: none (sales prices live on `items`)
- Extra history table: no
- Extra activity table: no

### families

- Purpose: product category (season / job type), not a manufacturer range. Start: Air conditioners (default), Underfloor heating, Domestic hot water.
- Written by (apps): staff web app (setup page)
- Fields (plus always-on):
  - `name` — text, required
  - `is_default` — boolean, required, default false
- Relationships: has many `sub_families`
- Uniqueness: live `name` (case-insensitive); at most one live row with `is_default` true
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes: default family is Air conditioners (most sold). New proforma lines pre-select it.

### sub_families

- Purpose: named range under a family (e.g. Sensira, Split). May optionally belong to one manufacturer (e.g. Perfera → Daikin). Shared ranges such as Split leave manufacturer blank so any brand can use them.
- Written by (apps): staff web app (setup page)
- Fields (plus always-on):
  - `family` — fk → `families`, required
  - `brand` — fk → `brands`, optional (null = shared across manufacturers)
  - `name` — text, required
  - `is_default` — boolean, required, default false
- Relationships: belongs to one `family`; optionally one `brand`; has many `items`
- Uniqueness: live `name` per `family` (name case-insensitive); at most one live `is_default` true per family
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes: if `brand` is set, New/Edit item fills manufacturer from the sub-family and the control is visible but inactive. If blank, staff pick manufacturer on the item. Item still has its own required `brand` FK.

### powers

- Purpose: standard catalog power ratings (AC BTU today; kW and other units later)
- Written by (apps): staff web app (setup page)
- Fields (plus always-on):
  - `power` — integer, required (e.g. `9000`; kW values such as `12` later)
  - `unit` — text, required (e.g. `BTU`, `kW`; stored trimmed)
- Relationships: has many `items`
- Uniqueness: live (`power`, `unit`) with unit compared case-insensitive
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes: seed starts with 9000 / 12000 / 18000 BTU. New item picks a row from this lookup instead of typing a number.

### vat_rates

- Purpose: catalog IVA lookup (warehouse-style). Staff pick a rate on each item. Not an official tax invoice table.
- Written by (apps): staff web app (setup page)
- Fields (plus always-on):
  - `code` — text, required (stored uppercase, e.g. `VAT23`)
  - `label` — text, required (e.g. `23%`)
  - `rate` — number, required, 0–1 inclusive (fraction; staff enter percent `23`, stored `0.2300`)
  - `is_default` — boolean, required, default false
- Relationships: has many `items`
- Uniqueness: live `code` (case-insensitive); at most one live row with `is_default` true
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes: start with Portugal IVA: 23% (default), 13%, 6%, Exempt (0%). New items pre-select the default rate. Quoting does not apply VAT yet; the FK is stored so a later slice can snapshot it onto lines. Do not confuse with official invoice / payment / tax tables (still rejected).

### items

- Purpose: one catalog machine (indoor or outdoor); one machine per proforma line
- Written by (apps): staff web app (Items page for identity; manufacturer pricelist for `list_price`)
- Fields (plus always-on):
  - `sub_family` — fk → `sub_families`, required
  - `brand` — fk → `brands`, required
  - `vat_rate` — fk → `vat_rates`, required
  - `internal_code` — text, required (stored uppercase)
  - `kind` — enum `indoor` | `outdoor`, required
  - `power` — fk → `powers`, required
  - `max_volume_m3` — number, optional (room volume this unit is suitable for, up to this many cubic metres; e.g. 9000 BTU indoor → 20). Null = unknown / not applicable. For later auto-matching; not used in quoting yet.
  - `list_price` — money, required, default 0 (current **sales** price; edited only on the manufacturer pricelist)
  - `is_default` — boolean, required, default false
- Relationships: belongs to one `sub_family` (and thus a family), one `brand`, one `vat_rate`, and one `power`; referenced by `proforma_lines`
- Uniqueness: live `internal_code` (compared case-insensitive); live (`sub_family`, `brand`, `kind`, `power`) — one catalog machine per combo (family is implied by `sub_family`); at most one live `is_default` true per (`sub_family`, `brand`)
- Reason-required fields: `list_price`
- Extra history table: no (locked lines hold the snapshot; no catalog price-history screen)
- Extra activity table: no
- Notes: default indoor+outdoor matching is deferred (`model_default_matches` in a later slice). Volume-based auto-pick is deferred (field stored only). MVP quoting picks each machine on its own line. New items start at sales price 0 until priced on the manufacturer page. VAT is identity on the item; line totals do not include VAT yet. When the parent sub-family has a manufacturer, the item’s `brand` is copied from that sub-family and cannot be chosen independently.

### tubing_lengths

- Purpose: priced extra-tubing options when indoor and outdoor are far apart
- Written by (apps): staff web app (setup page, not Django admin)
- Fields (plus always-on):
  - `length` — number, required (metres; see `parameters.tubing_length_unit`)
  - `price` — money, required
- Relationships: referenced by `proforma_lines` when extra tubing is needed
- Uniqueness: live `length`
- Reason-required fields: `price`
- Extra history table: no
- Extra activity table: no
- Notes: catalog-wide list, not per item. Which lengths exist is operational data.

### proformas

- Purpose: client-facing quote for **one site**; not an official finance document
- Written by (apps): staff web app; later CLI (mandatory `--user`)
- Fields (plus always-on):
  - `site` — fk → `sites`, required (client is that site’s client)
  - `number` — text, required; format `PF-YYYY-NNNN` (`YYYY` = create year, `NNNN` = 4-digit per-year sequence); assigned on create
  - `status` — enum `draft` | `issued`, required
  - `accepted_at` — datetime, optional; null = not accepted yet. Set only on `issued` rows when staff mark that the quote went through (client accepted and/or install done). Cleared when staff unmark. Mutually exclusive with `rejected_at`: staff must clear one before marking the other. Not a money field; freeze rules unchanged.
  - `rejected_at` — datetime, optional; null = not rejected yet. Set only on `issued` rows when staff mark that the client declined (or the deal died). Cleared when staff unmark. Mutually exclusive with `accepted_at`. Not a money field; freeze rules unchanged. Blocks **Change**, same as accepted.
  - `superseded_by` — fk → `proformas`, optional; set on an **issued** row when staff **Change** it — points to the new draft that replaces it. Null = still the active issued version for that revision chain.
  - `replaces` — fk → `proformas`, optional; set on a **draft** created by **Change** — points back to the source issued row. Null on normal new drafts.
  - `upfront_discount_percent` — number, required (copied from parameters on create; overridable while draft)
  - `extra_labour` — money, required, default 0
  - `observations` — text, optional
  - `equipment_subtotal` — money, optional until issue, then required frozen
  - `tubing_total` — money, optional until issue, then required frozen
  - `extra_tubing_metres` — number (metres), optional until issue, then required frozen; sum over extra-tubing lines of `quantity × length`. Not money. `tubing_total` stays the money sum.
  - `discount_amount` — money, optional until issue, then required frozen (equipment only)
  - `grand_total` — money, optional until issue, then required frozen
  - Snapshot fields (filled at issue; read by PDF):
    - `client_name` — text
    - `client_kind` — enum `person` | `company`
    - `client_tax_number` — text (NIF)
    - `client_street` — text
    - `client_postal_code` — text
    - `client_city` — text
    - `client_country_code` — text
    - `client_phone` — text, optional
    - `client_email` — text, optional
    - `site_alias_1` … `site_alias_4` — text
    - `site_street` — text, optional
    - `site_postal_code` — text, optional
    - `site_city` — text, optional
    - `site_notes` — text, optional
- Relationships: belongs to one `site`; has many `proforma_lines`
- Uniqueness: live `number`
- Reason-required fields: none (issued rows are not edited)
- Extra history table: no
- Extra activity table: no
- Notes:
  - Only `draft` is editable. Explicit **issue** snapshots totals, client/site display fields, and locks. PDF is for issued documents. Draft preview PDF (if added later) must not lock.
  - Upfront discount applies to **equipment line totals only**, not tubing, not extra labour.
  - `extra_labour` is on the header, not on lines.
  - Soft-delete still hides mistakes from live lists.
  - `accepted_at` and `rejected_at` are separate from `status`: an issued proforma stays `issued` with or without a mark. Later reporting can use `accepted_at IS NOT NULL` / `rejected_at IS NOT NULL` and group by those timestamps. Exclude superseded issued rows from active stats (`superseded_by` is null).
  - **Change** (issued, not accepted, not rejected, not superseded): copy to new draft on same site; set `replaces` on draft and `superseded_by` on source; source stays `issued` with frozen snapshots/PDF.
  - Totals at issue:
    - `equipment_subtotal` = sum over lines of `quantity × unit_price`
    - `tubing_total` = sum over lines of `quantity × tubing_amount`
    - `extra_tubing_metres` = sum over extra-tubing lines of `quantity × length`
    - `discount_amount` = `equipment_subtotal × upfront_discount_percent / 100`
    - `grand_total` = `equipment_subtotal - discount_amount + tubing_total + extra_labour`

### proforma_lines

- Purpose: one machine on a proforma (e.g. five AC units for a house = five lines)
- Written by (apps): staff web app; later CLI
- Fields (plus always-on):
  - `proforma` — fk → `proformas`, required
  - `item` — fk → `items`, required
  - `quantity` — number, required, default 1
  - `extra_tubing` — boolean, required, default false
  - `tubing_length` — fk → `tubing_lengths`, optional (required when `extra_tubing` is true)
  - `unit_price` — money, required (snapshot of item sales price at save/issue)
  - `tubing_amount` — money, required, default 0 (snapshot of tubing length price; 0 when no extra tubing)
  - `line_total` — money, required
  - Snapshot fields (filled at issue; read by PDF):
    - `brand_name` — text
    - `family_name` — text
    - `sub_family_name` — text
    - `internal_code` — text
    - `kind` — enum `indoor` | `outdoor`
    - `power_value` — integer (snapshot of catalog power at issue)
    - `power_unit` — text (snapshot of catalog unit at issue)
    - `tubing_length_value` — number, optional (metres; 0 or null when no extra tubing)
- Relationships: belongs to one `proforma`; points at one `item`; optional `tubing_length`
- Uniqueness: none (same item may appear on more than one line)
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes:
  - Extra tubing is **per line** and charged **per machine**: `line_total = quantity × (unit_price + tubing_amount)`.
  - On one invoice, some lines may need extra tubing and some may not.
  - After issue, money and snapshot fields do not change if catalog prices or names change.

## Rejected

- `contacts`, `addresses` tables
- Stock, supplier POs, jobs / install calendar tables
- Stored PDF / file table
- `model_default_matches` in MVP (deferred to later slice; explicit migration when quoting auto-pair is built)
- `item_price_history`, `proforma_activities`, or any collapse of the four audit kinds into one “audit” table
- Client-login / portal tables
- Mailer / worker / job-queue tables in this slice
- Per-app copies of shared entities
- Official invoice / payment / tax tables (`vat_rates` on catalog items is not this)
- Unlock or revision-chain tables for locked proformas

## Open questions

None.
