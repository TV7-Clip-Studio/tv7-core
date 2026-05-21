# Project Conductor Runbook

## Purpose
Operate Project Conductor across the TV7 workspace without losing repo boundaries.

`tv7-core` owns canonical roadmaps, governance, contracts, and compatibility Make targets.
`tv7-conductor` owns runtime code, state, policies, reports, worktree helpers, and review gates.
Product repos own their implementation, validation commands, and PRs.

## Operating Rule
Conductor creates or links issues in each target repo, not in one central queue repo.

Examples:
- `tv7-fastapi-backend` roadmap items create/link issues in `TV7-Clip-Studio/tv7-fastapi-backend`.
- `tv7-flutter-studio` roadmap items create/link issues in `TV7-Clip-Studio/tv7-flutter-studio`.
- `tv7-conductor` roadmap items create/link issues in `TV7-Clip-Studio/tv7-conductor`.
- Cross-repo items may target multiple repos, but each repo gets its own issue target and validation path.

## Roadmap Inventory
Canonical roadmap sources:

| Lane | Repo | Roadmap |
| --- | --- | --- |
| Core foundation | `tv7-core` | `docs/roadmaps/tv7-core-roadmap.md` |
| Agent orchestration | `tv7-core` | `docs/roadmaps/core/agent-orchestration-roadmap.md` |
| Conductor migration governance | `tv7-core` | `docs/roadmaps/core/project-conductor-roadmap.md` |
| Product master | `tv7-core` | `docs/roadmaps/roadmap.md` |
| Conductor runtime | `tv7-conductor` | `docs/roadmaps/tv7-conductor-roadmap.md` |
| Backend control plane | `tv7-fastapi-backend` | `../tv7-core/docs/roadmaps/tv7-fastapi-backend-roadmap.md` |
| Backend off-roadmap | `tv7-fastapi-backend` | `../tv7-core/docs/roadmaps/tv7-fastapi-backend-off-roadmap.md` |
| Flutter Studio | `tv7-flutter-studio` | `../tv7-core/docs/roadmaps/tv7-flutter-studio-roadmap.md` |
| Astro Site | `tv7-astro-site` | `../tv7-core/docs/roadmaps/tv7-astro-site-roadmap.md` |
| Axum Engine | `tv7-axum-engine` | `../tv7-core/docs/roadmaps/tv7-axum-engine-roadmap.md` |

Roadmap IDs and batch mappings are configured in `../tv7-conductor/tooling/orchestrator/roadmap_ids.toml`.
Repo defaults and validation hints are configured in `../tv7-conductor/tooling/orchestrator/repo_defaults.toml`.
Workspace paths, automation levels, validation commands, and preview commands are configured in `../tv7-conductor/tooling/orchestrator/workspace.tv7.toml`.

## State And Reports
Active runtime state lives in `tv7-conductor`:

- Runtime state: `../tv7-conductor/docs/.conductor/state.json`
- Events log: `../tv7-conductor/docs/.conductor/events.jsonl`
- Run artifacts: `../tv7-conductor/docs/.conductor/runs/`
- Reports: `../tv7-conductor/docs/.conductor/reports/`

Generated `tv7-core/docs/.conductor` state is obsolete after extraction. Core shims route runtime state to `tv7-conductor`.

## Standard Lifecycle
Default work item lifecycle:

```text
seeded -> expanded -> executing -> local_review -> pr_ready -> external_review -> integrated -> done
```

Operator meaning:
- `seeded`: issue exists or can be created with minimal deterministic body.
- `expanded`: issue has structured implementation context.
- `executing`: execution agent or human implementation is underway.
- `local_review`: repo validation/review is running before PR action.
- `pr_ready`: operator may open or update the PR.
- `external_review`: PR-stage review and CI signals are being evaluated.
- `integrated`: PR is accepted/merged or ready to mark integrated.
- `done`: roadmap item is complete and recorded.

`pr_ready` is an operator gate. Conductor reports readiness but does not open, update, merge, or deploy PRs by default.

## Automation Levels
Keep all TV7 repos at `automation_level = "plan"` until the extraction PRs merge and two clean dry-run batches pass.

Level order:

```text
observe < plan < apply < execute < review < integrate
```

Dry-run commands remain available at conservative levels.
Apply-mode commands are blocked unless a repo profile is raised deliberately:
- ticket/expand apply require `apply`
- execute apply requires `execute`
- local/external review apply requires `review`

## Operator Flow
Run from `tv7-core` for normal TV7 operation:

```bash
cd tv7-core
make conductor-init
make conductor-plan
make conductor-status
```

Before mutating GitHub, inspect the planned scope:

```bash
make conductor-tickets CONDUCTOR_TICKET_REPO=tv7-astro-site
make conductor-tickets CONDUCTOR_TICKET_ROADMAP=docs/roadmaps/tv7-astro-site-roadmap.md
make conductor-tickets CONDUCTOR_TICKET_ITEM_PREFIX=ST-A01-02
```

Seed issues only after the dry-run report is correct:

```bash
make conductor-tickets-apply CONDUCTOR_TICKET_REPO=tv7-astro-site
```

Expand issues in small batches:

```bash
make conductor-expand CONDUCTOR_TICKET_REPO=tv7-astro-site CONDUCTOR_EXPAND_LIMIT=1
make conductor-expand-apply CONDUCTOR_TICKET_REPO=tv7-astro-site CONDUCTOR_EXPAND_LIMIT=1
make conductor-expand-label-check CONDUCTOR_TICKET_REPO=tv7-astro-site
```

