# Project Conductor Charter

## Status
- Phase 1 charter baseline approved for implementation planning.
- Effective date: 2026-02-28.
- Owner: Architect Agent.

## Architecture Decision
Project Conductor is the canonical orchestration path for roadmap-to-execution coordination in TV7.

Decision:
- Keep roadmap parsing, coordination policy, and lifecycle governance centralized in `tv7-core`.
- Keep per-repo execution in each repo, with Conductor issuing scoped work and recording deterministic state.
- Keep legacy `orchestrator-*` commands available until migration gates pass.

## Goals
- Provide deterministic and idempotent work-item ingestion from roadmap files.
- Enforce scoped ticket operations (`repo`, `roadmap`, `item-prefix`) to avoid global accidental writes.
- Separate `seed` (minimal issue body) from `expand` (enriched planning context).
- Preserve a strict lifecycle for each work item with explicit transitions and observable events.
- Keep DeepSeek feedback loops actionable and bounded before integration completion.

## Non-Goals
- No background daemon/orchestrator service in Phase 1.
- No automatic production deploys or PR auto-merge.
- No ecosystem-wide refactors as part of migration plumbing.
- No replacement of per-repo CI with Conductor-local logic.

## Target Flow
1. `plan`: parse roadmap markdown into deterministic work items.
2. `seed`: create or link scoped issues with minimal deterministic body content.
3. `expand`: enrich seeded issues in controlled, idempotent updates.
4. `execute`: hand off work item context to per-repo execution agent.
5. `review`: apply DeepSeek feedback loops until approved or escalated.
6. `integrate`: run final validation matrix, then mark done.

## Success Metrics
- Zero off-scope issue creation during scoped runs.
- Stable item IDs and no duplicate issue creation on reruns.
- Reproducible reports in `docs/.conductor/reports/` for each run mode.
- Review loops bounded by configurable max loops and clear escalation state.
- Two clean full migration batches before decommissioning legacy commands.

## Deprecation Criteria For Legacy Orchestrator Surface
Legacy `orchestrator-*` commands can be removed only when all are true:
- Two full clean Conductor batches complete with zero blocking regressions.
- Expand/review/integrate stages are fully wired in Conductor run flow.
- Phase gate sign-offs in `project-conductor-phase-gates.md` are all PASS.
- Runbook and operator commands validated from clean workspace setup.

## Stakeholder Sign-Off Checklist
- [ ] Architect owner confirms scope and policy completeness.
- [ ] Repo owners confirm execution handoff expectations.
- [ ] CI/review owner confirms feedback loop and escalation behavior.
- [ ] Final migration sign-off recorded before legacy command removal.
