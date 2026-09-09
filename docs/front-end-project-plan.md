# Front-end project plan

How the staff UI should look and behave. Product scope: [`preliminary_project-plan.md`](preliminary_project-plan.md). Schema: [`data-points.md`](data-points.md). Build order: [`project-plan.md`](project-plan.md).

Copy chrome from [warehouse_V2](https://github.com/neopmpmtj/warehouse_V2) (CentCompras). i18n mechanics: warehouse [`docs/i18n-pattern.md`](https://github.com/neopmpmtj/warehouse_V2/blob/main/docs/i18n-pattern.md). **Do not clone warehouse product screens** (items catalog API, Company Voice, branches).

A later agent implements UI only after the matching implementation phase. Checkboxes below are the visual backlog; tick them on session-handoff when that chrome exists.

## How to use

1. Read this file **before any staff HTML/CSS/JS**.
2. Two layouts only: **dashboard** and **work page**. Do not invent a third shell.
3. **Server-rendered tables + JS drawer.** Do not add a `/api/manage/` clone unless a later phase truly needs it. Warehouse items load rows via JSON APIs; fri-uni does not.
4. Catalog identity (items) is a **staff work page**. Families, sub-families, manufacturers, VAT rates, parameters, company, and tubing lengths are **setup pages** opened from dashboard cards. Django contrib admin is users and audit only.

## Visual tokens (light only)

From warehouse `products/static/products/css/console.css`. No dark theme.

| Token | Value |
| ----- | ----- |
| `--bg` | `#f4f6f8` |
| `--surface` | `#ffffff` |
| `--surface-2` | `#eef2f5` |
| `--text` | `#1c2430` |
| `--muted` | `#5b6776` |
| `--border` | `#d5dde6` |
| `--accent` | `#0f766e` |
| `--accent-text` | `#ffffff` |
| `--shadow` | `0 12px 32px rgba(16, 24, 40, 0.12)` |
| Font | `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` |
| Radius | 6px controls, 8px cards/popover/drawer |

Primary buttons: accent fill, white text. Ghost/default: surface, 1px border. Body background `--bg`.

---

## Chrome rules (always)

### Two layouts

Warehouse does not use one `base.html` for everything. Match that:

- **Dashboard layout** — language + gear in a top `page-account-bar`; main is a card grid. Reference: warehouse `products/templates/products/dashboard.html`.
- **Work layout** — `header.topbar` + `main.page`. Reference: warehouse `products/templates/products/item_console.html`.

Shared includes: gear popover, i18n JS, CSS variables. Work pages include topbar nav. Dashboard does **not** include the work topbar nav.

### Dashboard layout

Top bar (`page-account-bar`), flex, space-between / end-aligned:

- Left (or start): language `<select>` (English / Português). **This is the only language control in the app.** Same idea as warehouse `preferences_bar.html` (`#pref-language`). No theme button.
- Right: gear Settings (see below).

Main (`dash-main`, max-width ~72rem):

- App title (e.g. company / “Proformas”).
- Two card groups:
  - **Daily** (`card-grid`): Clients, Sites, Proformas, Items.
  - **Setup** (`card-grid`, heading “Setup”): Families, Sub-families, Manufacturers, VAT rates, Powers, Parameters, Company, Tubing lengths, Positions.
- Do **not** put a Catalog (Django admin) card on the dashboard.
- Cards: white surface, 8px radius, shadow; hover accent border. Title + one-line description. `data-i18n` on strings.

Language change writes `fu-lang` to **localStorage and cookie**, sets `document.documentElement.lang` to `en` or `pt-PT`, dispatches `fu-lang-changed` (warehouse uses `cc-lang-changed`). Work pages never show a language select; they only read the stored value.

To produce an English PDF for a UK client, staff return to the dashboard, switch to English, then open the issued quote / download.

### Work layout

`header.topbar` (surface, bottom border):

1. **Eyebrow** + page **`h1`** (warehouse `console_eyebrow.html` + title). Eyebrow can be the app name; `h1` is the screen name (Clients, Sites, …).
2. **Nav** — Home, Clients, Sites, Proformas, Items. Active link styled (`is-active`). Home goes to the dashboard. **No language select here.** Setup pages are **not** in the topbar; they are dashboard setup cards.
3. **Actions (right)** — page-specific buttons if needed, then the **gear**. No warehouse “Master data” cluster. No Help `?`.

`main.page`: toolbar (filters + primary action), optional banner, `.table-wrap` > `table.grid`, optional pagination.

Early `<head>` script (anti-flash): read `fu-lang`, set `lang` on `<html>` before CSS paints. Default `en`.

### Gear / Settings (top right)

Warehouse calls this Settings (gear SVG), not “Definitions”. Copy the popover, not the extra warehouse actions.

- Button `#settings-toggle` (ghost, gear icon), `aria-haspopup`, `aria-controls="settings-popover"`.
- Popover: title “Settings”; **Sign out** (POST `{% url 'logout' %}`) in the head; line “Signed in as **{{ user.email }}**”.
- Click-outside and Escape close it; `hidden` when closed.
- **Skip:** Help launcher, user manuals, “Sign out other devices”, theme.

Reference: warehouse `products/templates/products/includes/account_settings.html`, `settings_menu.css`, `console_settings_menu.js` (menu open/close only).

### Drawer

Right-hand panel. Create and edit use the **same** drawer.

- `#drawer-backdrop.backdrop` + `#drawer.drawer`, both `hidden` when closed.
- Head: `h2` title + Close.
- Body: form, stacked labels (`span` + input/select). Actions row at the bottom (Save / soft-delete when editing).
- Close on Close button, backdrop click, Escape.
- Does not navigate to a separate form URL as the primary UX (query `?id=` or POST to the list URL is fine).

Reference: warehouse `item_console.html` (`#drawer`, `#drawer-backdrop`) and `.drawer*` rules in `console.css`.

### i18n

- English fallback text in HTML.
- `data-i18n`, `data-i18n-placeholder`, `data-i18n-aria`, `data-i18n-title` (and `data-i18n-col` on sortable headers if used).
- Shared `static/js/i18n.js`: `normalizeLang`, `t()`, `applyStaticI18n()`, `safeGet`/`safeSet`. `pt*` → `pt`; dicts may key `"pt-PT"` with a `pt` alias.
- No `.po` files, no `{% trans %}`, no `User.language`.

---

## Screens

### Login

Centered card on `--bg`. Email + password. English fallback + i18n. After login → dashboard.

### Dashboard

Only place to set language. Daily cards + Setup cards as above. Implementation: Phase 1, catalog cards in the catalog slice.

### Items (list + drawer)

Daily catalog. Light: identity only, **no sales price field**.

- Toolbar: search, filter by family / manufacturer, **New item**.
- `.grid`: code, family, design line (indoor only), manufacturer, kind, ports (outdoor), power, VAT, actions. Price may show read-only; it is not edited here.
- Drawer: family (hidden when only one live family), design line (indoor only; filtered by family), manufacturer, internal code, kind, **power**, **max indoor ports** (outdoor), VAT, default checkbox. Indoor may pick a default split outdoor; outdoor may pick compatible indoors. Room volume is not on the item.
- If the chosen design line has a manufacturer, that field is filled and **visible but inactive**. Outdoor items have no design line.
- Soft-delete in the drawer (admin only).

### Families / Sub-families / Manufacturers / VAT / Parameters / Company / Tubing (setup pages)

Same list+drawer chrome except **Company**. Opened from dashboard setup cards only.

- **Families:** name, default.
- **Sub-families:** family, name, optional manufacturer, default; filter by family. Empty manufacturer = shared range.
- **Manufacturers:** name, default. Row opens that brand’s **sales pricelist** (items + sales price). Edit price in a drawer with a **reason**. This is our sales price, not a supplier cost.
- **VAT rates:** code, label, percent (stored as 0–1), default. Soft-delete admin only.
- **Powers:** power, unit, volume from / to (m³), default indoor. Soft-delete admin only if unused.
- **Parameters:** known keys only; edit `value`. No New / Delete.
- **Company:** singleton work page with the form **on the page** (not list+drawer). Name, NIF, address, phone + note, email, contact, IBAN, logo (`enctype=multipart`). No New / Delete.
- **Tubing lengths:** length, price (reason required on price change). Soft-delete admin only.

Do **not** nest Families / Sub-families as a Master-data cluster on the Items page.


### Clients (list + drawer)

Analog of warehouse **Items**, not of nested Suppliers.

- Toolbar: search (name, NIF, city), **New client**.
- `.grid`: name, kind, NIF, city, postal code, actions.
- Row or Edit opens the drawer: `kind`, `name`, NIF, billing street / postal code / city, country (`PT`), optional phone and email. Soft-delete in the drawer (live lists hide deleted rows). Creating a client auto-creates a headquarters site (address copied once).

### Sites (list + drawer)

First-class page. **Do not** nest sites inside the client drawer the way warehouse nests Suppliers under Items. A proforma belongs to a site.

- Toolbar: search, **filter by client**, **New site**.
- `.grid`: client name, `alias_1` (and maybe city), actions.
- Drawer fields from data-points: `client` required; `alias_1` required; `alias_2`–`alias_4` optional; `street`, `postal_code` (`NNNN-NNN`), `city` required; `notes` optional. HQ site cannot be deleted alone.

### Proforma list

- Toolbar: search/filter by status (`draft` / `issued`), **New draft** (must pick a site).
- `.grid`: number (link to work page), site/client, status pills (+ Accepted / Rejected / Superseded when set), total including VAT, updated, **Actions**.
- **Actions:** `draft` → **Edit**. `issued` not accepted not rejected not superseded → **Open** (GET to the issued work page) plus thumbs-up (green) / thumbs-down (red) icons for accept/reject (hover label, Yes/No confirm). Do **not** supersede from the list. `issued` + accepted → **Clear accepted** only. `issued` + rejected → **Clear rejected** only. Superseded → no action.
- Implementation: Phase 5 + supersede slice.

### Proforma work page

Analog of a warehouse **console**, not a Django form wizard.

- Header **on the page** (not in a drawer): commercial discount %, financial discount %, extra labour, validity (days), observations; live totals including stored extra-tubing metres when non-zero, commercial discount amount when non-zero, extra labour, net total, VAT, and total including VAT; **Issue** / **Change** when allowed. Issued header also shows issued-on and valid-until dates.
- Lines: `.grid` grouped by system (outdoor heading, indoor rows under it; item snapshot or live catalog name while draft, qty, tubing, line total).
- **Add split / Add default / Add multi / Add indoor = drawer.** Family hidden while only one live family. **Split:** manufacturer → design line → indoor (matched ports=1 outdoor auto-added). **Default:** room volume m³; optional extra tubing (length shown when checked, shortest catalog length pre-selected); inserts the power-band default indoor + matched split outdoor (qty 1). **Multi:** manufacturer → outdoor (`ports≥2`). **Add indoor** on an outdoor row: design line → indoor from `item_matches`. Quantity; extra tubing on indoor lines only; tubing length only when extra tubing is checked (shortest catalog length pre-selected). If the design line has a manufacturer, that control is filled and inactive.
- **Draft:** editable; **Override checks** checkbox next to Save / Issue (persisted; skips multi occupancy rules); optional “Revision of PF-…” when `replaces` is set.
- **Issued:** read-only; **View quote** / **Download PDF**; **Change** (copy to new draft, Yes/No confirm) only on this page when not accepted, not rejected, and not superseded. Accept / reject / clear live on the **list** (thumbs up/down), not on this page.
- **Issued superseded:** read-only; link to replacement draft; no Change.
- Implementation: Phases 5–7 + supersede slice.

### Issued quote view

Document-like page for the client-facing quote. Still uses the **work topbar** and **Download PDF**. Language from `fu-lang` cookie on the server for PDF.

Layout (on-screen HTML and PDF share `quote_body.html` + `quote_styles.html`):

- **Header:** two columns — left: live company (logo, name, address, NIF, phone, email, contact); right: document title + number, then client snapshot, then site snapshot.
- **Date band:** issued-on and valid-until only.
- **Lines:** existing equipment/qty/unit/tubing/line-total columns; grey table header.
- **Footer:** left — VAT breakdown by frozen rate (base + IVA amount); right — net totals and boxed **total of document** (`total_with_vat`). Header IVA is not duplicated as the hero figure.
- **Below footer:** extra tubing metres (when set), observations, IBAN (when set on company).

Implementation: Phase 7 + company letterhead slice + guia-style layout slice.

---

## What not to copy from warehouse_V2

- Dark theme / `cc-theme`
- Help `?` and user-manual PDFs
- “Sign out other devices”
- JSON item/supplier APIs and client-rendered table bodies (unless a later phase adds an API for a good reason)
- “Master data” button cluster on the Items page (Families / Sub-families / Manufacturers are **dashboard setup cards**, not a toolbar cluster)
- Manager catalog console (`catalog.html`) as a JSON SPA
- Company Voice, branch cards, cost-trends, POs, goods receipts
- Nested supplier-style drawers for sites

---

## Tie-in to [`project-plan.md`](project-plan.md)

| Phase | Front-end delivers |
| ----- | ------------------ |
| 1 | Login, dashboard (language + cards + gear), work-page shell (topbar, empty home-quality chrome), i18n JS |
| 4 | Clients and sites list + drawer |
| 5 | Proforma list + work page + line drawer (draft) |
| 6 | Issue / mark accepted or rejected on the work page; issued read-only |
| 7 | Issued quote view + PDF download |
| 3, 8 | No extra staff chrome (admin / CLI) |

---

## Checkboxes

- [x] Front-end: CSS tokens + dashboard and work layouts (completed 2026-09-06)
- [x] Front-end: gear Settings popover (email + sign out) (completed 2026-09-06)
- [x] Front-end: language select on dashboard only (`fu-lang`) (completed 2026-09-06)
- [x] Front-end: shared drawer (backdrop, Escape, create/edit) (completed 2026-09-06)
- [x] Front-end: Clients list + drawer (completed 2026-09-06)
- [x] Front-end: Sites list + drawer (completed 2026-09-06)
- [x] Front-end: Proforma list + work page + line drawer (completed 2026-09-06)
- [x] Front-end: issued quote view chrome (completed 2026-09-06)
- [x] Front-end: dashboard daily vs setup cards; Items in work nav (completed 2026-09-06)
- [x] Front-end: Items list + drawer (no price) (completed 2026-09-06)
- [x] Front-end: Families / Sub-families / Manufacturers setup pages + pricelist (completed 2026-09-06)
- [x] Front-end: line drawer Family → Sub-family → Manufacturer → Item with defaults (completed 2026-09-06)
- [x] Front-end: VAT on Items + Setup cards for VAT rates, Parameters, Tubing (completed 2026-09-06)
- [x] Front-end: Add default drawer + Powers volume band / default indoor (completed 2026-09-08)
- [x] Front-end: Company setup page (form on page, logo upload, no delete) (completed 2026-09-09)
- [x] Front-end: issued quote/PDF letterhead from live company row (completed 2026-09-09)
