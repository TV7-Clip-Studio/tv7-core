# Cross-Repo Roadmap (Snapshot)

Guiding rule: `tv7-core` tracks only cross-repo milestones that unblock 3+ repos (engine/app/backend/site). Repo-specific work stays local.

## Phase 1 — Foundations (active)
- Core: All repos mount `00-tv7-core`; standards (naming, repo structure, versioning, changelog, security) published; Arch Agent directive enforced.
- Tooling: Shared Makefile/scripts to update submodules and run lint-all/checks across repos; bootstrap stub ready.
- Engine: HTTP surface + job model stubbed; FFI shape agreed (even if not implemented yet).
- Backend: Auth/license flows stable; worker skeleton in place (jobs queue + noop posting).
- App (Flutter): Desktop can spawn engine, ingest/transcribe/export minimally.
- Site (Astro): Live marketing page with downloads/docs links.

## Phase 2 — Core Feature Parity
- Engine: End-to-end pipeline (ingest, transcript, clip suggestion, cut, export) callable via HTTP; baseline perf budgets noted.
- Backend: Optional LLM fallback endpoint; Pro clip upload + scheduling CRUD usable; schema stable.
- App: Timeline/editing UX with local-first defaults; can upload rendered clip + metadata to backend for Pro.
- Tooling: Cross-repo lint/format targets green; shared CI snippets drafted.
- Standards: Repo structure + docs-local vs `00-tv7-core` separation adopted everywhere.

## Phase 3 — Pro Scheduling & Hardening
- Worker: Posts to social targets with retries/metrics/logging; status updates reflected in backend API.
- App/site: Dashboard polish; status sync to Flutter; Astro surfaces Pro value and links to dashboard.
- Packaging: Signing templates per platform; release versioning rules enforced per repo.
- Security: Secrets guidance adopted; basic audits in CI (ruff/bandit/cargo-audit/npm audit as applicable).

## Phase 4 — Mobile & Scale
- Engine: FFI bindings usable for mobile; parity with desktop surfaces where feasible.
- Performance: Profiling + optimizations on engine hot paths; baseline perf docs captured in `00-tv7-core`.
- CI/Release: Shared CI templates in use; changelog/release-note policy enforced; coordinated releases when contracts change.
