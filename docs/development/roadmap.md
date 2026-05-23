# LeagueLedger Roadmap

This roadmap is based on a senior-developer inspection of the current FastAPI, Jinja, and SQLAlchemy codebase.

## Roadmap Execution (GitHub)

This document describes outcomes and acceptance criteria. Execution is tracked in GitHub:

- Umbrella roadmap issue: https://github.com/christianlouis/LeagueLedger/issues/144
- GitHub milestones track versions (`v0.3.0` → `v1.0.0`).
- Each version has a release epic (label: `roadmap`) with sub-issues for the scoped work.

## Current Findings

- LeagueLedger currently treats teams, QR sets, events, redemptions, and leaderboards as global records. That blocks multiple pubs or organizers from sharing one installation cleanly.
- Database migrations are split between `app/db.py` and `app/db_migrations.py`. This increases drift risk because schema changes can land in one path and not the other.
- Tests are thin and some existing tests mock SQLAlchemy chains in ways that do not match the current query implementation.
- Several workflows still include compatibility branches for removed model names, which makes behavior harder to reason about.
- QR redemption did not consistently record the redeeming user on the QR code record, weakening auditability.

## Feature Landscape (Themes)

These themes reflect what a modern, operator-friendly loyalty + league product typically needs beyond the foundational multi-league work.

### Foundation & Governance (P0)

- Multi-league operations: league creation, archival, and delegation.
- Role-based access control (RBAC) and strict data isolation by league.
- Migration safety and release hygiene (CI, smoke tests, release checklist).

### QR Trust, Fraud Prevention & Auditability (P0/P1)

- Rotating/expiring QR codes, replay protection, and rate limits.
- Clear redemption audit trails and admin review tooling.

### Engagement, Rewards & Retention (P1)

- Rewards catalog and redemption flow (points → rewards).
- Seasons (timeboxed leaderboards) and historical archives.
- Notifications, announcements, and team communication.
- Optional Apple/Google Wallet passes for “always-on” engagement.

### Integrations & Automation (P1/P2)

- Webhooks + exports as the baseline “integration surface”.
- Slack/Discord notifications and calendar feeds (ICS).
- PWA + offline QR scanning to make the mobile experience resilient.

### Analytics, Insights & Reporting (P2)

- Admin reports, retention/cohort analytics, and operational dashboards.

### Platform Extensibility + MCP/AI (P2/P3)

- Public API (read-first) with rate limits and scoped auth.
- MCP server for safe “tools” (create event, generate QR sets, query stats).
- Guardrailed AI operator UX built on top of MCP tools.

## Release Plan (GitHub Milestones)

| Version | Focus | Tracking Epic | Target (UTC) |
| --- | --- | --- | --- |
| v0.2.0 | Multi-league foundation (shipped) | Release notes: https://github.com/christianlouis/LeagueLedger/releases/tag/v0.2.0 | 2026-05-22 |
| v0.3.0 | League administration | https://github.com/christianlouis/LeagueLedger/issues/145 | 2026-06-30 |
| v0.4.0 | Data isolation + RBAC | https://github.com/christianlouis/LeagueLedger/issues/151 | 2026-07-31 |
| v0.5.0 | Migrations + release hardening | https://github.com/christianlouis/LeagueLedger/issues/156 | 2026-08-31 |
| v0.6.0 | QR trust + security | https://github.com/christianlouis/LeagueLedger/issues/162 | 2026-09-30 |
| v0.7.0 | Engagement layer | https://github.com/christianlouis/LeagueLedger/issues/165 | 2026-10-31 |
| v0.8.0 | Integrations + automation | https://github.com/christianlouis/LeagueLedger/issues/168 | 2026-11-30 |
| v0.9.0 | Analytics + reporting | https://github.com/christianlouis/LeagueLedger/issues/173 | 2026-12-31 |
| v1.0.0 | Platform + MCP + AI operator | https://github.com/christianlouis/LeagueLedger/issues/176 | 2027-03-31 |

## Milestones

### 1. Multi-League Foundation

Status: implemented in this branch.
Release: `v0.2.0` (shipped).

Acceptance criteria:
- Add a `League` model with a default league for existing data.
- Attach teams, QR sets, QR codes, and events to a league.
- Filter team lists, QR dashboards, leaderboards, and redemption team choices by league.
- Keep existing URLs and seeded data working.
- Backfill existing records into the default league during startup migrations.

### 2. League Administration

