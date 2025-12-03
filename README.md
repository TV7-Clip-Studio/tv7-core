# TV7 Core (Shared Foundation)

`tv7-core` is the shared operating system for all `TV7-Clip-Studio` repos. It holds only cross-repo, foundational assets: system architecture, standards, shared tooling, templates, and governance. Anything that is repo-specific stays in that repo.

## Mounting in other repos
- Add `tv7-core` as a submodule under `00-tv7-core/` in every repo (visibly distinct and always present).  
  `git submodule add git@github.com:TV7-Clip-Studio/tv7-core.git 00-tv7-core`
- Clone with `--recurse-submodules`, or run `git submodule update --init --recursive` after clone.
- After changing `tv7-core`, bump the submodule pointer in each repo:  
  `git submodule update --remote 00-tv7-core && git add 00-tv7-core && git commit -m "Bump tv7-core docs/tooling"`

## What belongs here (rule-of-thumb)
- If removing `tv7-core` would break all repos → it lives here.
- If it helps only one repo/feature/tech stack → keep it local to that repo (e.g., `docs-local/`).

## Layout (intended)
- `architecture/` — system-level docs only (e.g., `tv7_high_architecture.md`, engine/backend control-plane overviews).
- `tooling/` — cross-repo Make targets and scripts (lint-all, format-all, update-submodules, bootstrap).
- `templates/` — shared scaffolds (Rust/FastAPI/Flutter/Astro starters, CI snippets).
- `standards/` — naming, repo structure, versioning rules, changelog policy, security guidelines.
- `meta/` — ADRs, decision log, and the Arch Agent directive.

## Keep out
- Repo-specific docs (feature plans, implementation notes, TODOs) → live in that repo under `docs-local/`.
- Tech-specific scripts that don’t apply across repos (only Flutter/Python/Rust/Astro).
- Drafts/experiments meant for a single module.

See `meta/ARCH_AGENT_DIRECTIVE.md` for the full governance rules.***
