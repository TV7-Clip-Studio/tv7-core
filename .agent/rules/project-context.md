---
trigger: always_on
---

# TV7 Workspace Context & Map

## 1. Governing Law
> **CRITICAL:** This agent must adhere to the global standards defined in:
> `tv7-core/docs/agent-best-practices.md`
>
> That document is the single source of truth for planning, git workflows, and security.

## 2. Repository Map (Architecture)
This workspace contains multiple integrated services. Use the correct folder names:

* **`tv7-core`**: Shared standards, docs, and roadmap governance.
    * **Roadmap**: [`tv7-core/docs/roadmaps/roadmap.md`](file:///Users/joaquinastelarra/Documents/TV7/tv7-core/docs/roadmaps/roadmap.md)
    * **Architecture**: [`tv7-core/docs/tv7_high_architecture.md`](file:///Users/joaquinastelarra/Documents/TV7/tv7-core/docs/tv7_high_architecture.md)
* **`tv7-conductor`**: Standalone Project Conductor runtime (plan/seed/expand/execute/review).
* **`tv7-studio`** (The Client): React UI in a Tauri desktop shell, coordinating a local Engine child.
* **`tv7-backend`** (The Control Plane): Python/FastAPI service for identity, licensing, approved private assets, scheduling, and publishing. No media rendering.
* **`tv7-site`**: Documentation or marketing site (Astro).
* **`tv7-engine`**: Rust local compute sidecar for media ingest and rendering. No business logic.
* **`.agent/mcp`**: **Custom MCP Servers.** Local bridge for AI agents to interact with the Engine.
    * **`tv7-media-mcp`**: Rust MCP for media analysis and transform operations.

## 3. Full-Stack Workflow Rules
**Context:** Studio, Engine, and Backend share explicit API contracts.

**Rule 1: Cross-Repo Sync**: When modifying one side, **ALWAYS** check the other.
* **Modifying `tv7-backend`?** -> Check Studio's API calls and Core OpenAPI contract.
* **Modifying `tv7-studio`?** -> Verify Backend and Engine endpoints support the UI logic.

**Rule 2: Roadmap Synchronization**:
* Agents are responsible for keeping [`tv7-core/docs/roadmaps/roadmap.md`](file:///Users/joaquinastelarra/Documents/TV7/tv7-core/docs/roadmaps/roadmap.md) up to date.
* **Before starting:** Claim the task (Status: `IN_PROGRESS`).
* **After finishing:** Mark it done (Status: `DONE`) and add a multi-line status block.

**Rule 3: Symlink Coordination**:
* Product repos expose shared Core context through symlinks such as `.agent`, `docs/core`, and `Makefile.core`.
* If the Codex app file tree does not show a symlinked folder, verify with the terminal before assuming it is missing.
* Prefer repo-local shared paths (`docs/core/...`, `.agent/...`) inside a product repo; use canonical `../tv7-core/...` paths only when a symlink is missing or broken.
* See `tv7-core/docs/repos/symlink-coordination.md`.

## 4. Execution & Testing Commands
Execute commands inside the specific service directories:

### Backend (`tv7-backend`)
* **Start:** `make up` (Docker) or `make dev` (Local)
* **Test:** `make test` or `pytest`
* **Lint:** `make lint`

### Frontend (`tv7-studio`)
* **Start:** `make dev-studio` from Core for the browser UI, or `npm run desktop:build` from Studio for a macOS package.
* **Check:** `make check` from Studio (lint and browser build).

### Conductor (`tv7-conductor`)
* **Start/Status:** `make conductor-init`, `make conductor-status` (from `tv7-core` shim) or `python3 tooling/conductor.py` (inside `tv7-conductor`)
* **Tests:** `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests/orchestrator -p 'test_*.py'`

## 5. Planning Requirement
As per "Agent Best Practices," you must output a numbered **Implementation Plan**.
In that plan, explicitly list:
1.  Which folders (`tv7-*`) are affected.
2.  The cross-repo impact (e.g., "Changes in Backend require update in Studio").
3.  The test commands you will run for each folder.