Release: `v0.3.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/145).

Acceptance criteria:
- Add a dedicated admin workflow for creating, editing, activating, and archiving leagues.
- Allow league managers to administer only their own league.
- Replace generic admin CRUD for league-sensitive records with validated forms where needed.
- Add tests for league creation, activation, and manager permissions.

### 3. Data Isolation and Permissions

Release: `v0.4.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/151).

Acceptance criteria:
- Introduce league-level roles for owners, quiz masters, and staff.
- Enforce league boundaries in every query that reads or mutates teams, events, QR sets, QR codes, achievements, and leaderboards.
- Add authorization tests covering cross-league access attempts.

### 4. Migration Cleanup

Release: `v0.5.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/156).

Acceptance criteria:
- Consolidate schema migrations into one approach.
- Add repeatable migration tests against a fresh database and a simulated legacy database.
- Remove stale compatibility code after migration coverage is in place.

### 5. Release Hardening

Release: `v0.5.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/156).

Acceptance criteria:
- Add CI checks for syntax, tests, and a lightweight app smoke test.
- Document local development with 1Password-injected environment secrets.
- Add a release checklist with migration, rollback, and verification steps.

### 6. QR Trust + Security

Release: `v0.6.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/162).

Acceptance criteria:
- Support rotating/dynamic QR codes where appropriate (see https://github.com/christianlouis/LeagueLedger/issues/96).
- Support expiration and scheduling for QR codes (see https://github.com/christianlouis/LeagueLedger/issues/102).
- Provide QR usage statistics (see https://github.com/christianlouis/LeagueLedger/issues/98).
- Add a redemption audit trail + admin review workflow.
- Add anti-fraud controls (rate limits, replay protection, optional constraints) with tests.

### 7. Engagement Layer

Release: `v0.7.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/165).

Acceptance criteria:
- Rewards catalog primitives and a redemption flow (see https://github.com/christianlouis/LeagueLedger/issues/166).
- Seasons and controlled leaderboard resets with archives (see https://github.com/christianlouis/LeagueLedger/issues/167).
- Notifications and team comms are usable and league-scoped (see https://github.com/christianlouis/LeagueLedger/issues/75 and https://github.com/christianlouis/LeagueLedger/issues/92).
- Wallet passes are available as an opt-in enhancement (see https://github.com/christianlouis/LeagueLedger/issues/180).

### 8. Integrations + Automation

Release: `v0.8.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/168).

Acceptance criteria:
- Webhook framework exists for core events (see https://github.com/christianlouis/LeagueLedger/issues/169).
- Slack/Discord notifications are available (see https://github.com/christianlouis/LeagueLedger/issues/170).
- Calendar feeds (ICS) are available (see https://github.com/christianlouis/LeagueLedger/issues/171).
- Exports v1 exist for core objects (see https://github.com/christianlouis/LeagueLedger/issues/172).
- PWA can be installed and supports offline scan queue + sync (see https://github.com/christianlouis/LeagueLedger/issues/181).

### 9. Analytics + Reporting

Release: `v0.9.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/173).

Acceptance criteria:
- Admin reports exist for key operational views (see https://github.com/christianlouis/LeagueLedger/issues/23).
- Basic performance/health metrics are tracked (see https://github.com/christianlouis/LeagueLedger/issues/85).
- Cohort/retention analytics and report templates exist (see https://github.com/christianlouis/LeagueLedger/issues/174 and https://github.com/christianlouis/LeagueLedger/issues/175).

### 10. Platform + MCP + AI Operator

Release: `v1.0.0` (tracking: https://github.com/christianlouis/LeagueLedger/issues/176).

Acceptance criteria:
- Public API v1 exists with scoped auth + rate limits (see https://github.com/christianlouis/LeagueLedger/issues/177).
- MCP server exists for safe operator tooling (see https://github.com/christianlouis/LeagueLedger/issues/178).
- AI operator UX uses MCP tools with explicit guardrails (see https://github.com/christianlouis/LeagueLedger/issues/179).
- Security baseline is in place (see https://github.com/christianlouis/LeagueLedger/issues/64, https://github.com/christianlouis/LeagueLedger/issues/66, https://github.com/christianlouis/LeagueLedger/issues/68).
- Backup/restore is available (see https://github.com/christianlouis/LeagueLedger/issues/82).
- API documentation is up to date (see https://github.com/christianlouis/LeagueLedger/issues/104).
