# Arch Agent Directive: TV7-Core Governance

Goal: Keep `tv7-core` a clean, cross-repo foundation—never a dumping ground.

Mounting: Every repo mounts `tv7-core` as `00-tv7-core/` (submodule). Update with `git submodule update --remote 00-tv7-core && git add 00-tv7-core`.

Golden rule: If removing `tv7-core` would break all repos, it belongs here. If it affects only one repo/feature/tech stack, keep it local (e.g., `docs-local/` in that repo).

Must include (cross-repo only):
- System/architecture docs (e.g., `tv7_high_architecture.md`, engine/backend/control-plane overviews).
- Shared tooling (Makefiles, lint-all/format-all/update-submodules, bootstrap scripts).
- Templates usable by multiple repos (Rust/FastAPI/Flutter/Astro, CI snippets).
- Standards: naming, repo layout, versioning, changelog policy, security guidelines.
- Meta: ADRs, decision logs, cross-repo roadmaps.

Must NOT include:
- Repo-specific docs, feature notes, or TODOs (keep in that repo’s `docs-local/`).
- Tech-specific scripts that don’t apply to all repos.
- Experimental drafts for a single module.

Promotion rule:
- Promote only if it impacts 3+ repos or defines global standards.
- Otherwise reject/relocate to the owning repo.

Scope check to enforce:
- Ask: “Does this impact 3+ repos?” If no → keep it local.
- Ask: “Is it system-wide or shared tooling/standards?” If no → keep it local.

On change:
- Update `00-tv7-core` in each repo; communicate cross-repo changes in release/ADR logs.
