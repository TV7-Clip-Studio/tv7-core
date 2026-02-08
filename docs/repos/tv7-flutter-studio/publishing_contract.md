# Publishing Contract (TV7 Pro Scheduler)

Source: `tv7_high_architecture.md`. Publishing is Pro-only and executed by the backend worker; the Flutter app triggers and monitors.

## Ownership
- **Backend + worker**: holds platform OAuth/tokens, asset intake, schedule creation, posting execution, retries/backoff, logging/auditing. Exposes minimal web dashboard for OAuth/connect.
- **Client**: renders locally, uploads assets (or uses signed URL), submits schedules with metadata, polls status, shows logs/errors. Never stores platform tokens.

## Required Backend Capabilities
- Config endpoint: `publishing_enabled`, allowed platforms, asset size/format limits, OpenAI/local policy.
- Asset intake: multipart upload or signed URL issuance → returns `asset_url`, checksum/size fields.
- Schedule API: create/read/list with `status` (`draft|scheduled|posted|failed`), `publish_at`, per-platform results, error message/log, retries.
- Web dashboard endpoints for OAuth/social connections; app opens in WebView.

## Client Responsibilities
- Enforce plan/licensing: publishing only when `plan=pro` and license valid.
- Upload rendered clip + thumbnail (if required); include checksum/size; store returned `asset_url`.
- Create schedule with `publish_at`, platforms, title/description/captions; poll status and surface errors/retries.
- Respect config flags: hide/disable publishing when off or limits exceeded.

## Flow
1) Fetch config; confirm publishing enabled and Pro license valid.
2) Upload asset (direct or signed URL) → obtain `asset_url`.
3) POST schedule with metadata + `publish_at`; receive initial status.
4) Worker posts at `publish_at`, retries on failure, updates status/logs.
5) App polls (`GET schedule`) to show `scheduled/posted/failed`, errors, and retry info; dashboard handles OAuth.

## OpenAPI Notes
- Include scheduler endpoints, publish status enum, asset fields, and config fields in the spec.
- Mark publishing endpoints as Pro-only/gated by license; align naming with client (`/api/v1/clips/{id}/publish` or schedule resource).
