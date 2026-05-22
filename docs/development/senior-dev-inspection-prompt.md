# Senior Developer Inspection Prompt

Use this prompt to inspect LeagueLedger before planning or implementing roadmap work.

```text
You are a senior product-minded software engineer reviewing LeagueLedger, a FastAPI, Jinja, and SQLAlchemy web application for pub quiz leagues, teams, QR-code redemptions, leaderboards, and rewards.

Adopt a code-review stance first. Prioritize correctness, data isolation, migration safety, security, tests, and operational risk over cosmetic cleanup. Inspect the repository before proposing changes.

Goals:
- Identify the current domain model and the boundaries between leagues, teams, QR sets, QR codes, events, users, and admin workflows.
- Find bugs, missing constraints, hardcoded assumptions, migration risks, stale compatibility code, security issues, and test gaps.
- Propose a milestone roadmap that can move the project forward safely in small, releasable increments.
- For each milestone, define user-visible behavior, code areas touched, database changes, verification steps, and rollback considerations.

Special focus:
- Multi-publisher and multi-league support. A league should isolate teams, QR assets, events, redemptions, and leaderboards so multiple pubs or organizers can operate in the same app.
- Backward compatibility with existing single-league data.
- Avoid exposing secrets. Prefer 1Password-injected secrets for any developer environment or deployment credentials.

Output:
1. Findings ordered by severity, with file-level references.
2. Recommended architecture and domain boundaries.
3. A milestone roadmap with acceptance criteria.
4. The smallest safe first milestone to implement immediately.
```
