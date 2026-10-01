# TV7 Backend Roadmap

Roadmap Code: BE
Batch Code: A01

Last updated: 2026-10-01

## Done
- [X] [BE-A01-01-01] Completed control-plane cleanup: backend now focuses on auth, metadata, uploads, and scheduling metadata.
- [X] [BE-A01-01-02] Removed legacy media pipeline responsibilities from backend (download/transcribe/render paths).
- [X] [BE-A01-01-03] Implemented JWT auth flow and protected API routes (`login`, `refresh`, users, videos, clips, config).
- [X] [BE-A01-01-04] Restored/kept lightweight admin surfaces for operators (users, schedules, metrics).
- [X] [BE-A01-01-05] Kept quality gates and developer workflow (`make fmt/lint/type/test/testcov`).

## Needs To Be Done
- [ ] [BE-A01-02-01] Finalize and document clip sync contract for Studio desktop clients.
- [ ] [BE-A01-02-02] Expose and harden read-only polling/status APIs used by client/admin workflows.
- [ ] [BE-A01-02-03] Remove any remaining pre-credits scheduling logic and reconcile credit-ledger behavior.
- [ ] [BE-A01-02-04] Expand publish workflow model (`PublishJob`) and endpoint behavior with clear status transitions.
- [X] [BE-A01-02-09] Add owner-scoped private assets and durable schedule drafts.
    **COMPLETED** | Backend Agent + Architect | 2026-10-01
    - **NOTE**: Added private asset upload/read, owner-scoped clip update and publish listing, and idempotent `PENDING` schedule drafts with target platform/account, caption, asset, and UTC time. The direct publish route now returns 503 until a real adapter exists. Capability flags report scheduling and publishing unavailable. Verified 66 Backend tests, lint, type checking, and fresh/copy SQLite migrations; exported OpenAPI.
- [X] [BE-A01-02-10] Add a separate worker with durable due-job claims, leases, safe retries, and provider receipts after Studio exits.
    **COMPLETED** | Backend Agent + Architect | 2026-10-01
    - **NOTE**: Worker entrypoints and migration gate added for local, Compose, and Fly deployment. Due UTC drafts are claimed conditionally with a lease token; only a matching adapter receipt with remote post ID can complete a job. Safe pre-request errors retry at most three times; unknown outcomes and expired leases enter `RECONCILE`. The adapter registry is empty and publishing flags remain false. Verified 72 tests, lint, type checking, Compose config, and fresh/copied SQLite migrations. Real OAuth, adapters, shared object storage, billing, and provider reconciliation remain release gates.
- [ ] [BE-A01-02-11] Connect creator social accounts and implement real YouTube, Instagram, and TikTok publishing adapters with provider receipts.
- [X] [BE-A01-02-14] Build the first real account and publishing path for YouTube.
    **COMPLETED** | Backend Agent + Architect | 2026-10-01
    - **NOTE**: Added one-use PKCE OAuth, encrypted access/refresh credentials, owner-bound channel identity, resumable upload from approved assets, verified public/channel receipts, and reconciliation of uncertain sessions without blind re-upload. Capability flags require configured credentials plus explicit audit/publish gates. Exact fractional clip timing is preserved in migration `d8e5f3a1b720`. Verified 79 tests, lint, type checks, Compose config, and fresh SQLite migrations. Live Google OAuth, API audit, and public upload remain unverified; Instagram/TikTok remain open.
- [X] [BE-A01-02-12] Add private cloud object storage for approved assets retained for unattended schedules.
    **COMPLETED** | Backend Agent + Architect | 2026-10-01
    - **NOTE**: Owner-scoped asset API now supports local development storage and private S3-compatible production storage; worker materializes assets with checksum verification and temporary-file cleanup. Production fails closed without S3 configuration. Verified 75 Backend tests, lint, type checks, Compose config, and fresh SQLite migration `b457e9c83a12`. Live bucket access and billing remain unverified/open.
