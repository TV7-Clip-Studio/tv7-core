# TV7 Core Roadmap

Roadmap Code: CO
Batch Code: A01

Last updated: 2026-02-08

## Done
- [X] [CO-A01-01-01] Established `tv7-core` as the shared docs/tooling repo with symlink-first workflow.
- [X] [CO-A01-01-02] Standardized sibling workspace layout across `tv7-*` repositories.
- [X] [CO-A01-01-03] Added shared Make targets for cross-repo bootstrap/sync/status flows.
- [X] [CO-A01-01-04] Consolidated global architecture and agent workflow docs into core-managed paths.

## Needs To Be Done
- [ ] [CO-A01-02-01] Complete docs reorganization so every active reference resolves without legacy fallbacks.
- [ ] [CO-A01-02-02] Keep the product coordination roadmap current with active owners and status updates.
- [ ] [CO-A01-02-03] Add a stable index for standards, architecture, and runbooks to reduce path drift.
- [ ] [CO-A01-02-04] Tighten governance around what is allowed in repo-local docs vs core docs.

## Nice To Have
- [ ] [CO-A01-03-01] Add a docs link checker in CI for all markdown links and symlink targets.
- [ ] [CO-A01-03-02] Publish shared templates for recurring deliverables (roadmap updates, ADRs, handoffs).
- [ ] [CO-A01-03-03] Add a single command for validating all repo symlinks and reporting drift.
