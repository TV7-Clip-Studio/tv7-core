# Tooling

Cross-repo automation and bootstrap scripts live here. Invoke everything via the root `Makefile` (no per-folder make invocations). Examples:
- Bootstrap scripts (dev env setup, shared deps).
- Cross-repo helpers (lint-all, format-all).
- Shared CI snippets that apply everywhere.

Exclude: language- or repo-specific scripts; keep those in the owning repo.

## Root Makefile targets (run from repo root)
- `make status` — per-repo summary (branch, ahead/behind, dirty counts, last commit).
- `make pull-all` — pull current branch in each repo (auto-sets upstream if present).
- `make bootstrap` — clone/fix remotes and ensure sibling repos exist.
- `make sync` (`make update`) — bootstrap, pull with rebase; outputs per-repo status.
- `make set-secret` — set a GitHub Actions secret across repos via `tooling/set-secret.sh` (pass `SECRET_NAME`, `SECRET_VALUE`, and `REPOS` or `ALL`; optional `ORG`).
- `make batch-pr` — run checks across all repos, commit changed repos, push branches, and open PRs by default.
- `make batch-pr-dry-run` — preview branch/check/commit/push/PR actions without writing changes.
- `make batch-pr-report` (`make repo-status`) — show branch/upstream/dirty/PR state across repos.

## Batch PR config
- `tooling/repos-checks.conf` controls per-repo base branch and check command.
