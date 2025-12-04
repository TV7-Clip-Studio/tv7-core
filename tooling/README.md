# Tooling

Cross-repo automation and bootstrap scripts live here. Invoke everything via the root `Makefile` (no per-folder make invocations). Examples:
- Bootstrap scripts (dev env setup, shared deps).
- Cross-repo helpers (lint-all, format-all, update-submodules).
- Shared CI snippets that apply everywhere.

Exclude: language- or repo-specific scripts; keep those in the owning repo.
