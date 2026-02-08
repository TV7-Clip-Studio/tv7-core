# TV7 Architecture (Aligned to `tv7_high_architecture.md`)

`tv7_high_architecture.md` is the canonical source. This doc restates the architecture in repo terms and how the Flutter app, FastAPI control plane, and scheduler worker fit together.

## Component Roles
- **Flutter app (desktop-first)**: local-first pipeline. Handles auth/licensing, ingest (file/YouTube), local transcription (Whisper.cpp), LLM clip suggestions via backend, auto clipping (ffmpeg), timeline/editing/export, optional local posting, Pro uploads for scheduling, schedule status display, Pro dashboard in WebView.
- **FastAPI control plane**: auth + trial + license issuance (signed token), clip suggestion endpoint (LLM provider), Pro-only clip upload & scheduling APIs, social OAuth (Pro), config/feature flags, payment integration, minimal web dashboard.
- **Scheduler worker**: polls DB for `scheduled` posts, publishes at `publish_at`, retries/failure logging, updates status (`scheduled` → `posted|failed`), runs with access to object storage and platform tokens.
- **Storage**: Postgres tables for users, licenses, scheduled posts, social connections; S3-compatible bucket for Pro clip uploads.

## App ↔ Backend Contracts
- **Auth & licensing**: register/login/trial validation/license activation. Backend returns signed license token with `plan` (`trial|core|pro`) + `expires_at`; app caches securely for offline use and blocks when expired.
- **Clip suggestions**: app sends transcript (local + YouTube merge) + optional prompt; backend returns clip segments (start/end) with titles/descriptions/hooks.
- **Uploads & scheduling (Pro)**: app uploads rendered clip + metadata; backend stores and creates ScheduledPost; app polls status; social OAuth handled in backend WebUI.
- **Config**: app fetches config/feature flags (publishing enabled, limits, OpenAI policy) and gates flows accordingly.

## Local Pipeline (App)
- Workspace under app data dir (`ingest/normalize/render/logs/cache`).
- Ingest: YouTube via `yt-dlp` or file import; metadata + transcript saved locally.
- Transcription: Whisper.cpp by default; backend/cloud fallback when disabled/failing.
- Clip suggestion: backend LLM endpoint; results drive auto clipping.
- Editing/export: timeline/trim/text/subtitles; ffmpeg renders; local export; optional local posting.

## Pro Scheduler Flow (App + Backend + Worker)
1) User on Pro uploads rendered clip (or gets signed URL) + metadata to backend.
2) Backend persists ScheduledPost with `publish_at` and platform list; returns status.
3) Worker posts at `publish_at`, retries on failure, updates status/logs.
4) App polls status and surfaces posted/failed info; Pro dashboard in WebView handles OAuth/platform connections.

## Non-functional
- Local-first, offline-capable while license token valid.
- Low backend cost (no heavy media processing in cloud).
- JWT-signed license tokens; secure storage client-side; HTTPS everywhere.
- Scheduler reliability and retry safety.
