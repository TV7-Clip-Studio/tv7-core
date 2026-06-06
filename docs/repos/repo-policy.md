# Multi-Repo Workflow Policy

This policy defines the default branch/check/commit/PR workflow across TV7 repositories.

## Scope
- `tv7-core`
- `tv7-engine`
- `tv7-backend`
- `tv7-studio`
- `tv7-site`

## Branching
- Never open PRs from `main`/`master`.
- Default automation branch prefix: `codex/batch-<repo>-<timestamp>`.
- Reuse an existing non-main branch if already checked out.

## Checks
- Checks run in all repos on every batch run.
- Repo command map is defined in `tooling/repos-checks.conf`.
- Default commands:
  - `tv7-core`: no hard check gate (docs-only allowed)
  - `tv7-engine`: `cargo check`
  - `tv7-backend`: `make test`
  - `tv7-studio`: `make check`
  - `tv7-site`: `npm run build`

## Commit Rules
- Commit only when checks pass for that repo.
- Skip commit if there are no staged changes.
- Default batch commit message: `chore: batch update <timestamp>`.

## PR Rules
- Push and open PRs by default when a repo has a new commit.
- Base branch defaults are in `tooling/repos-checks.conf` (currently `main`).
- If `gh` or auth is unavailable, the run reports a clear failure for PR creation.

## Command Surface
- `make batch-pr` - full run, push + PR by default.
- `make batch-pr-dry-run` - no writes, preview actions.
- `make batch-pr-report` - current cross-repo dashboard.

