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

* **`tv7-core`**: Shared standards, docs, and reusable workflows.
    * **Roadmap**: [`tv7-core/docs/roadmaps/roadmap.md`](file:///Users/joaquinastelarra/Documents/TV7/tv7-core/docs/roadmaps/roadmap.md)
    * **Architecture**: [`tv7-core/docs/tv7_high_architecture.md`](file:///Users/joaquinastelarra/Documents/TV7/tv7-core/docs/tv7_high_architecture.md)
* **`tv7-flutter-studio`** (The Client): Flutter Desktop application. Primary UI, manages local Engine processes.
* **`tv7-fastapi-backend`** (The Control Plane): Python/FastAPI backend service. **Auth, Billing, Scheduling ONLY.** No media processing.
* **`tv7-astro-site`**: Documentation or marketing site (Astro).
* **`tv7-axum-engine`**: High-performance Rust components. **Local Compute Sidecar.** Transcoding, AI, Media. No business logic.
* **`.agent/mcp`**: **Custom MCP Servers.** Local bridge for AI agents to interact with the Engine.
    * **`tv7-media-mcp`**: Rust MCP for media analysis and transform operations.

## 3. Full-Stack Workflow Rules
**Context:** The system relies on tight integration between the Flutter Client and FastAPI Backend.

**Rule 1: Cross-Repo Sync**: When modifying one side, **ALWAYS** check the other.
* **Modifying `tv7-fastapi-backend`?** -> Check if `tv7-flutter-studio` models/API calls need updates.
* **Modifying `tv7-flutter-studio`?** -> Verify backend endpoints support the new UI logic.

**Rule 2: Roadmap Synchronization**:
* Agents are responsible for keeping [`tv7-core/docs/roadmaps/roadmap.md`](file:///Users/joaquinastelarra/Documents/TV7/tv7-core/docs/roadmaps/roadmap.md) up to date.
* **Before starting:** Claim the task (Status: `IN_PROGRESS`).
* **After finishing:** Mark it done (Status: `DONE`) and add a multi-line status block.

## 4. Execution & Testing Commands
Execute commands inside the specific service directories:

### Backend (`tv7-fastapi-backend`)
* **Start:** `make up` (Docker) or `make dev` (Local)
* **Test:** `make test` or `pytest`
* **Lint:** `make lint`

### Frontend (`tv7-flutter-studio`)
* **Start:** `make run-desktop` (macOS) or `make run FLAVOR=dev`
* **Test:** `flutter test`
* **Lint:** `flutter analyze`

## 5. Planning Requirement
As per "Agent Best Practices," you must output a numbered **Implementation Plan**.
In that plan, explicitly list:
1.  Which folders (`tv7-*`) are affected.
2.  The cross-repo impact (e.g., "Changes in Backend require update in Flutter").
3.  The test commands you will run for each folder.
