# Backend Integration (FastAPI control plane)

Source of truth: `docs/architecture/tv7_high_architecture.md`. This doc maps the FastAPI contract the Flutter app depends on (Core + Pro) and the OpenAPI expectations.

## Required Endpoints
- **Auth & licensing**: register, login, trial validation, activation key, license issuance/refresh. Response includes signed license token with `plan` and `expires_at` for offline use.
- **Config**: feature flags + limits (publishing enabled, platforms, size limits, OpenAI policy/local-vs-cloud rule).
- **Clip suggestion**: transcript (+ optional prompt) → list of segments with start/end/title/description/hook; deterministic schema in OpenAPI.
- **Uploads (Pro)**: asset upload endpoint or signed-URL negotiation; returns `asset_url` and metadata for schedule creation.
- **Videos/clips**: local video registration, clip upsert (with `asset_url`, timings, captions).
- **Scheduling (Pro)**: create/read/list scheduled posts with `status` (`draft|scheduled|posted|failed`), `publish_at`, per-platform results, error logs, retries.
- **Dashboard/Web**: endpoints backing the minimal Pro dashboard for OAuth/social connections.

## OpenAPI Expectations
- Publish updated spec to `docs/contracts/openapi/tv7-fastapi-backend/openapi.json` with the above endpoints. Regenerate the Dart client (`lib/api/generated`) after each spec change.
- Include enums for plan, clip status, publish status; document request/response shapes for license issuance and schedule status.
- Keep `/api/v1/ai/highlights` (or renamed) in spec to match the client; remove ad-hoc endpoints once aligned.

## Client Responsibilities (per spec)
- Attach auth + license token; operate offline while license valid; block when expired.
- Respect config flags: disable publishing when off, enforce size/platform limits, follow OpenAI/local policy.
- For Pro: upload assets, create schedules, poll status; open dashboard WebView for OAuth.
- Send transcripts, captions, and timing metadata when registering videos/clips; handle retries/backoff on failure.

## Backend coordination (Phase 1 highlights)
- Implement `/api/v1/ai/highlights` as specced: request `{transcript, duration_seconds, prompt?, max_clips?, transcript_language?}`; response `{clips: [{start_sec, end_sec, title?, description?, hook}], max_clips?, model?}` with HTTP Bearer auth and validation.
- Wire the endpoint to the LLM prompt/logic for clip suggestions; keep or alias `/api/v1/ai/execute` only if needed.
- Re-export the OpenAPI after backend changes so the Dart SDK can be regenerated; keep the path/tag naming stable.

## Next Integration Steps
- Add licensing/trial endpoints and scheduler endpoints to the FastAPI spec; align clip suggestion path/schema.
- Export spec and run `make gen-api` (or `tool/generate_api.sh`) to refresh the Dart SDK.
- Update the client to use generated APIs (minimize raw Dio calls) and wire config/licensing flows.
