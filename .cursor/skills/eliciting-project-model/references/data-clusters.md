# Phase B clusters

Load at the start of Phase B, after the user is comfortable with the plan. Stay inside the approved app map. Ask what to **omit** as often as what to add.

## 1. Confirm conventions

Walk the always-on list from [conventions.md](conventions.md) once. Only spend questions on vetoes or extras.

## 2. Core entities

From the plan, list candidate nouns (client, item, order, site, …). For each:

- Is this a table, a field on another table, or out of scope?
- Current state vs history (do we need a history table, or only `change_logs`)?
- Which app writes it?

Recommended default: one table per noun that is referenced from more than one screen or app. Do not create a table for a one-off label.

## 3. People

- `users` fields that this project actually needs (email, name, status)
- Roles/permissions: enum on users vs `roles` + `user_roles`
- Clients/customers/contacts/addresses: one record or many
- Uniqueness while soft-deleted (email unique among rows with `deleted_at` null)

Recommended default: `users` + roles if more than one permission set; `clients` with many `contacts` and many `addresses` only if the interview said so.

## 4. Fields and constraints (per entity, one entity per round if large)

For each kept table:

- Required fields
- Enums and lifecycles (status machines)
- Cardinality and foreign keys
- Uniqueness
- Money fields (currency, who may change the amount)
- Reason-required fields (price, status, and anything with a justification dialogue)

Recommended default: conceptual types only (`text`, `number`, `boolean`, `datetime`, `enum`, `fk`, `money`). Do not pick Postgres vs MySQL types.

## 5. Audit and history

Keep the four kinds distinct. For each significant entity, ask:

- Field-level old/new → `change_logs` (always)
- Must staff browse history as a list → per-entity history
- Actions that are not a field write → `activity_logs` (always)
- Must this entity show its own timeline → specific activity table

Canonical example: changing an item price opens a reason dialogue; that field is reason-required and lands in `change_logs`. If they also need a price-history screen, add `item_price_history`.

## 6. Parameters

Always a `parameters` (or `app_settings`) table unless they insist all config is env/code.

Ask: key/value bag vs a few typed rows; which app may edit; whether changes are reason-required.

## 7. What we should not have

Close Phase B with a rejection pass:

- Tables implied by out-of-scope apps
- Duplicate audit tables that collapse the four kinds into one vague "audit"
- History tables for fields nobody will query
- Per-app copies of shared entities

List rejected ideas in `docs/data-points.md` so a later session does not resurrect them silently.

## 8. Open questions

Leave the remaining 30–40% here. Do not fill gaps with invented columns.
