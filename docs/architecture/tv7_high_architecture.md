# TV7 High Architecture Behavior (Revised)

## Overview
TV7 is a local-first video clipping and repurposing application consisting of a desktop/mobile studio, a local compute engine, and a cloud control plane.

## 1. TV7 Studio
*See [Studio Architecture](studio_architecture.md) for details.*

Primary user interface for the whole workflow. Manages the local Engine process and connects to the Backend for scheduling/billing.

## 2. TV7 Engine (Rust / Axum Sidecar, Local)
*See [Engine Architecture](engine_architecture.md) for details.*

Runs locally on the user machine. Performs all compute-heavy work (transcription, clip detection, rendering).

## 3. TV7 Backend (FastAPI, Cloud Control Plane)
*See [Backend Architecture](backend_architecture.md) for details.*

Supports account, scheduling, and posting execution. Not involved in clip detection, LLM, or media generation.

## 4. TV7 Site
*See [Site Architecture](site_architecture.md) for details.*

Public landing pages and download sources. No billing or engine interaction.

---

## Cross-cutting Rules

1. **Local-first**: Ingest → Detect → Edit → Export works without backend.
2. **Studio owns UX**: Studio manages the "schedule builder" user experience.
3. **Backend owns Truth**: Backend is the source of truth for the final schedule.
4. **Billing**: Scheduling is the only billable feature (credits).
5. **Post Visibility**: First-class citizen.
    - Every post has history.
    - Attempts are tracked.
    - Results and timestamps are visible in Studio and backend.
