# Tooling

Cross-repo automation and bootstrap scripts live here. Invoke everything via the root `Makefile` (no per-folder make invocations). Examples:
- Bootstrap scripts (dev env setup, shared deps).
- Cross-repo helpers (lint-all, format-all, update-submodules).
- Shared CI snippets that apply everywhere.

Exclude: language- or repo-specific scripts; keep those in the owning repo.

## Root Makefile targets (run from repo root)
- `make status` — per-repo summary (branch, ahead/behind, dirty counts, submodule state, last commit).
- `make pull-all` — pull current branch in each repo (auto-sets upstream if present).
- `make submodules-init` — init/update submodules in each repo.
- `make submodules-update` — update `00-tv7-core` submodule to remote in each repo.
- `make bootstrap` — clone/fix remotes and ensure `00-tv7-core` exists in sibling repos.
- `make sync` (`make update`) — bootstrap, pull with rebase, update submodule; outputs per-repo status.
- `make set-secret` — set a GitHub Actions secret across repos via `tooling/set-secret.sh` (pass `SECRET_NAME`, `SECRET_VALUE`, and `REPOS` or `ALL`; optional `ORG`).
