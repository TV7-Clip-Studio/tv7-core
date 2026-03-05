# Project Conductor Runbook

## Purpose
Run deterministic ticket planning and ticket syncing for TV7 repos using Project Conductor.

## Governance References
- Charter: `docs/repos/core/project-conductor-charter.md`
- Phase gates: `docs/repos/core/project-conductor-phase-gates.md`
- Failure policy: `docs/repos/core/project-conductor-failure-policy.md`
- Policy config: `tooling/orchestrator/conductor_policy.toml`
- Execution sandbox policy: `tooling/orchestrator/execution_policy.toml`
- Review loop policy: `tooling/orchestrator/review_policy.toml`

## Prerequisites
- Python 3.11+
- `gh` authenticated (`gh auth status`)
- `gemini` and/or `codex` CLI available (depending on selected profile)
- Workspace layout rooted at `TV7/` with sibling repos

## State Location
- Runtime state: `docs/.conductor/state.json`
- Events log: `docs/.conductor/events.jsonl`
- Iteration artifacts: `docs/.conductor/runs/<iteration_id>/`
- Ticket sync reports: `docs/.conductor/reports/ticket-sync-*.json|.md`
- Planning artifacts: `state.planning.idea_runs` and `state.planning.intent_queue`
- Execution artifacts: `state.agent_runs[]` entries with `run_type=execute_handoff` and run logs under `docs/.conductor/runs/execute-*/`
- Review artifacts: `work_items[].review_feedback` (normalized retry payloads + findings), `work_items[].review_verdict`
- Repo defaults config: `tooling/orchestrator/repo_defaults.toml`

## Commands
```bash
cd tv7-core
make conductor-init
make conductor-plan
make conductor-graph-plan    # dry-run IDEA ingestion + queue emit (+ expand handoff dry-run)
make conductor-graph-plan-apply
make conductor-tickets        # dry-run issue sync
make conductor-tickets-apply  # create/link issues in GitHub
make conductor-expand         # dry-run issue enrichment (expand stage)
make conductor-expand-apply   # apply expansion + stage label transition
make conductor-expand-label-check
make conductor-execute        # dry-run execution bridge (ao spawn)
make conductor-execute-apply
make conductor-review         # dry-run DeepSeek review gate for executing items
make conductor-review-apply
make conductor-status
make conductor-ops-status     # AO session board + actionable hints
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
make conductor-tickets-reset-scan      # dry-run close scan
make conductor-tickets-reset-scan-apply
rm -rf docs/.conductor
make conductor-init
```

## Ticket labels (fixed base set)
Every created/linked issue gets:
- `conductor`
- `type:task`
- `source:roadmap`
- `repo:<repo-name>`
- `batch:<batch-id>` (when provided)
- `stage:seed`
- Optional repo defaults labels from `repo_defaults.toml`

Label assertion helper:
```bash
cd tv7-core
python3 tooling/orchestrator/verify_seed_labels.py \
  --repo TV7-Clip-Studio/tv7-core \
  --issue <issue-number-or-url> \
  --target-repo tv7-core \
  --batch-id <batch-id>
```

## Scope Filters
Use any combination of:
- `CONDUCTOR_TICKET_REPO=tv7-...`
- `CONDUCTOR_TICKET_ROADMAP=docs/roadmaps/<repo-roadmap>.md`
- `CONDUCTOR_TICKET_ITEM_PREFIX=<REPO-BATCH|REPO-BATCH-EPIC>`

Examples:
```bash
cd tv7-core
make conductor-tickets-apply CONDUCTOR_TICKET_REPO=tv7-fastapi-backend
make conductor-tickets-apply CONDUCTOR_TICKET_ROADMAP=docs/roadmaps/tv7-fastapi-backend-roadmap.md
make conductor-tickets-apply CONDUCTOR_TICKET_ITEM_PREFIX=PY-A01-02
```

## Notes
- `make conductor-run` executes `plan` then `tickets` in one command.
- `CONDUCTOR_RUN_FLAGS` is a direct passthrough to `tooling/conductor_run.py`.
- `CONDUCTOR_ROADMAP_FILE` maps directly to `--roadmap-file` in `conductor-run`.
- Assessment is disabled by default in `conductor-run`; enable with `CONDUCTOR_ASSESS=1`.
- `make conductor-expand` supports `CONDUCTOR_EXPAND_LIMIT`, `CONDUCTOR_EXPAND_RESUME_FROM`, and `CONDUCTOR_EXPAND_DRY_RUN_DIFF=1`.
- `make conductor-graph-plan` reads `CONDUCTOR_IDEA_FILE` (default `tv7-core/IDEA.md`) and supports `CONDUCTOR_GRAPH_HANDOFF=0` to skip expand handoff.
- `make conductor-execute` supports `CONDUCTOR_EXECUTE_LIMIT`, `CONDUCTOR_EXECUTE_RESUME_FROM`, `CONDUCTOR_EXECUTE_FORCE=1`, `CONDUCTOR_AO_COMMAND`, and optional `CONDUCTOR_EXECUTE_POLICY=<path>`.
- `make conductor-ops-status` surfaces live AO sessions plus operator hints; supports `CONDUCTOR_AO_COMMAND` and optional `CONDUCTOR_TICKET_REPO=<repo>` filter.
- `make conductor-review` supports `CONDUCTOR_REVIEW_LIMIT`, `CONDUCTOR_REVIEW_RESUME_FROM`, `CONDUCTOR_REVIEW_MAX_LOOPS`, optional `CONDUCTOR_REVIEW_POLICY`, and recommendation handling flags (`CONDUCTOR_REVIEW_HARD_ONLY` / `CONDUCTOR_REVIEW_INCLUDE_RECOMMENDATIONS`).