Execute only after expansion is clean:

```bash
make conductor-execute CONDUCTOR_TICKET_REPO=tv7-astro-site CONDUCTOR_EXECUTE_LIMIT=1
make conductor-execute-apply CONDUCTOR_TICKET_REPO=tv7-astro-site CONDUCTOR_EXECUTE_LIMIT=1
```

Run local review and worktree/preview helpers from `tv7-conductor`:

```bash
cd ../tv7-conductor
make conductor-local-review \
  CONDUCTOR_REPO=tv7-astro-site \
  CONDUCTOR_ITEM_ID=ST-A01-02-01 \
  CONDUCTOR_LOCAL_REVIEW_COMMAND="npm run build"
```

After local review passes and the item reaches `pr_ready`, the operator opens or updates the repo PR. Then run external review:

```bash
make conductor-external-review \
  CONDUCTOR_REPO=tv7-astro-site \
  CONDUCTOR_ITEM_ID=ST-A01-02-01
```

Paid/API external reviewers require explicit opt-in:

```bash
make conductor-external-review \
  CONDUCTOR_REPO=tv7-astro-site \
  CONDUCTOR_ITEM_ID=ST-A01-02-01 \
  CONDUCTOR_REVIEW_ALLOW_PAID=1
```

## Repo Lanes
Use these lanes when selecting work:

| Lane | Primary repo | Cross-repo checks | Default validation |
| --- | --- | --- | --- |
| Core governance | `tv7-core` | all repos for shared docs/tooling impact | `make conductor-shim-check` |
| Conductor runtime | `tv7-conductor` | `tv7-core` shims/runbooks | `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'` |
| Backend control plane | `tv7-fastapi-backend` | Flutter API clients and publish UX | `make lint`, `make type`, `make test` |
| Flutter Studio | `tv7-flutter-studio` | Backend API contract and Engine sidecar contract | `make check` |
| Axum Engine | `tv7-axum-engine` | Flutter local sidecar integration | `make check`, `make test` |
| Astro Site | `tv7-astro-site` | product truth from Studio/Backend/Engine | `npm run build` |

Cross-repo contract rule:
- Backend API changes require Flutter client and `tv7-core` OpenAPI contract review.
- Engine API changes require Flutter integration and local contract review.
- Studio schedule/publish changes require Backend schedule truth review.
- Site messaging must match the actual local-first/control-plane architecture.
- Conductor runtime semantics require `tv7-core` shim/runbook review.

## Worktree And Preview Flow
For human testing without disturbing the primary checkout, use `tv7-conductor`:

```bash
cd tv7-conductor
make conductor-prepare-worktree \
  CONDUCTOR_REPO=tv7-astro-site \
  CONDUCTOR_ITEM_ID=ST-A01-02-01 \
  CONDUCTOR_APPLY=1
```

Launch a preview when the repo profile has a preview command:

```bash
make conductor-launch-preview \
  CONDUCTOR_REPO=tv7-astro-site \
  CONDUCTOR_ITEM_ID=ST-A01-02-01 \
  CONDUCTOR_WORKTREE_PATH=../tv7-conductor/docs/.conductor/worktrees/tv7-astro-site/ST-A01-02-01 \
  CONDUCTOR_PREVIEW_PORT=4322 \
  CONDUCTOR_PREVIEW_COMMAND="npm run dev -- --host 127.0.0.1 --port 4322"
```

Validate the worktree:

```bash
make conductor-validate-worktree \
  CONDUCTOR_REPO=tv7-astro-site \
  CONDUCTOR_ITEM_ID=ST-A01-02-01 \
  CONDUCTOR_WORKTREE_PATH=../tv7-conductor/docs/.conductor/worktrees/tv7-astro-site/ST-A01-02-01 \
  CONDUCTOR_VALIDATION_COMMAND="npm run build"
```

Cleanup remains explicit. Follow the cleanup command printed in the generated worktree/preview report.

## Batch Flow
Use this sequence for a safe workspace batch:

1. Confirm PRs for `tv7-core` and `tv7-conductor` extraction are merged or intentionally checked out.
2. Run `make conductor-shim-check` from `tv7-core`.
3. Run `make conductor-test` from `tv7-conductor`.
4. Run `make conductor-plan` from `tv7-core`.
5. Run `make conductor-status` and inspect item counts.
6. Run scoped `make conductor-tickets` dry-runs per repo.
7. Apply tickets one repo at a time.
8. Expand one repo and one item prefix at a time.
9. Execute only expanded items.
10. Run local review before opening/updating PRs.
11. Run external review only after PRs exist.
12. Mark integrated/done only after merge and validation evidence exists.

## Cleanup And Recovery
Dry-run close scan:

```bash
cd tv7-core
make conductor-tickets-reset-scan
```

Apply close scan only after report review:

```bash
make conductor-tickets-reset-scan-apply
```

Compare old core state and active conductor state:

```bash
cd ../tv7-conductor
make conductor-state-migration-check
```

Ground-zero active state reset:

```bash
cd tv7-core
rm -rf ../tv7-conductor/docs/.conductor
make conductor-init
```

Only do this when active state is disposable or archived.

## Operator Checks
After every stage command, read the `Operator summary` block first. It includes:
- stage and mode
- outcome counts
- report paths
- risks
- next recommended action

Do not run an apply command just because the previous command exited zero. Inspect the report path printed by the dry run.