- [ ] [BE-A01-02-13] Meter storage usage, retention, and billing for scheduled approved assets.
- [X] [BE-A01-02-08] Store and serve owner-scoped source videos for Studio sync.
    **COMPLETED** | Backend Agent + Architect | 2026-10-01
    - **NOTE**: Local video registration is idempotent per account and source URL. Added private source upload, authenticated source retrieval, and duration-aware signed playback tickets for browser Range streaming. Video list/detail and clip creation are owner-scoped. Exported the updated OpenAPI contract. Verified 64 Backend tests, lint, type checking, a real 96 MB upload, and a live 206 partial response.
- [X] [BE-A01-02-05] Add Engine cloud AI delegation token endpoint.
    **COMPLETED** | Backend Agent | 2026-06-10 00:00
    - **CROSS-AGENT-NOTES**: Studio authenticates the user normally, requests a short-lived delegated Engine token after a lightweight account/credit check, and passes it to Engine over loopback. Token scope should be limited to `engine:cloud_ai`; for testing phase, keep revocation and auth mechanics simple and maintainable while preserving expiry and secret-safe logs.
    - **NOTE**: Implemented `/api/v1/cloud-ai/engine-token` using the existing JWT auth model with a short-lived `engine_cloud_ai` token scoped to `engine:cloud_ai`; token carries no provider secrets and requires available credits.
- [X] [BE-A01-02-06] Add TV7 cloud AI execution endpoint for Engine.
    **COMPLETED** | Backend Agent | 2026-06-10 00:00
    - **CROSS-AGENT-NOTES**: Engine is the caller for cloud AI execution. Studio should not call this endpoint directly for feature execution or AI debug. Backend owns DeepSeek credentials, authorization, credit checks, metering, and provider error normalization. Keep rate limiting minimal during testing; rely first on credit balance and simple request safeguards.
    - **NOTE**: Implemented `/api/v1/cloud-ai/engine/execute` for delegated Engine tokens only, with DeepSeek adapter config, minimal context/rate safeguards, credit checks, stable AI error normalization, and no backend media-processing ownership.
- [X] [BE-A01-02-07] Add cloud AI usage metering and admin visibility.
    **COMPLETED** | Backend Agent | 2026-06-10 00:00
    - **CROSS-AGENT-NOTES**: Meter TV7 cloud AI usage per user/request and expose operator diagnostics for perpetual purchased credits, remaining balance, cost, provider latency, and provider failure analysis. Admin/test users may receive a very large initial credit grant for development. Keep request bodies and secrets out of logs unless an explicit redacted debug artifact is designed.
    - **NOTE**: Added perpetual credit ledger and request metering tables, large testing admin grant support, an admin-only per-user credit grant workflow, `/admin/cloud-ai` balance/request/latency visibility, and regenerated the backend OpenAPI contract.

## Nice To Have
- [ ] [BE-A01-03-01] Add migration cleanup for legacy `local_path` artifacts where no longer relevant.
- [ ] [BE-A01-03-02] Improve observability with stage-level metrics and richer structured logs.
- [ ] [BE-A01-03-03] Add storage hygiene automation for stale media/temp assets.
- [ ] [BE-A01-03-04] Implement YouTube OAuth connector to replace cookie-based operational workflows.

## Cross-Repo Milestone: Unified Engine AI + Cloud Delegation
- **Active handoff**: `docs/handoffs/active/backend.md`
- **Backend route**: Own Backend cloud AI control plane: delegated Engine token minting, Engine-only cloud execution, provider credentials, credit/quota metering, admin visibility, and OpenAPI contract updates.
- **Primary roadmap items**: `BE-A01-02-01`, `BE-A01-02-02`, `BE-A01-02-04`, `BE-A01-02-05`, `BE-A01-02-06`, `BE-A01-02-07`.
- **Boundary**: Backend must not own local media probing, local transcription, local rendering, local transcript scoring, or Studio-facing provider UX.
