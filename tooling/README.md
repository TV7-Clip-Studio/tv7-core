# Tooling

Cross-repo automation and bootstrap scripts live here. Invoke via root `Makefile`.

## Root Makefile targets (run from repo root)
- `make status` - per-repo summary (branch, ahead/behind, dirty counts, last commit).
- `make pull-all` - pull current branch in each repo (auto-sets upstream if present).
- `make bootstrap` - clone/fix remotes and ensure sibling repos exist.
- `make sync` (`make update`) - bootstrap, pull with rebase; outputs per-repo status.
- `make set-secret` - set GitHub Actions secrets across repos.
- `make batch-pr` - run checks across repos, commit changed repos, push branches, open PRs.
- `make batch-pr-dry-run` - preview branch/check/commit/push/PR actions.
- `make batch-pr-report` (`make repo-status`) - show branch/upstream/dirty/PR state.

## Project Conductor targets
- `make conductor-init` - initialize Conductor runtime state (`docs/.conductor`).
- `make conductor-plan` - parse roadmap tasks into work items.
- `make conductor-graph-plan` / `make conductor-graph-plan-apply` - IDEA ingestion, queue emission, and optional expand handoff.
- `make conductor-profiles` - list available ticket assessment profiles.
- `make conductor-tickets` / `make conductor-tickets-apply` - dry-run/apply issue sync.
- `make conductor-tickets-gemini` / `make conductor-tickets-gemini-apply` - explicit Gemini profile.
- `make conductor-tickets-codex` / `make conductor-tickets-codex-apply` - explicit Codex profile.
- `make conductor-expand` / `make conductor-expand-apply` - dry-run/apply expand-stage issue enrichment.
- `make conductor-expand-label-check` / `make conductor-expand-label-check-apply` - verify/fix stage label consistency.
- `make conductor-execute` / `make conductor-execute-apply` - dry-run/apply execution bridge (`ao spawn <repo> <item_id>`).
- `make conductor-review` / `make conductor-review-apply` - dry-run/apply DeepSeek review gate and stage transitions.
- `make conductor-tickets-reset` / `make conductor-tickets-reset-apply` - dry-run/apply linked issue closure.
- `make conductor-tickets-reset-scan` / `make conductor-tickets-reset-scan-apply` - close all linked open issues by scan.
- `make conductor-run` - one-shot flow (`plan` + `tickets`).
- `make conductor-status` / `make conductor-events` - inspect Conductor state and events.
- `make conductor-ops-status` - show live AO spawned sessions with actionable operator hints.

## Conductor options
- `CONDUCTOR_PLAN_ROADMAP=docs/roadmaps/<repo-roadmap>.md`
- `CONDUCTOR_ROADMAP_FILE=docs/roadmaps/<repo-roadmap>.md` (for `conductor-run --roadmap-file`)
- `CONDUCTOR_TICKET_REPO=tv7-...`
- `CONDUCTOR_TICKET_ROADMAP=docs/roadmaps/<repo-roadmap>.md`
- `CONDUCTOR_TICKET_ITEM_PREFIX=<REPO-BATCH|REPO-BATCH-EPIC>`
- `CONDUCTOR_AGENT_PROFILE=local_auto_medium` (default)
- `TV7_ASSESS_PROVIDER=codex|gemini` (optional override when profile uses `assess_agent=auto`)
- `CONDUCTOR_BATCH_ID=<batch-id>`
- `CONDUCTOR_ASSESS=1` (off by default in `conductor-run`)
- `CONDUCTOR_DRY_RUN=1`
- `CONDUCTOR_RUN_FLAGS="--roadmap-file=docs/roadmaps/<repo-roadmap>.md --repo tv7-..."`
- `CONDUCTOR_EXPAND_LIMIT=1`
- `CONDUCTOR_EXPAND_RESUME_FROM=CO-C01-04-01`
- `CONDUCTOR_EXPAND_DRY_RUN_DIFF=1`
- `CONDUCTOR_EXPAND_STRICT=1`
- `CONDUCTOR_EXPAND_AGENT=auto|codex|gemini|none` (default: `auto`)
- `CONDUCTOR_EXPAND_MODEL=<provider-model-name>` (optional)
- `CONDUCTOR_EXPAND_REASONING=low|medium|high` (optional)
- `CONDUCTOR_EXPAND_PERSONALITY=<provider-personality>` (optional)
- `TV7_EXPAND_PROVIDER=codex|gemini` (optional override when `CONDUCTOR_EXPAND_AGENT=auto`)
- `CONDUCTOR_EXECUTE_LIMIT=1`
- `CONDUCTOR_EXECUTE_RESUME_FROM=CO-C01-06-01`
- `CONDUCTOR_EXECUTE_FORCE=1`
- `CONDUCTOR_AO_COMMAND=ao`
- `CONDUCTOR_EXECUTE_POLICY=tooling/orchestrator/execution_policy.toml`
- `CONDUCTOR_REVIEW_LIMIT=1`
- `CONDUCTOR_REVIEW_RESUME_FROM=CO-C01-07-01`
- `CONDUCTOR_REVIEW_MAX_LOOPS=2`
- `CONDUCTOR_REVIEW_POLICY=tooling/orchestrator/review_policy.toml`
- `CONDUCTOR_REVIEW_HARD_ONLY=1`
- `CONDUCTOR_REVIEW_INCLUDE_RECOMMENDATIONS=1`
- `CONDUCTOR_IDEA_FILE=IDEA.md`
- `CONDUCTOR_GRAPH_DEFAULT_REPO=tv7-core`
- `CONDUCTOR_GRAPH_ROADMAP_CODE=CO`
- `CONDUCTOR_GRAPH_BATCH_CODE=C01`
- `CONDUCTOR_GRAPH_DEFAULT_EPIC=01`
- `CONDUCTOR_GRAPH_HANDOFF=0` (skip expand handoff in graph-plan)

