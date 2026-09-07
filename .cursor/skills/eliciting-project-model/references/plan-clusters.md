# Phase A clusters

Load at the start of Phase A. Ask only frontier questions. Do not turn these into a checklist the user must finish in one sitting.

Skip a cluster when the existing plan or codebase already settled it and the user is not reopening it.

## 1. Destination

- What is this product for, in one sentence?
- Who uses it (roles, not job titles only)?
- What does "working" look like for the first shippable slice?
- What must never happen (data loss, silent price edits, client seeing admin data)?

Recommended default: one primary user role plus an operator/admin role, unless they say it is consumer-only.

## 2. Apps and surfaces

Projects here usually have **more than one app** for organization and maintenance. Discover the map before any tables.

Ask which of these exist now or in this effort:

- Admin / back office
- Client or customer portal
- Internal staff app
- Public marketing or intake site
- Mobile app
- Background worker / jobs
- Shared API

For each yes: purpose, who logs in, what it must never do.

Recommended default: one admin app and one client-facing app, plus a worker if anything is emailed, billed, or logged asynchronously. Do not invent a mobile app unless they need it.

## 3. Ownership and sharing

For each capability (clients, catalog, billing, users, settings, audit):

- Which app is the source of truth for writes?
- Which apps may read?
- Is there one shared database or separate stores?

Recommended default: one shared database, admin writes reference data, client app writes only its own actions, audit tables writable from every app that can change data.

## 4. Tenancy and identity

- One company or many (multi-tenant)?
- Are "user" and "client/customer" the same person or different records?
- How do people get access (invite, signup, staff-provisioned)?
- Must every action be attributable to a person, or can automation act?

Recommended default: users are login identities; clients/customers are domain records; staff users are not the same table as clients unless it is truly a consumer app. Automation may act with null `created_by` and `actor_type = system`.

## 5. Scope

- In scope for this effort
- Explicitly out of scope (apps, integrations, locales, payments)
- Existing systems this must not duplicate

Recommended default: record out-of-scope items in the plan so Phase B does not grow tables for them.

## 6. Product behaviors that force data later

Do not design columns here. Do mark behaviors that Phase B must implement as tables:

- Fields that need a **reason-for-change** dialogue (price is the canonical example)
- Parameters/settings staff will edit without a deploy
- Activities the business must trace for the life of the project
- Files, notifications, money, or scheduling if they are in scope

Recommended default: assume reason-required on money and status changes; assume a parameters table; assume generic activity logging.

## Multi-app anti-patterns

- One "the app" with every role behind a flag, when they already described separate products
- A table per app for the same entity (`admin_clients` and `portal_clients`) without a shared core
- Grilling all apps' schemas before the app map is confirmed
- Treating a worker process as not an app, then surprising Phase B with job tables
