# Tooling

Cross-repo automation and bootstrap scripts live here. Invoke via root `Makefile`.

## Root Makefile targets (run from repo root)
- `make status` - per-repo summary (branch, ahead/behind, dirty counts, last commit).
- `make pull-all` - pull current branch in each repo (auto-sets upstream if present).
- `make bootstrap` - clone/fix remotes and ensure sibling repos exist.
- `make sync` (`make update`) - bootstrap, pull with rebase, show PR URLs, infer roadmap/code focus per repo, and offer the repo operation flow.
- `make inspect REPO=tv7-backend` - local, non-mutating post-agent inspection for one repo.
- `make handoff` - update tracked active Backend/Engine/Studio handoffs from the latest sync cockpit artifact.
- `make handoff-check` - warning-only check for stale generated active handoffs.
- `make precommit-context` - local precommit context check: tooling syntax, diff whitespace, and warning-only handoff freshness.
- `make git-dev` - deprecated compatibility alias for `make sync SYNC_MODE=operate`.
- `make set-secret` - set GitHub Actions secrets across repos.
- `make batch-pr` - run checks across repos, commit changed repos, push branches, open PRs.
- `make batch-pr-dry-run` - preview branch/check/commit/push/PR actions.
- `make batch-pr-report` (`make repo-status`) - show branch/upstream/dirty/PR state.

## Project Conductor Entry Points
Conductor runtime now lives in sibling repo `tv7-conductor`.

From `tv7-core`, `make conductor-*` targets are shim entry points that execute:
- `../tv7-conductor/tooling/conductor.py`
- `../tv7-conductor/tooling/conductor_run.py`

## Conductor options
- `CONDUCTOR_REPO=../tv7-conductor`
- `CONDUCTOR_TOOLING_DIR=$(CONDUCTOR_REPO)/tooling`
- `CONDUCTOR_PLAN_ROADMAP=docs/roadmaps/<repo-roadmap>.md`
- `CONDUCTOR_ROADMAP_FILE=docs/roadmaps/<repo-roadmap>.md`
- `CONDUCTOR_TICKET_REPO=tv7-...`
- `CONDUCTOR_TICKET_ROADMAP=docs/roadmaps/<repo-roadmap>.md`
- `CONDUCTOR_TICKET_ITEM_PREFIX=<REPO-BATCH|REPO-BATCH-EPIC>`
- `CONDUCTOR_AGENT_PROFILE=local_auto_medium`
- `CONDUCTOR_BATCH_ID=<batch-id>`
- `CONDUCTOR_EXPAND_AGENT=auto|codex|gemini|none`
- `CONDUCTOR_EXECUTE_POLICY=$(CONDUCTOR_TOOLING_DIR)/orchestrator/execution_policy.toml`
- `CONDUCTOR_REVIEW_POLICY=$(CONDUCTOR_TOOLING_DIR)/orchestrator/review_policy.toml`

Per-repo seed defaults now live in:
- `../tv7-conductor/tooling/orchestrator/repo_defaults.toml`

## Examples
- `make sync`
- `SYNC_GEMINI=0 make sync` to skip the Gemini planner pass.
- `SYNC_INTERACTIVE=0 make sync` for CI-style status output only.
- `make inspect REPO=tv7-backend` after a repo agent reports completion, before the next full sync/handoff cycle.
- `make handoff` to refresh `docs/handoffs/active/{backend,engine,studio}.md`.
- `make handoff HANDOFF_REPO=tv7-engine` to refresh one active handoff.
- `make handoff HANDOFF_REPO=tv7-backend HANDOFF_VERBOSE=1` to print semantic detector details.
- `make precommit-context` before committing Core orchestration/docs changes.
- `make conductor-status`
- `make conductor-plan CONDUCTOR_PLAN_ROADMAP=docs/roadmaps/tv7-site-roadmap.md`
- `make conductor-expand-apply CONDUCTOR_TICKET_REPO=tv7-site CONDUCTOR_TICKET_ITEM_PREFIX=SI-A01-02-01 CONDUCTOR_EXPAND_LIMIT=1 CONDUCTOR_EXPAND_AGENT=gemini`
- `make conductor-execute-apply CONDUCTOR_TICKET_REPO=tv7-site CONDUCTOR_TICKET_ITEM_PREFIX=SI-A01-02-01 CONDUCTOR_EXECUTE_LIMIT=1`

## Legacy note
`orchestrator-*` targets are deprecated compatibility aliases. Use `conductor-*` only.
