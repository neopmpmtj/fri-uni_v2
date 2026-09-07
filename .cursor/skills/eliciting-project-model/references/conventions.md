# Data conventions

Load at the start of Phase B, or when the user mentions changelogs, activity logs, soft delete, or parameters.

## Always-on columns

Every entity table includes:

| Column | Meaning |
| --- | --- |
| `created_at` | Insert time |
| `updated_at` | Last update time |
| `created_by` | FK to `users`, nullable for automation |
| `updated_by` | FK to `users`, nullable for automation |
| `deleted_at` | Soft delete; **null means live** |
| `deleted_by` | Who soft-deleted; null if live |

Do not use a boolean `is_deleted` unless the user vetoes timestamps.

Unique constraints apply to **live** rows (`deleted_at` is null). Say that in the data-points doc; do not emit SQL.

## Four audit kinds (do not collapse)

| Table | When | Typical fields |
| --- | --- | --- |
| `change_logs` | Always. Field-level old/new. | entity type, entity id, field, old value, new value, actor, actor type (`user` \| `system`), time, `reason` (required only if the field is reason-required) |
| Per-entity history (e.g. `item_price_history`) | Only when history is a first-class list or report | the business fields being historized, effective time, actor, reason if required |
| `activity_logs` | Always. Actions that are not a single field write (login, export, invite). | actor, actor type, action, object type, object id, time, details |
| Entity-specific activity (e.g. `order_activities`) | Only when that entity has a user-facing timeline | the same shape, scoped to one parent entity |

A price change with a reason dialogue is **`change_logs` + reason-required**. It is not an activity row. It becomes `item_price_history` only if they need to browse prices over time as their own screen or report.

## Users and parameters

- `users` is always in the model for a data-backed app in this skill's default set.
- `parameters` is always in the model unless the interview shows all config lives in env/code.
- Roles: add `roles` / `user_roles` (or equivalent) when more than one permission set exists.

## System actors

Jobs, webhooks, and migrations may write data. `created_by` / `updated_by` may be null. `change_logs` and activity tables still get a row with `actor_type = system`.

## Conceptual types only

Record fields as `text`, `number`, `boolean`, `datetime`, `enum`, `fk`, or `money`. Do not choose a SQL dialect, ORM, or index names in these docs.
