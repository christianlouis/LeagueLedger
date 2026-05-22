# LeagueLedger Roadmap

This roadmap is based on a senior-developer inspection of the current FastAPI, Jinja, and SQLAlchemy codebase.

## Current Findings

- LeagueLedger currently treats teams, QR sets, events, redemptions, and leaderboards as global records. That blocks multiple pubs or organizers from sharing one installation cleanly.
- Database migrations are split between `app/db.py` and `app/db_migrations.py`. This increases drift risk because schema changes can land in one path and not the other.
- Tests are thin and some existing tests mock SQLAlchemy chains in ways that do not match the current query implementation.
- Several workflows still include compatibility branches for removed model names, which makes behavior harder to reason about.
- QR redemption did not consistently record the redeeming user on the QR code record, weakening auditability.

## Milestones

### 1. Multi-League Foundation

Status: implemented in this branch.

Acceptance criteria:
- Add a `League` model with a default league for existing data.
- Attach teams, QR sets, QR codes, and events to a league.
- Filter team lists, QR dashboards, leaderboards, and redemption team choices by league.
- Keep existing URLs and seeded data working.
- Backfill existing records into the default league during startup migrations.

### 2. League Administration

Acceptance criteria:
- Add a dedicated admin workflow for creating, editing, activating, and archiving leagues.
- Allow league managers to administer only their own league.
- Replace generic admin CRUD for league-sensitive records with validated forms where needed.
- Add tests for league creation, activation, and manager permissions.

### 3. Data Isolation and Permissions

Acceptance criteria:
- Introduce league-level roles for owners, quiz masters, and staff.
- Enforce league boundaries in every query that reads or mutates teams, events, QR sets, QR codes, achievements, and leaderboards.
- Add authorization tests covering cross-league access attempts.

### 4. Migration Cleanup

Acceptance criteria:
- Consolidate schema migrations into one approach.
- Add repeatable migration tests against a fresh database and a simulated legacy database.
- Remove stale compatibility code after migration coverage is in place.

### 5. Release Hardening

Acceptance criteria:
- Add CI checks for syntax, tests, and a lightweight app smoke test.
- Document local development with 1Password-injected environment secrets.
- Add a release checklist with migration, rollback, and verification steps.
