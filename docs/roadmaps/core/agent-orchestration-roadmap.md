# TV7 Core Agent Orchestration Roadmap

## Purpose
Coordinate TV7 agent orchestration so Architect and per-repo agents load the right shared context, repo-local skills, and MCP tools with predictable behavior.

## Scope
- `.agent` shared guardrails and workflows (symlink-first strategy).
- `.codex/skills` repo-local specialization.
- MCP topology split between global and repo/domain-specific servers.

## Phase 0: Decisions Captured
- [x] Capture initial orchestration decisions for this iteration.
    **COMPLETED** | Architect Agent | 2026-02-15 18:53
    - **NOTE**: Confirmed strategy is `.agent` symlinks across repos, hybrid MCP topology (global + per-repo), and no CI hard-gate yet.

## Phase 1: Filesystem and Context Loading
- [x] Standardize `.agent` symlink visibility for each repo (`tv7-fastapi-backend`, `tv7-flutter-studio`, `tv7-astro-site`, `tv7-axum-engine`).
    **COMPLETED** | Architect Agent | 2026-02-15 19:01
    - **NOTE**: Updated `tooling/bootstrap-repos.sh` so `make bootstrap`/`make sync` enforce `<repo>/.agent -> ../tv7-core/.agent` while preserving `TV7/.agent -> tv7-core/.agent`; if `.agent` exists as non-symlink it is auto-migrated to `.agent.backup-<timestamp>`.
- [x] Document role-based context loading contract (Architect loads workspace-level context; per-repo agent loads repo-local context + shared `.agent`).
    **COMPLETED** | Architect Agent | 2026-02-15 19:01
    - **CROSS-AGENT-NOTES**: Required by all agent types.
    - **NOTE**: Added contract and bootstrap guarantees to `README.md`.

## Phase 2: Skill Layering
- [x] Define skill ownership boundaries: shared skills in `.agent/skills`, repo execution skills in `<repo>/.codex/skills`.
    **COMPLETED** | Architect Agent | 2026-02-15 19:39
    - **NOTE**: Added repo-specific `AGENTS.md` files (core/backend/studio/site/engine) explicitly documenting skill boundaries and shared-vs-local prompt behavior, with a common system-flow read order.
- [x] Create initial prompt templates for Architect and each repo agent, and wire `AGENTS.md` to those prompts.
    **COMPLETED** | Architect Agent | 2026-02-15 19:48
    - **NOTE**: Added `.agent/prompts/{architect,backend,studio,site,engine}-initial-prompt.md` plus `.agent/prompts/README.md`, and updated all repo `AGENTS.md` files to load their role prompt first.
- [ ] Add a lightweight skill index doc mapping shared vs repo-local skills and intended triggers.
    **BACKLOG** | Architect Agent | 2026-02-15 18:53

## Phase 3: MCP Topology
- [ ] Create MCP namespace convention for global and repo-scoped servers under `.agent/mcp`.
    **BACKLOG** | Architect Agent | 2026-02-15 18:53
    - **NOTE**: Proposed structure: `mcp/global/*` and `mcp/repos/<repo>/*`.
- [ ] Define MCP loading policy by role and working directory (Architect vs per-repo agent).
    **BACKLOG** | Architect Agent | 2026-02-15 18:53
    - **CROSS-AGENT-NOTES**: Avoid loading unrelated heavy MCPs in per-repo sessions.

## Phase 4: Validation (No CI Gate Yet)
- [x] Automate commit/PR metadata flow in `tooling/batch-pr.sh` (task id, title, and description).
    **COMPLETED** | Architect Agent | 2026-02-15 20:29
    - **NOTE**: Added support for `TASK_ID`, `CHANGE_TITLE`, `PR_TITLE`, `PR_BODY`, and `PR_BODY_FILE`; PR creation now uses explicit title + body (with default generated description when not supplied).
- [ ] Add a manual validation checklist to verify symlink health, skill discoverability, and MCP reachability per repo.
    **BACKLOG** | Architect Agent | 2026-02-15 18:53
    - **NOTE**: Keep this as runbook/manual checks until CI enforcement phase.
- [ ] Track baseline orchestration metrics (bootstrap success rate, manual context-fix rate, review skip/tooling-failure rate).
    **BACKLOG** | Architect Agent | 2026-02-15 18:53
    - **NOTE**: Use these to decide when to introduce CI enforcement.
