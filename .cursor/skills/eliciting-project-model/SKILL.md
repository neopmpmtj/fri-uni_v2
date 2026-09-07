---
name: eliciting-project-model
description: Interviews the user about a data-backed project until the plan and data model are explicit, then writes docs/preliminary_project-plan.md and docs/data-points.md after an explicit go-ahead. Use when starting a project, scoping multiple apps, gathering tables and fields, asking to be grilled on a plan, discussing changelogs or activity logs, or when the user says grill me, data points, project plan, or what tables do we need.
license: MIT
metadata:
  author: pedro-julio
  version: "1.0"
---

# Eliciting a project model

Two-phase interview for data-backed products. Phase A settles the project and its apps. Phase B settles tables and fields against that plan. Write nothing until the user gives an explicit go-ahead. Never implement schema.

Read these only when needed:

- Round format, frontier, facts vs decisions: [references/interview.md](references/interview.md)
- Phase A question clusters (including multi-app): [references/plan-clusters.md](references/plan-clusters.md)
- Phase B question clusters: [references/data-clusters.md](references/data-clusters.md)
- Always-on columns and the four audit table types: [references/conventions.md](references/conventions.md)
- File shapes: [assets/project-plan.template.md](assets/project-plan.template.md), [assets/data-points.template.md](assets/data-points.template.md)

## When to use

- Greenfield project with a database, or mid-development when the model is still incomplete
- User wants to be grilled, asked questions, or walked through data points
- Multiple apps or surfaces (admin, portal, mobile, worker) need organizing
- User asks what tables, changelogs, activity logs, or parameters the project needs

## When not to use

- Short always-on coding constraints (those are rules)
- User already has approved docs and wants migrations, ORM models, or seed data
- Pure UI/copy work with no data or product-scope decisions
- The user only wants a spec synthesized from an already-finished grilling session with no new decisions

## Hard stops

- Do not write `docs/preliminary_project-plan.md` or `docs/data-points.md` until the user explicitly says to.
- Do not write or overwrite `docs/project-plan.md`. That file is this project's checkbox backlog, not this skill's output.
- Do not create, alter, or emit migrations, SQL DDL, ORM models, seed data, or application code. Not even if the user sounds ready. This skill ends at the two documents.
- Do not start Phase B until the user is comfortable with the plan. If they ask for tables first, say Phase A comes first unless they insist on a documented override.
- Do not overwrite `docs/preliminary_project-plan.md`. Append a dated `## Update YYYY-MM-DD` section.
- Do not skip reading existing docs (and, mid-project, the live schema source).

## 0. Orient

Before the first question:

1. Read `docs/` if it exists, especially `docs/preliminary_project-plan.md` and `docs/data-points.md`. Also read `docs/project-plan.md` if present (backlog only; do not write to it).
2. If this is mid-development, also read the live schema source (migrations, Prisma, SQLAlchemy, and similar). Do not quiz the user on facts already in the repo.
3. Summarize what is already known and name contradictions. Ask about those before opening a new cluster.

If no docs exist, say so and start Phase A from a blank tree.

## Interview protocol

Borrow the grilling shape, not a dump of 40 questions.

- Map the subject as a **design tree**. Each settled decision unblocks later ones.
- Ask in **rounds**. A round is the **frontier**: every question whose prerequisites are settled, and none that still depend on an unanswered one. Cap a round at **5–8** questions.
- Every question includes a **recommended answer**. The user may accept, reject, or say they do not know.
- **Facts** (files, existing tables, named apps in the plan) are the agent's job to look up. **Decisions** are the user's. Do not answer decisions for them.
- When the user says "ask me questions", stay in the current phase and the largest remaining gap. Do not restart from zero.
- Target about **60–70%** coverage. Remaining items go under Open questions. Do not chase 100%.
- "I don't know" is a valid answer. Park it as an open question rather than inventing a table.
- End a phase only when the frontier is empty **and** the user confirms shared understanding. Then wait for go-ahead before writing that phase's file.

