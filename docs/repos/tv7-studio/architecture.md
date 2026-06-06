# TV7 Studio Architecture

Last updated: 2026-02-12

Canonical system source: `docs/architecture/tv7_high_architecture.md`.
This doc captures the Studio repo view and the practical boundaries for implementation.

## Component Roles
- **Studio (`tv7-studio`)**: desktop-first app for auth, ingest, local media workflows, clip UX, and backend metadata sync.
- **FastAPI control plane (`tv7-backend`)**: auth/session APIs, config APIs, clip/publish APIs, and admin/dashboard endpoints.
- **Scheduler worker (backend-owned)**: executes deferred publishing jobs, updates status, and records retries/failures.
- **Storage**: backend DB + object storage for uploaded assets and publish jobs.

## Current Studio Surface (Repo Reality)
- App lives in `forgotten_client/`.
- Feature modules currently present under `forgotten_client/lib/features/`: `auth`, `dashboard`, `ingest`, `player`, `user`.
- App data layer currently present under `forgotten_client/lib/data/`: `api`, `auth`, `config`, `local`.
- Generated API SDK lives in `forgotten_client/lib/api/generated/` and is treated as generated-only code.

## Architecture Boundaries
- Keep business/data IO in `lib/data/...`; keep UI logic in `lib/features/...`.
- Do not store platform OAuth secrets in client code.
- Prefer OpenAPI-generated models/clients for backend contract usage; avoid ad-hoc request DTO drift.
- Any backend contract change must be reflected in `docs/contracts/openapi/tv7-backend/openapi.json` before client regeneration.

## App-to-Backend Responsibilities
- **Auth**: login/refresh token flow plus user-facing session handling.
- **Config**: consume backend config to gate publish/features/limits.
- **Ingest and clips**: sync video/clip metadata and maintain stable IDs for local-to-remote mapping.
- **Publishing**: client triggers publish/schedule workflows; backend and worker execute and report state.

## Quality and Operations
- Desktop-first workflow is the default development path.
- Required checks in this repo: `make check` (format + analyze + test).
- Cross-repo changes must follow `docs/repos/cross-repo-policy.md`.
