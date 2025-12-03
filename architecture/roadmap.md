# Cross-Repo Roadmap (Snapshot)

Phase 1 — Foundations
- Align repos on `00-tv7-core` submodule; document standards and tooling.
- Solidify engine HTTP/FFI surface; stub handlers where needed.
- Backend auth/license flows stable; worker skeleton in place.
- Flutter desktop orchestrates engine, basic ingest/transcript/export.
- Astro site live with downloads/docs links.

Phase 2 — Core Feature Parity
- Engine media pipeline end-to-end (ingest, transcript, clip suggestion, cut, export).
- Flutter UX for timeline/editing; local-first defaults.
- Backend optional LLM fallback endpoint; Pro clip upload & scheduling CRUD usable.
- Cross-repo lint/format targets operational.

Phase 3 — Pro Scheduling & Hardening
- Worker posting to social targets with retries and observability.
- Dashboard polishing; status sync to Flutter.
- Packaging/signing templates per platform; release versioning rules enforced.
- Security/secrets guidance adopted across repos.

Phase 4 — Mobile & Scale
- FFI bindings for mobile; parity with desktop flows where feasible.
- Performance passes on engine; profile/optimize hotspots.
- CI templates shared; changelog/release note policy enforced.
