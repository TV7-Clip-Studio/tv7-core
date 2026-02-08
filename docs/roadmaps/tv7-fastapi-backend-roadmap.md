# TV7 FastAPI Backend Roadmap

Last updated: 2026-02-08

## Done
- [x] Completed control-plane cleanup: backend now focuses on auth, metadata, uploads, and publish scheduling.
- [x] Removed legacy media pipeline responsibilities from backend (download/transcribe/render paths).
- [x] Implemented JWT auth flow and protected API routes (`login`, `refresh`, users, videos, clips, config).
- [x] Restored/kept lightweight admin surfaces for operators (users, schedules, metrics).
- [x] Kept quality gates and developer workflow (`make fmt/lint/type/test/testcov`).

## Needs To Be Done
- [ ] Finalize and document clip sync contract for Flutter desktop clients.
- [ ] Expose and harden read-only polling/status APIs used by client/admin workflows.
- [ ] Remove any remaining pre-credits scheduling logic and reconcile credit-ledger behavior.
- [ ] Expand publish workflow model (`PublishJob`) and endpoint behavior with clear status transitions.

## Nice To Have
- [ ] Add migration cleanup for legacy `local_path` artifacts where no longer relevant.
- [ ] Improve observability with stage-level metrics and richer structured logs.
- [ ] Add storage hygiene automation for stale media/temp assets.
- [ ] Implement YouTube OAuth connector to replace cookie-based operational workflows.
