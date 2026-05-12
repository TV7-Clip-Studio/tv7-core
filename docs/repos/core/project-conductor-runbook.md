# Project Conductor Runbook

## Purpose
Run deterministic ticket planning and ticket syncing for TV7 repos using Project Conductor.

Conductor runtime is implemented in sibling repo `tv7-conductor`.
`tv7-core` Make targets are shim entry points.

## Governance References
- Charter: `docs/repos/core/project-conductor-charter.md`
- Phase gates: `docs/repos/core/project-conductor-phase-gates.md`
- Failure policy: `docs/repos/core/project-conductor-failure-policy.md`
- Runtime policy config: `../tv7-conductor/tooling/orchestrator/conductor_policy.toml`
- Execution sandbox policy: `../tv7-conductor/tooling/orchestrator/execution_policy.toml`
- Review loop policy: `../tv7-conductor/tooling/orchestrator/review_policy.toml`

## Prerequisites
- Python 3.11+
- `gh` authenticated (`gh auth status`)
- `gemini` and/or `codex` CLI available (depending on selected profile)
- Workspace layout rooted at `TV7/` with sibling repos including `tv7-conductor`

## State Location
- Runtime state: `../tv7-conductor/docs/.conductor/state.json`
- Events log: `../tv7-conductor/docs/.conductor/events.jsonl`
- Iteration artifacts: `../tv7-conductor/docs/.conductor/runs/<iteration_id>/`
- Ticket sync reports: `../tv7-conductor/docs/.conductor/reports/ticket-sync-*.json|.md`
- Planning artifacts: `state.planning.idea_runs` and `state.planning.intent_queue`
- Execution artifacts: `state.agent_runs[]` entries with `run_type=execute_handoff`
- Review artifacts: `work_items[].review_feedback`, `work_items[].review_verdict`

## Commands (from `tv7-core`)
```bash
cd tv7-core
make conductor-init
make conductor-plan
make conductor-tickets
make conductor-tickets-apply
make conductor-expand
make conductor-expand-apply
make conductor-execute
make conductor-execute-apply
make conductor-review
make conductor-review-apply
make conductor-status
make conductor-ops-status
make conductor-events
```

Single-repo run:
```bash
cd tv7-core
make conductor-run CONDUCTOR_TICKET_REPO=tv7-astro-site
```

Roadmap-scoped run:
```bash
cd tv7-core
make conductor-run CONDUCTOR_ROADMAP_FILE=docs/roadmaps/tv7-astro-site-roadmap.md
```

All-repo run:
```bash
cd tv7-core
make conductor-run
```

Ground-zero cleanup:
```bash
cd tv7-core
make conductor-tickets-reset-scan
make conductor-tickets-reset-scan-apply
rm -rf ../tv7-conductor/docs/.conductor
make conductor-init
```

## Labels applied to issues
Base labels:
- `conductor`
- `type:task`
- `source:roadmap`

Dynamic labels:
- `repo:<repo-name>`
- `batch:<batch-id>` (when provided)
- `stage:seed`
- repo defaults labels from `../tv7-conductor/tooling/orchestrator/repo_defaults.toml`

## Notes
- `make conductor-run` executes `plan` then `tickets`.
- `CONDUCTOR_RUN_FLAGS` is passed to `../tv7-conductor/tooling/conductor_run.py`.
- `CONDUCTOR_EXECUTE_POLICY` and `CONDUCTOR_REVIEW_POLICY` default to paths inside `tv7-conductor`.
