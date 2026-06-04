# TV7 Core (Shared Foundation)

`tv7-core` is the shared operating system for all `TV7-Clip-Studio` repos. It holds the canonical docs, cross-repo contracts, standards, shared tooling, templates, and governance.

## Workspace layout (required)
- Clone all repos as siblings:  
  ```
  ./TV7/
    tv7-core/
    tv7-conductor/
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

## New developer localhost flow
From a fresh sibling checkout, use `tv7-core` as the workspace entrypoint:

```
cd tv7-core
make sync
make dev-status
make dev
```

Local prerequisites:
- Docker Desktop or Docker Engine for backend Postgres/API containers.
- `lsof` for local port/process ownership checks.
- Rust/Cargo for the Axum engine.
- Node/npm for the Astro site.
- Flutter with macOS desktop support for Studio.

`make dev` starts the product services that make sense as a background local stack:
- FastAPI backend and Postgres through `tv7-fastapi-backend` Docker Compose.
- Axum engine through `tv7-axum-engine`.
- Astro site through `tv7-astro-site`.

Flutter Studio is a desktop app and stays explicit:

```
make dev-studio
```

Default local URLs:
- Backend health: `http://localhost:8000/health`
- Engine health: `http://127.0.0.1:7070/health`
- Astro site: `http://localhost:4321/`

Useful controls:
- `make dev-backend` — run the backend foreground dev command in its repo.
- `make dev-engine` — run the engine foreground dev command in its repo.
- `make dev-site` — run the Astro foreground dev server in its repo.
- `make dev-status` — check repo presence, background pids, and local health endpoints.
- `make dev-logs` — show recent background stack logs from `docs/.tmp/dev-stack/logs`.
- `make dev-stop` — stop background engine/site pids and backend Docker Compose.

The Conductor repo participates in `make sync` as a sibling repo, but it is not part of the TV7 localhost product stack.

## Mounting in other repos (symlinked)
- Ensure `tv7-core` is a sibling directory to each repo (see layout above).
- Add symlinks so shared assets are visible in each repo (tracked as links, content lives in `tv7-core`). From repo root:
  - `docs/core -> ../../tv7-core/docs` (note the extra `..` because the link lives inside `docs/`)
  - `Makefile.core -> ../tv7-core/tooling/Makefile.core`
  - `.agent -> ../tv7-core/.agent`
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
- `repos/` — repo-scoped docs promoted to core (e.g., Flutter/FastAPI architecture, integration notes, runbooks).
- `contracts/` — cross-repo interface artifacts (e.g., OpenAPI exports).
- `tooling/` — cross-repo Make targets and scripts (lint-all, format-all, bootstrap).
- `templates/` — shared scaffolds (Rust/FastAPI/Flutter/Astro starters, CI snippets).
- `standards/` — naming, repo structure, versioning rules, changelog policy, security guidelines.
- `meta/` — ADRs, decision log, and the Arch Agent directive.

## Keep out
- Local machine notes, personal scratch files, and transient drafts.
- Generated binaries or heavyweight artifacts not needed for collaboration.

## Reusable CI/automation
- AI code review (DeepSeek): see `docs/ai-code-review.md` for how to wire it into any TV7 repo.

See `meta/ARCH_AGENT_DIRECTIVE.md` for the full governance rules.


## Makefile targets
- `make status` — show git status for all tracked repos.
- `make pull-all` — pull current branch in each repo (auto-sets upstream if present).
- `make bootstrap` — clone/fix remotes and ensure sibling repos exist.
- `make sync` (`make update`) — bootstrap, pull with rebase; outputs per-repo status plus open PR number and URL for the local branch when `gh` is authenticated.
- `make install-guardrails` — install the local no-push Git hook across TV7 repos. Humans can override with `TV7_ALLOW_PUSH=1 git push`.
- `make dev` (`make dev-up`) — start backend/Postgres, engine, and site for localhost development.
- `make dev-status` — check localhost repo/process/health status.
- `make dev-stop` — stop the background localhost stack.
- `make dev-logs` — show recent localhost stack logs.
- `make dev-backend`, `make dev-engine`, `make dev-site`, `make dev-studio` — refresh one service from core, then stream its logs in the current terminal.
- `make reviews` — collect all open PR review data across TV7 repos into `docs/code-reviews/<repo>/`.
- `make set-secret` — set a GitHub Actions secret across repos via `tooling/set-secret.sh` (pass `SECRET_NAME`, `SECRET_VALUE`, and `REPOS` or `ALL`; optional `ORG`).

## Agent context loading contract
- **Architect Agent** (workspace root with all repos):
  - Reads workspace-level `.agent` (`TV7/.agent/rules/project-context.md`) and `tv7-core/docs/*`.
  - May coordinate cross-repo tasks and shared policy updates.
- **Per-repo Agent** (single repo root):
  - Reads local `.agent` symlink (`<repo>/.agent -> ../tv7-core/.agent`) and repo-local context.
  - Uses shared guardrails from core while remaining scoped to its active repository.
- **Bootstrap guarantee**:
  - `make bootstrap` and `make sync` must ensure:
    - `TV7/.agent -> tv7-core/.agent` (workspace-level)
    - `<repo>/.agent -> ../tv7-core/.agent` (repo-level for each sibling repo)
  - If `<repo>/.agent` already exists as a normal file/directory, bootstrap moves it to `<repo>/.agent.backup-<timestamp>` and then creates the symlink.


# Agent Bootstrap (human prompt)
You are now the TV7 Agent.
Determine your agent role based on the current working directory:
- If the root contains ALL TV7 repos (core, conductor, backend, astro, flutter, axum, etc.), you are the **Architect** Agent.
- If the root contains ONLY one repo (e.g., fastapi-backend, astro-site, flutter-studio, axum-engine), you are the (Backend, Site, Studio, or Engine) Agent.
- You can also be a **Code Reviewer** Agent.
- If uncertain, ask the human to clarify your role.

Before anything else, read and internalize:
TV7/.agent/rules/project-context.md (if available)
TV7/tv7-core/docs/

You MUST follow all rules defined there.
Acknowledge with your detected agent type:
“Agent {TYPE} ready. What's the task?”
