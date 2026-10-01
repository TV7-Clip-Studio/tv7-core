# TV7 Core Architecture (Shared Foundation)

## Purpose
- Single source for cross-repo standards, architecture docs, templates, and shared tooling.
- Lives alongside product repos and is symlinked in where needed; no runtime services here.

## What Core Provides
- Architecture references: high-level system view plus per-surface overviews.
- Standards: agent rules, governance, naming/structure guidance.
- Tooling: shared Make targets/scripts for bootstrap, lint/test orchestration, CI snippets.
- Templates: shared editor settings and reusable scaffolding.

## Boundaries
- No product/runtime code; no service configs.
- Repo-specific docs or feature notes stay in that repo (`docs-local/` there), not here.
- Core changes should remain backward-compatible for sibling repos that symlink these assets.