Question format (use this in chat, not in the docs):

```text
Q1 - <title>: <body, including why this becomes an app, table, or field>
Recommended: <one concrete answer>
```

If the round format is unclear, read [references/interview.md](references/interview.md) before asking.

## Phase A — project plan

Goal: a plan the user is comfortable with, including **which apps exist** and what each one is for. Do not discuss columns yet.

Load [references/plan-clusters.md](references/plan-clusters.md) at the start of this phase. Work clusters in dependency order. Typical order:

1. Destination, users, and what success looks like
2. Apps and surfaces (admin, client portal, mobile, worker, public site, and so on)
3. What each app owns vs what is shared
4. Tenancy, auth, and who may act
5. In scope / out of scope for this effort
6. Cross-cutting product behavior that will later force tables (reason-for-change dialogues, parameters, activity the business must trace)

When the frontier is empty, summarize the plan in chat: purpose, apps, ownership, out of scope, open questions. Ask the user to confirm they are comfortable.

On explicit go-ahead to write the plan:

- Create `docs/` if needed.
- If `docs/preliminary_project-plan.md` does not exist, write it from [assets/project-plan.template.md](assets/project-plan.template.md).
- If it exists, **append only**. Add `## Update YYYY-MM-DD` with new decisions and deltas. Do not rewrite earlier sections. Do not duplicate unchanged apps.

Then, and only then, start Phase B.

## Phase B — data points

Goal: conceptual tables and fields for the approved app map, including what **not** to have.

Load [references/data-clusters.md](references/data-clusters.md) and [references/conventions.md](references/conventions.md) at the start of this phase.

Rules:

- Stay conceptual: table name, purpose, fields, types as text/number/boolean/datetime/enum/fk/money, uniqueness, cardinality. No dialect-specific SQL, index DDL, or ORM.
- Apply always-on columns and the default audit tables from conventions unless the user vetoes a specific one.
- Scope tables to the approved apps: shared core vs app-specific. Do not invent a table for an app that was ruled out of scope.
- Mark reason-required fields. Those are not a silent UPDATE.
- Keep the four audit kinds distinct: `change_logs`, per-entity history, `activity_logs`, entity-specific activity. See conventions.

When the frontier is empty, summarize tables, what was rejected, and open questions. Wait for go-ahead.

On explicit go-ahead to write data points:

- Rewrite `docs/data-points.md` **in place** from [assets/data-points.template.md](assets/data-points.template.md) so it stays one source of truth.
- Merge with any existing file: keep tables that are still true, fold in new ones, drop only what this session explicitly rejected. Do not leave three conflicting `clients` tables.
- Preserve still-open questions.

## Always-on defaults (unless the user vetoes)

Every entity table gets `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at` (null = live), `deleted_by`.

Always create, unless the interview finds a reason not to:

- `users` (and roles/permissions if more than one kind of actor)
- `change_logs` (entity, field, old, new, actor, time; `reason` required only when the field is marked reason-required)
- `activity_logs` (actions that are not a single field write)
- `parameters` (app settings), unless all config lives in env/code

Create extra tables only when justified:

- Per-entity history when history is a first-class list or report (price history, status history)
- Entity-specific activity when that entity has a user-facing timeline

`created_by` / `updated_by` may be null for automation. Logs record actor type `user` or `system`.

## Continuity

- Greenfield: Phase A, then Phase B, files only on go-ahead.
- Mid-project: orient from docs and schema first. Phase A still runs if the app map or scope is unclear; otherwise confirm the existing plan and go to Phase B.
- Later sessions append the plan and rewrite data points after a merge pass.
- Clarify ambiguities with the user before writing either file.

## Done when

The user confirmed shared understanding for the phases that ran, any requested docs exist in `docs/` with the correct write rules, open questions are listed, and no schema code was emitted.
