# TV7 Backend Roadmap

Roadmap Code: BE
Batch Code: A01

Last updated: 2026-02-08

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

## Nice To Have
- [ ] [BE-A01-03-01] Add migration cleanup for legacy `local_path` artifacts where no longer relevant.
- [ ] [BE-A01-03-02] Improve observability with stage-level metrics and richer structured logs.
- [ ] [BE-A01-03-03] Add storage hygiene automation for stale media/temp assets.
- [ ] [BE-A01-03-04] Implement YouTube OAuth connector to replace cookie-based operational workflows.
