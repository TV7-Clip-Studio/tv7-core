# TV7 v1 Alignment & Roadmap (source: `docs/architecture/tv7_high_architecture.md`)

`docs/architecture/tv7_high_architecture.md` is now the source of truth. This note captures where the repo stands today, the gaps vs the final plan, and what to change in docs and delivery.

## Current State Snapshot (this repo)
- Flutter desktop-first client with login/refresh wired to FastAPI (`/api/v1/auth/login|refresh`) using an in-memory token store (no secure caching yet).
- Local ingest flows: YouTube download via `yt-dlp`, file import, ffprobe metadata, transcript download from YouTube captions, local clip rendering via `ffmpeg`, thumbnailing, and asset upload to `/api/v1/uploads/assets`.
- Auto highlights/clip suggestions: calls ad-hoc `/api/v1/ai/highlights` (not in the checked-in OpenAPI spec) to get start/end/hooks; can auto-render and sync clips to backend `/api/v1/videos/local` + `/api/v1/videos/{id}/clips`.
- UI: login shell, ingest screen (URL/file), dashboard with grouped videos/clips, simple player with highlight-driven clipping, user list page. No settings/workspace management or license gating.
- OpenAPI spec (32 paths) includes auth, config, ingest, clips, publish job stubs, but **no** licensing/trial endpoints; client code partly bypasses the generated SDK.

## Gaps vs Final Architecture
### Core (local-first)
- Licensing/trial: no activation key flow, no signed license token caching for offline, no plan awareness (`trial/core/pro`), no expiry handling.
- Offline posture: tokens live only in-memory; no secure persisted store; app assumes online API availability.
- Transcription: relies on YouTube captions; no local Whisper.cpp integration; no UX to pick local vs cloud or handle model paths/downloads.
- Clip suggestion contract: app uses `/api/v1/ai/highlights` while spec exposes `/api/v1/ai/execute`; LLM prompt/schema not aligned to the “transcript + prompt → segments” contract.
- Editing/export: only simple trim + thumbnail; no timeline editing, subtitle burn-in, or explicit export flow.
- Config/flags: placeholder repository; no backend-driven config fetch for feature flags (publishing, limits).
- Local cache/sync: no SQLite/Hive workspace metadata or offline queue; uploads happen immediately.

### Pro (scheduler)
- No flow to upload rendered clips for scheduling, no scheduled status polling, no social OAuth hand-off, no WebView/dashboard link, and no UI/worker contract for `publish_at` / status enums.
- Backend worker expectations (retries, status transitions, failure logging) not expressed in client or docs.

### Backend/API
- Missing/unstated endpoints: register/activate license, issue signed license token, trial validation, plan upgrades, license refresh.
- Scheduler contract not in spec: schedule create/list/status, worker status updates, posting results.
- Clip suggestion endpoint/schema divergence; need OpenAPI update plus regenerated Dart SDK.
- Config endpoint exists in spec but client ignores it; need to standardize fields (feature flags, limits, OpenAI policy).

### Docs
- `docs/repos/tv7-flutter-studio/architecture.md` / `docs/roadmaps/tv7-flutter-studio-roadmap.md` / `docs/repos/tv7-flutter-studio/backend_integration.md` describe the older hybrid plan; they don’t reflect Core vs Pro, licensing, or scheduler worker roles from `docs/architecture/tv7_high_architecture.md`.
- Publishing contract doc assumes backend owns tokens but doesn’t mention the Pro-only scheduler/web dashboard split or license gating.

## Doc Updates to Make
- Designate `docs/architecture/tv7_high_architecture.md` as canonical; link to it from README and other docs.
- Rewrite `docs/repos/tv7-flutter-studio/architecture.md` around the final component roles: Flutter app (local-first), FastAPI control plane, scheduler worker, storage/DB tables listed in the final doc.
- Replace `docs/roadmaps/tv7-flutter-studio-roadmap.md` with the phased roadmap below; split Core vs Pro scope explicitly.
- Update `docs/repos/tv7-flutter-studio/backend_integration.md` and `docs/repos/tv7-flutter-studio/publishing_contract.md` to include license/plan enforcement, clip suggestion schema, config endpoint fields, scheduler API, and dashboard/WebView touchpoints.
- Add a short “API/OpenAPI status” note summarizing missing endpoints (license, scheduler) and the highlight endpoint mismatch, plus a regeneration plan.

## Proposed Roadmap (aligned to TV7 v1)
1) **Spec & licensing foundation (Core)**
   - Add backend endpoints: register/login, trial check, activation key, signed license token issuance/refresh, config flags; export OpenAPI and regenerate the Dart client.
   - Implement secure token store + cached license token with offline validation; gate UI by plan/expiry.
2) **Local pipeline completeness (Core)**
   - Integrate Whisper.cpp for local transcription (model management, path validation, fallback to backend); workspace management; settings for binaries.
   - Align clip suggestion call with backend contract (transcript + optional prompt → segments); error UX and retries.
   - Add timeline/basic editing, subtitle burn-in, explicit export flow, and local cache/queue for offline sync of videos/clips/uploads.
3) **Pro scheduler**
   - Client upload flow to backend storage, schedule create/update, status polling; display scheduled/posted/failed states.
   - WebView link to backend dashboard for OAuth/connect; reflect connected platforms in client config.
   - Worker status contract (retries, errors) exposed in UI; notifications/polling cadence.
4) **Polish & distribution**
   - Settings, diagnostics/log export, missing-binary guidance; desktop packaging; minimal mobile parity once desktop solid.

## Immediate Next Actions
- Update OpenAPI spec to include licensing/trial and scheduler endpoints; align clip suggestion path/schema; regenerate `lib/api/generated`.
- Swap token store to a persisted secure implementation; add license token caching/validation and plan flags in the client.
- Draft updated `docs/repos/tv7-flutter-studio/architecture.md` / `docs/roadmaps/tv7-flutter-studio-roadmap.md` / `docs/repos/tv7-flutter-studio/backend_integration.md` using the above roadmap and the final architecture roles.
- Wire backend config fetch and enforce feature flags (publishing enabled, limits, OpenAI policy) in the client flows.
