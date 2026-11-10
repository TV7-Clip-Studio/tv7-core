# TV7 Core — Shared Architecture & Contracts

`tv7-core` is the foundational operating system, contract hub, and shared developer platform for the **TV7 Clip Studio** ecosystem. It maintains canonical architecture specifications, shared OpenAPI schemas, cross-repository developer toolchains, and multi-service orchestration.

---

## 🏛️ Architecture Overview

TV7 Clip Studio is an AI-assisted video clipping and editing platform designed for content creators. The ecosystem is organized into modular services:

```
                       ┌────────────────────────┐
                       │        tv7-site        │
                       │ (Astro Marketing/Docs) │
                       └────────────────────────┘

┌────────────────────────┐                   ┌────────────────────────┐
│       tv7-studio       │                   │       tv7-backend      │
│ (Tauri / React Desktop)│ ───────────────>  │(FastAPI Control Plane) │
└───────────┬────────────┘                   └────────────────────────┘
            │                                             ▲
            ▼                                             │
┌────────────────────────┐                                │
│       tv7-engine       │                                │
│ (Rust / Axum Sidecar)  │                                │
└────────────────────────┘                                │
            ▲                                             │
            └─────────────── [ tv7-core ] ────────────────┘
                      (OpenAPI Contracts & Tooling)
```

* **`tv7-studio`**: Desktop application built with Tauri, React 19, TypeScript, and Remotion for video review, timeline trimming, and subtitle styling.
* **`tv7-engine`**: Local-first Rust media engine powered by `engine-core` (Whisper transcription, FFmpeg rendering) and `engine-service` (Axum HTTP API).
* **`tv7-backend`**: FastAPI control-plane service managing authentication, user accounts, clip metadata, and publishing schedules with PostgreSQL and SQLite.
* **`tv7-site`**: Fast, static documentation and marketing website built with Astro and Tailwind CSS.
* **`tv7-core`**: Canonical contracts, OpenAPI specifications, shared developer tooling, and workspace governance.

---

## 📁 Workspace Layout

The TV7 workspace is designed for sibling checkouts:

```text
./TV7/
  ├── tv7-core/        # Shared contracts, tooling, and architecture specs
  ├── tv7-backend/     # FastAPI control plane service
  ├── tv7-studio/      # Tauri / React desktop application
  ├── tv7-engine/      # Rust local media & Whisper processing engine
  ├── tv7-site/        # Astro marketing & documentation website
  └── tv7-conductor/   # Optional multi-repo workflow automation
```

### Shared Symlink Pattern
Sibling repositories symlink shared assets directly into their trees for zero-overhead synchronization:
* `docs/core -> ../../tv7-core/docs` (canonical contracts and ADRs)
* `Makefile.core -> ../tv7-core/tooling/Makefile.core` (standardized make targets)

---

## 🚀 Local Developer Flow

From a fresh checkout, `tv7-core` provides high-level commands to orchestrate the entire stack:

```bash
# Start the full local development stack (Backend, Engine, and Studio)
make dev-browser-up

# Check running processes and health endpoints
make dev-status

# Stop all background services
make dev-browser-stop
```

### Individual Service Endpoints
* **Backend API**: `http://localhost:8000/health` (FastAPI / Swagger docs at `/docs`)
* **Engine API**: `http://127.0.0.1:7070/health` (Rust / Axum local sidecar)
* **Studio UI**: `http://127.0.0.1:5173/` (Vite / React frontend)
* **Marketing Site**: `http://localhost:4321/` (Astro static preview)

---

## 📑 API Contracts & OpenAPI Synchronization

All inter-service API contracts are version-controlled in `tv7-core` under `docs/contracts/openapi/`:
* `docs/contracts/openapi/tv7-backend/openapi.json`: OpenAPI 3.1 specification for Backend endpoints.
* `docs/contracts/openapi/tv7-engine/openapi.json`: OpenAPI 3.1 specification for Engine media endpoints.

Tests in each service validate that runtime routes and schemas conform strictly to these contracts before release.

---

## 📄 License

TV7 Core is available under the [MIT License](LICENSE). External dependencies and sibling repositories retain their respective licenses.
