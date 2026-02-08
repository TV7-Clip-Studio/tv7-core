# TV7 Core Roadmap

Last updated: 2026-02-08

## Done
- [x] Established `tv7-core` as the shared docs/tooling repo with symlink-first workflow.
- [x] Standardized sibling workspace layout across `tv7-*` repositories.
- [x] Added shared Make targets for cross-repo bootstrap/sync/status flows.
- [x] Consolidated global architecture and agent workflow docs into core-managed paths.

## Needs To Be Done
- [ ] Complete docs reorganization so every active reference resolves without legacy fallbacks.
- [ ] Keep the product coordination roadmap current with active owners and status updates.
- [ ] Add a stable index for standards, architecture, and runbooks to reduce path drift.
- [ ] Tighten governance around what is allowed in repo-local docs vs core docs.

## Nice To Have
- [ ] Add a docs link checker in CI for all markdown links and symlink targets.
- [ ] Publish shared templates for recurring deliverables (roadmap updates, ADRs, handoffs).
- [ ] Add a single command for validating all repo symlinks and reporting drift.
