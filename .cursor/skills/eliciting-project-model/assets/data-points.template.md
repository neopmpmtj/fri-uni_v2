# Data points

Conceptual model only. Not SQL, not ORM, not seeds.

## Conventions

Always-on columns on every entity table: `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at` (null = live), `deleted_by`.

Unique keys apply to live rows only.

Audit defaults: `change_logs` (field-level), `activity_logs` (actions). Per-entity history and entity-specific activity only where listed below.

`created_by` / `updated_by` may be null for `actor_type = system`.

## Apps this model serves

<!-- Shared core vs app-specific tables. Taken from docs/preliminary_project-plan.md. -->

## Tables

### users

- Purpose:
- Written by (apps):
- Fields:
- Uniqueness:
- Notes:

### change_logs

- Purpose: field-level old/new
- Fields: entity type, entity id, field, old value, new value, actor, actor type, time, reason (required only for reason-required fields)
- Reason-required fields elsewhere:

### activity_logs

- Purpose: actions that are not a single field write
- Fields: actor, actor type, action, object type, object id, time, details

### parameters

- Purpose: settings editable without a deploy, unless the session ruled this out
- Fields:
- Reason-required: yes/no

### <entity>

- Purpose:
- Written by (apps):
- Fields (name, conceptual type, required, notes):
- Relationships:
- Uniqueness:
- Reason-required fields:
- Extra history table: no | `<name>` (why)
- Extra activity table: no | `<name>` (why)

## Rejected

<!-- Tables or fields we explicitly will not have, so later sessions do not resurrect them. -->

## Open questions

<!-- Remaining 30–40%. -->
