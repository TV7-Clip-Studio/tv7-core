# TV7 Backend Roadmap

Roadmap Code: BE
Batch Code: A01

Last updated: 2026-06-10

## Done
- [X] [BE-A01-01-01] Completed control-plane cleanup: backend now focuses on auth, metadata, uploads, and publish scheduling.
- [X] [BE-A01-01-02] Removed legacy media pipeline responsibilities from backend (download/transcribe/render paths).
- [X] [BE-A01-01-03] Implemented JWT auth flow and protected API routes (`login`, `refresh`, users, videos, clips, config).
- [X] [BE-A01-01-04] Restored/kept lightweight admin surfaces for operators (users, schedules, metrics).
- [X] [BE-A01-01-05] Kept quality gates and developer workflow (`make fmt/lint/type/test/testcov`).

## Needs To Be Done
- [ ] [BE-A01-02-01] Finalize and document clip sync contract for Flutter desktop clients.
- [ ] [BE-A01-02-02] Expose and harden read-only polling/status APIs used by client/admin workflows.
- [ ] [BE-A01-02-03] Remove any remaining pre-credits scheduling logic and reconcile credit-ledger behavior.
- [ ] [BE-A01-02-04] Expand publish workflow model (`PublishJob`) and endpoint behavior with clear status transitions.
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
    - **NOTE**: Added perpetual credit ledger and request metering tables, large testing admin grant support, `/admin/cloud-ai` balance/request visibility, and regenerated the backend OpenAPI contract.

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