Per-repo seed defaults are configured in:
- `tooling/orchestrator/repo_defaults.toml`

## Examples
- Single repo:
  - `make conductor-run CONDUCTOR_TICKET_REPO=tv7-astro-site`
- Force local automated assessment for tickets:
  - `make conductor-tickets-apply CONDUCTOR_AGENT_PROFILE=local_auto_medium`
- One-ticket expand dry-run with diff artifact:
  - `make conductor-expand CONDUCTOR_TICKET_REPO=tv7-core CONDUCTOR_TICKET_ITEM_PREFIX=CO-C01-04-01 CONDUCTOR_EXPAND_LIMIT=1 CONDUCTOR_EXPAND_DRY_RUN_DIFF=1`
- One-ticket expand apply using Codex planner generation:
  - `make conductor-expand-apply CONDUCTOR_TICKET_REPO=tv7-astro-site CONDUCTOR_TICKET_ITEM_PREFIX=ST-A01-02-01 CONDUCTOR_EXPAND_LIMIT=1 CONDUCTOR_EXPAND_AGENT=codex`
- One-ticket expand apply using Gemini planner generation:
  - `make conductor-expand-apply CONDUCTOR_TICKET_REPO=tv7-astro-site CONDUCTOR_TICKET_ITEM_PREFIX=ST-A01-02-01 CONDUCTOR_EXPAND_LIMIT=1 CONDUCTOR_EXPAND_AGENT=gemini`

Notes:
- `CONDUCTOR_EXPAND_AGENT=gemini` now attempts a direct non-interactive Gemini CLI run.
- `.pending.json` files in `docs/.conductor/reports/expansions/` are fallback artifacts created only when automated Gemini execution fails.
- IDEA dry-run with queue-only (no expand handoff):
  - `make conductor-graph-plan CONDUCTOR_IDEA_FILE=IDEA.md CONDUCTOR_GRAPH_HANDOFF=0`
- Execute bridge for one target:
  - `make conductor-execute CONDUCTOR_TICKET_REPO=tv7-core CONDUCTOR_TICKET_ITEM_PREFIX=CO-C01-06-01 CONDUCTOR_EXECUTE_LIMIT=1`
- Review gate for one target (hard-only mode):
  - `make conductor-review CONDUCTOR_TICKET_REPO=tv7-core CONDUCTOR_TICKET_ITEM_PREFIX=CO-C01-07-01 CONDUCTOR_REVIEW_LIMIT=1 CONDUCTOR_REVIEW_HARD_ONLY=1`
- Single roadmap file:
  - `make conductor-run CONDUCTOR_ROADMAP_FILE=docs/roadmaps/tv7-astro-site-roadmap.md`
- All repos:
  - `make conductor-run`
- Ground-zero cleanup:
  - `make conductor-tickets-reset-scan`
  - `make conductor-tickets-reset-scan-apply`
  - `rm -rf docs/.conductor`
  - `make conductor-init`

## Labels applied to issues
Conductor applies a fixed base label set:
- `conductor`
- `type:task`
- `source:roadmap`

Dynamic labels are added per ticket:
- `repo:<repo-name>`
- `batch:<batch-id>` (if set)
- `stage:seed`
- plus optional repo defaults labels from `repo_defaults.toml`

Optional label assertion helper:
- `python3 tooling/orchestrator/verify_seed_labels.py --repo TV7-Clip-Studio/tv7-core --issue 123 --target-repo tv7-core --batch-id <batch>`

## Legacy note
`make orchestrator-*` targets remain for backward compatibility, but new usage should be `make conductor-*`.
