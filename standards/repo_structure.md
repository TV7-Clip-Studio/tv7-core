# Repo Structure Standards

Submodule
- Mount `tv7-core` as `00-tv7-core/` in every repo. Required for docs, standards, and shared tooling.

Docs
- Cross-repo/system docs → `00-tv7-core/`.
- Repo-specific docs/notes/TODOs → `docs-local/` in that repo (do not sync to `tv7-core`).

Top-level hygiene
- Keep repo roots lean: source, tests, infra (docker, scripts), `docs-local/`, `00-tv7-core/`.
- Avoid duplicating shared configs; prefer shared templates from `00-tv7-core/templates/`.

Submodules/updates
- After edits to `tv7-core`, run `git submodule update --remote 00-tv7-core && git add 00-tv7-core && git commit -m "Bump tv7-core"`.
