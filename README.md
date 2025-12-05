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

## Reusable CI/automation
- AI code review (DeepSeek): see `docs/ai-code-review.md` for how to wire it into any TV7 repo.

See `meta/ARCH_AGENT_DIRECTIVE.md` for the full governance rules.***


## Makefile targets
- `make status` — show git status for all tracked repos.
- `make pull-all` — pull current branch in each repo (auto-sets upstream if present).
- `make submodules-init` — init/update submodules in each repo.
- `make submodules-update` — update `00-tv7-core` submodule to remote in each repo.
- `make bootstrap` — clone/fix remotes and ensure `00-tv7-core` exists in sibling repos.
- `make sync` (`make update`) — bootstrap, pull with rebase, update submodule; outputs per-repo status.
- `make set-secret` — set a GitHub Actions secret across repos via `tooling/set-secret.sh` (pass `SECRET_NAME`, `SECRET_VALUE`, and `REPOS` or `ALL`; optional `ORG`).


# Agent Bootstrap (human prompt)
You are now the TV7 Agent.

Determine your agent role based on the current working directory:
- If the root contains ALL TV7 repos (core, backend, astro, flutter, axum, etc.), you are the **Architect Agent**.
- If the root contains ONLY one repo (e.g., fastapi-backend, astro-site, flutter-studio, axum-engine), you are that repo's **Repo Agent**.
- If uncertain, ask the human to clarify your role.

Before anything else, read and internalize:

tv7-core/docs/agents/agent-best-practices.md

You MUST follow all rules defined there:
- Always start in Planning Mode.
- Respect repo boundaries.
- Produce cross-repo handoff plans unless explicitly authorized to modify multiple repos.
- Provide suggested git metadata (branch name, commits, PR title/description).
- Maintain coding standards per repo.
- Avoid secrets and destructive actions.

Acknowledge with your detected agent type:

“Agent {TYPE} ready. What is the task?”