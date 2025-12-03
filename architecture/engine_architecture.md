# TV7 Engine Architecture (Cross-Repo View)

Context
- Lives in `tv7-axum-engine` repo; consumed by Flutter (desktop via HTTP, mobile via future FFI) and backend (no direct coupling).
- Goal: keep heavy media/LLM local, expose a stable surface for app integrations.

Components
- `engine-core` (library): media pipeline, transcription, LLM; no transport/runtime concerns.
- `engine-service` (Axum sidecar): HTTP on `127.0.0.1`, validates inputs, invokes `engine-core`, exposes job polling (`/jobs/{id}`); no cloud/business logic.
- `engine-ffi` (future): C ABI for Flutter mobile; mirrors `engine-core` APIs without hosting a server.

Integration contract
- Desktop: Flutter spawns `engine-service`, polls `/health`, submits work, polls `/jobs/{id}` for long tasks.
- Mobile: Flutter calls FFI bindings; must receive the same shapes as HTTP responses.
- Inputs use absolute paths; engine never accesses the network; results stay local unless the app uploads to backend for Pro scheduling.

Non-goals
- No auth/state/business logic (lives in FastAPI backend).
- No cloud calls; no direct DB/object storage access.

Runtime expectations
- Loopback-only binding; configurable port (default `27107`).
- FFmpeg orchestrated by engine; caller supplies media paths.
- Whisper.cpp/Llama.cpp embedded; models provisioned locally by the app.
