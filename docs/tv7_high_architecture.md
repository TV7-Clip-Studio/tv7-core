# TV7 v1 – High-Level Architecture  
Hybrid Local-First Editor + Thin Cloud Control Plane

---

## 1. Overview

TV7 is a local-first video clipping and repurposing application.  
All heavy media operations run on-device using the user’s CPU/GPU:

- Video ingestion  
- Transcription  
- Clip detection (with local LLM help; backend optional as a fallback)  
- Cutting and editing  
- Local exporting  
- Optional local posting  

A minimal FastAPI backend acts as the control plane for:

- Accounts & authentication  
- Trials & licensing  
- Pro-only cloud scheduling (backend posts clips when user is offline)
- Optional remote clip suggestion (only if local model is unavailable/disabled)

This architecture keeps backend cost extremely low and allows a one-time purchase model for Core and subscription for Pro.

### Repos & shared docs (tv7-*)
- `tv7-flutter-studio` — Flutter desktop/mobile app that orchestrates the local engine (HTTP on desktop, FFI on mobile).
- `tv7-axum-engine` — Rust `engine-core` + Axum `engine-service` sidecar; future `engine-ffi` for mobile.
- `tv7-fastapi-backend` — FastAPI control plane with Dramatiq worker for scheduling; no heavy media work.
- `tv7-astro-site` — Astro marketing + downloads site that links to installers/docs.
- `tv7-docs` — Single source-of-truth docs repo (this file). Mount as `/docs` submodule in every code repo. Clone with `git clone --recurse-submodules` or run `git submodule update --init --recursive` after cloning to pull docs; update docs in `tv7-docs` then bump each repo’s submodule pointer.

---

## 2. Product Tiers

### 2.1 TV7 Core (Local-First)
- 1-month free trial  
- After trial → one-time purchase (activation key)  
- All heavy functionality runs offline:  
  - Ingest, transcript, clip cutting, editing, export  
- Backend used only for:  
  - Login  
  - Trial validation  
  - License activation  
  - Optional clip suggestion fallback if local LLM is not available  

### 2.2 TV7 Pro (Cloud Scheduler)
Adds:  
- Cloud posting when user is offline  
- Minimal web dashboard for Pro users  
- Backend stores social tokens (Option A)  
- Scheduler worker posts clips at scheduled times  

---

## 3. Architecture Components

### 3.1 Flutter App (`tv7-flutter-studio`, desktop-first)
Responsibilities:

- User authentication (via FastAPI)  
- Caching license token for offline usage  
- **Orchestrating the Rust Engine** (spawning, managing lifecycle)
- Local video ingestion (file or YouTube)  
- Sending transcript + user prompt to the Rust engine for clip suggestions (backend fallback only if local LLM unavailable)  
- Local clip editing (timeline, trimming, text, subtitles)  
- Local exporting  
- Uploading rendered clips to backend for Pro scheduling  
- Displaying scheduled post status (from backend)  
- Opening Pro dashboard via WebView  

---

### 3.2 Rust Engine (`tv7-axum-engine`: Core + Service)
Responsibilities (split by crate):

- **engine-core** (Rust library): heavy logic for media processing, transcription, and local LLM. No Axum/Tokio/JSON/platform code; reusable across desktop/mobile/CLI.
- **engine-service** (Axum sidecar): HTTP adapter on `127.0.0.1`. Parses JSON, validates inputs, invokes `engine-core`, exposes `/jobs/{id}` for long tasks. No business logic or cloud calls live here.
- **engine-ffi** (future): C ABI for Flutter mobile (Dart → C → Rust). Mobile never hosts an Axum server; it calls the same `engine-core` functions via FFI.

Shared traits:
- High-performance local media processing
- **FFmpeg** orchestration (cutting, watermarking, rendering)
- **Whisper.cpp** integration (local transcription)
- **Llama.cpp** integration (local LLM tasks)
- Async job model for long-running work (`/jobs/{id}` on desktop; equivalent callbacks/polling over FFI later)

---

### 3.3 FastAPI Backend (`tv7-fastapi-backend`, control plane)
Responsibilities:

- REST API for authentication & license management  
- Trial logic & activation key validation  
- Issuing signed license tokens (JWT-like)  
- Optional remote clip suggestion endpoint (if local model is absent/disabled)  
- Pro-only clip upload endpoint  
- Pro scheduling system storage & logic  
- Storing social OAuth tokens (Option A)  
- Simple web dashboard for Pro users  
- Payment integration (Stripe, Paddle, Lemon Squeezy)  

---

### 3.4 Scheduler Worker (part of `tv7-fastapi-backend`)
Responsibilities:

- Periodically checks DB for upcoming scheduled posts  
- At `publish_at`, posts the clip to the target platform  
- Handles retries & failure logging  
- Updates post status (scheduled → posted/failed)  

---

### 3.5 Storage & Database

- **Database (Postgres)**  
  - Users  
  - License records  
  - Scheduled posts  
  - Social connections (Pro)

