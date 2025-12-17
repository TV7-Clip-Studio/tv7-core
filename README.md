# TV7 Core (Shared Foundation)

`tv7-core` is the shared operating system for all `TV7-Clip-Studio` repos. It holds only cross-repo, foundational assets: system architecture, standards, shared tooling, templates, and governance. Anything that is repo-specific stays in that repo.

## Workspace layout (required)
- Clone all repos as siblings:  
  ```
  ./TV7/
    tv7-core/
    tv7-fastapi-backend/
    tv7-astro-site/
    tv7-flutter-studio/
    tv7-axum-engine/
  ```
- Supported environments: macOS, Linux, WSL2/Ubuntu. Native Windows is not supported for symlinks.

## Why symlinks (not submodules)
- You control the workspace layout; submodule pinning adds friction without a benefit here.
- Symlinks keep shared docs/tooling live and avoid detached SHA churn.
- Simpler mental model: edit through the link, commit in `tv7-core`, done.

## Mounting in other repos (symlinked)
- Ensure `tv7-core` is a sibling directory to each repo (see layout above).
- Add symlinks so shared assets are visible in each repo (tracked as links, content lives in `tv7-core`). From repo root:
  - `docs/core -> ../../tv7-core/docs` (note the extra `..` because the link lives inside `docs/`)
  - `Makefile.core -> ../tv7-core/tooling/Makefile.core`
- Bootstrap (`make bootstrap` or `make sync`) will ensure these symlinks exist if the repo is present.
- Example (from inside a repo, e.g., `tv7-fastapi-backend`):
  ```
  ln -s ../tv7-core/docs docs/core
  ln -s ../tv7-core/docs/high-architecture docs/high-architecture
  ln -s ../tv7-core/docs/roadmaps docs/roadmaps
  ln -s ../tv7-core/tooling/Makefile.core Makefile.core
  ```
  - Bootstrap ensures symlinks; see `tooling/bootstrap-repos.sh` for details.

## Editing workflow (day-to-day)
- Open shared docs/tooling through the symlink in the repo you are working in.
- Changes appear in `tv7-core` (the linked content), not the downstream repo.
- Commit/push those changes from `tv7-core`.
- Optionally add helper targets in downstream repos:
  - `core-status`: `cd ../tv7-core && git status`
  - `core-commit`: `cd ../tv7-core && git commit -am "Update from $(shell basename $$PWD)"`

## What belongs here (rule-of-thumb)
- If removing `tv7-core` would break all repos → it lives here.
- If it helps only one repo/feature/tech stack → keep it local to that repo (e.g., `docs-local/`).

## Layout (intended)
- `architecture/` — system-level docs only (e.g., `tv7_high_architecture.md`, engine/backend control-plane overviews).
- `tooling/` — cross-repo Make targets and scripts (lint-all, format-all, bootstrap).
- `templates/` — shared scaffolds (Rust/FastAPI/Flutter/Astro starters, CI snippets).
- `standards/` — naming, repo structure, versioning rules, changelog policy, security guidelines.
- `meta/` — ADRs, decision log, and the Arch Agent directive.

## Keep out
- Repo-specific docs (feature plans, implementation notes, TODOs) → live in that repo under `docs-local/`.
- Tech-specific scripts that don’t apply across repos (only Flutter/Python/Rust/Astro).
- Drafts/experiments meant for a single module.

## Reusable CI/automation
- AI code review (DeepSeek): see `docs/ai-code-review.md` for how to wire it into any TV7 repo.

See `meta/ARCH_AGENT_DIRECTIVE.md` for the full governance rules.


## Makefile targets
- `make status` — show git status for all tracked repos.
- `make pull-all` — pull current branch in each repo (auto-sets upstream if present).
- `make bootstrap` — clone/fix remotes and ensure sibling repos exist.
- `make sync` (`make update`) — bootstrap, pull with rebase; outputs per-repo status.
- `make set-secret` — set a GitHub Actions secret across repos via `tooling/set-secret.sh` (pass `SECRET_NAME`, `SECRET_VALUE`, and `REPOS` or `ALL`; optional `ORG`).


# Agent Bootstrap (human prompt)
You are now the TV7 Agent.
Determine your agent role based on the current working directory:
- If the root contains ALL TV7 repos (core, backend, astro, flutter, axum, etc.), you are the **Architect** Agent.
- If the root contains ONLY one repo (e.g., fastapi-backend, astro-site, flutter-studio, axum-engine), you are the (Backend, Site, Studio, or Engine) Agent.
- You can also be a **Code Reviewer** Agent.
- If uncertain, ask the human to clarify your role.

Before anything else, read and internalize:
TV7/.agent/rules/project-context.md (if available)
TV7/tv7-core/docs/

You MUST follow all rules defined there.
Acknowledge with your detected agent type:
“Agent {TYPE} ready”
