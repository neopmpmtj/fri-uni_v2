# New project workflow

1. Copy `bootstrap.sh` into an empty folder.
2. Make it executable (see below) and run:
   ```bash
   ./bootstrap.sh
   ```
   You will be prompted:
   - **1) POC / minimal** — default Django user (username); no `accounts` app
   - **2) Email login** — `accounts` app with email `User` (OAuth-ready fields)

   Non-interactive: `BOOTSTRAP_AUTH=poc ./bootstrap.sh` or `BOOTSTRAP_AUTH=email ./bootstrap.sh`
   Or without the execute bit:
   ```bash
   bash bootstrap.sh
   ```
3. `cp .env.example .env`
4. `.venv/bin/python manage.py migrate`
5. `manage.py startapp` when you're ready for your first app (POC mode only; email mode already includes `accounts`).

## Do I need `chmod +x` first?

**Sometimes.** Copying the file may or may not keep the executable bit, depending on how you copy it (`cp`, drag-and-drop, zip, etc.).

- If `./bootstrap.sh` says "Permission denied", run once:
  ```bash
  chmod +x bootstrap.sh
  ```
- Or skip that and use `bash bootstrap.sh` — no execute bit required.

After a successful run, `bootstrap.sh` sets `chmod +x` on itself in that folder, so later runs can use `./bootstrap.sh`.

## Reset and re-bootstrap

To recreate the scaffold from scratch in this folder, delete everything **except** `bootstrap.sh`, then run `./bootstrap.sh` again (or `bash bootstrap.sh`). That restores all files the script generates: Django `conf/`, `.cursor/`, docs, `.venv` (recreated), and `git init` if `.git` was removed.

You will **not** get back: `.env`, `db.sqlite3`, manual edits, or anything not defined inside `bootstrap.sh` (e.g. `.cursor/plans/` from a prior session).