- **Object Storage (S3-compatible)**  
  - Short-term clip file storage for scheduled posting  

---

### 3.6 Astro Marketing Site (`tv7-astro-site`)
Responsibilities:

- Static marketing + download page (Astro project in the repo root)  
- Links to installers or store pages per platform  
- Hosts docs/FAQs and directs users to support  

---

### 3.7 Shared Docs (`tv7-docs` submodule)
Responsibilities:

- Canonical, versioned documentation for architecture, API contracts, and runbooks.
- Lives in the `tv7-docs` repo; mounted at `/docs` inside each `tv7-*` codebase via Git submodule to keep all teams aligned.
- Update docs once in `tv7-docs`, then update each repo’s submodule ref so app/backend/engine/site all ship the same documentation snapshot.

## 4. App ↔ Backend Interactions

### 4.1 Authentication & Licensing
The app communicates with backend for:

- Register  
- Login  
- Trial validation  
- License activation  
- License refresh  

The backend responds with a **signed license token** containing:

- Plan (`trial`, `core`, `pro`)  
- Expiration timestamp  

The app works offline as long as the token is valid.

---

### 4.2 Clip Suggestion (LLM-Assisted)
Default path (local-first):

The app sends to the **Rust engine**:

- Transcript (local+YouTube merged)  
- Optional user prompt  

Engine returns:

- Suggested clip segments  
- Titles & descriptions  

App uses these timecodes for local cutting.

Fallback (optional):
- If the local model is missing/disabled, the app can call the backend suggestion endpoint instead.

---

### 4.3 Pro Scheduling
For Pro users only:

- App uploads rendered clip file + metadata to backend  
- Backend stores clip & creates a ScheduledPost entry  
- Scheduler worker posts clip at `publish_at`  
- App can query status via API  
- Actual social account connections are done in the backend WebUI  

---

## 5. Data Model (Simplified)

### User
- `id`  
- `email`  
- `password_hash`  
- `plan` (trial | core | pro)  
- `trial_started_at`  
- `trial_expires_at`  

### License
- `user_id`  
- `activation_key`  
- `plan`  
- `expires_at`  

### ScheduledPost
- `id`  
- `user_id`  
- `platform`  
- `title`  
- `description`  
- `clip_url`  
- `publish_at`  
- `status` (draft | scheduled | posted | failed)  
- `posted_at`  
- `error_message`  

### SocialConnection
- `user_id`  
- `platform`  
- `access_token`  
- `refresh_token`  
- `expires_at`  

---

## 6. Non-functional Requirements

- Local-first operation (offline support)  
- Low backend cost (no heavy media processing)  
- Secure token storage (backend)  
- End-to-end HTTPS  
- JWT-signed license tokens  
- Scheduler worker must be reliable and retry-safe  

---

## 7. Responsibilities Overview

### Flutter App
- Local ingest, transcript, cutting, editing  
- Call backend for:
  - auth  
  - license  
  - clip suggestions (only if local LLM unavailable)  
  - Pro uploads  
- Display scheduled post status  
- Open Pro dashboard  

### FastAPI Backend
- Auth & licensing  
- Optional remote clip suggestion  
- Pro scheduling endpoints  
- Social OAuth management  
- Background worker for posting  
- Payment integration  

---

## 8. TV7 v1 Release Scope

### TV7 Core
- Login, Trial, License  
- Local ingest & transcript  
- Clip suggestion (local Rust engine; backend optional fallback)  
- Local auto-cut  
- Local editing  
- Local export  

### TV7 Pro
- Cloud OAuth (backend)  
- Clip upload to backend  
- Scheduling  
- Worker posting  
- Web dashboard  
- Status sync to app  

---

## 9. Local-First Guarantees & Operational Notes
- Media stays on-device for Core flows; only Pro scheduling uploads rendered clips to the backend.
- Rust engine binds to loopback only; Flutter supplies absolute paths to avoid traversal issues.
- If the engine is unavailable, the Flutter app should start it, poll `/health`, and fail fast with a clear error if it cannot start.
- Updates: the Flutter app bundles a pinned engine version; auto-update can be delegated to Flutter or a small updater that swaps the binary atomically.
- Crash isolation: the editor process survives if the engine crashes; retry by respawning the engine.
- Long-running work uses the engine’s async job model (`/jobs/{id}`) for progress polling.

### Engine Lifecycle (Desktop App)
1. Pick a port (default `27107`, override via env/CLI flag) and persist it for the current session.
2. Spawn the engine binary with `--port` and logging flags; bind to loopback only.
3. Poll `/health` with exponential backoff; give up with a user-friendly error if it never comes up.
4. On crash, prompt to retry: respawn and re-poll `/health`.
5. On graceful exit (app quit), send a shutdown signal or kill the child process to avoid orphans.
6. For long-running work, the app submits the request, receives `job_id`, shows progress via `/jobs/{id}`, and refreshes results until terminal (`completed`/`failed`).
