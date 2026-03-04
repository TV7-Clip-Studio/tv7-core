# TV7 Flutter Studio Roadmap

Roadmap Code: FL
Batch Code: A01

Last updated: 2026-02-08

## Done
- [X] [FL-A01-01-01] Scaffolded Flutter client foundation with flavor entrypoints (`dev`, `stage`, `prod`).
- [X] [FL-A01-01-02] Added configuration wiring via dart-defines and baseline app bootstrap structure.
- [X] [FL-A01-01-03] Created API/auth scaffolding (Dio client, auth token models/store placeholders).
- [X] [FL-A01-01-04] Established repo docs for architecture, backend integration, publishing contract, and testing strategy.

## Needs To Be Done
- [ ] [FL-A01-02-01] Regenerate and adopt OpenAPI client against the current FastAPI contract.
- [ ] [FL-A01-02-02] Wire clip suggestion/highlight APIs into production auto-clip flows with robust error UX.
- [ ] [FL-A01-02-03] Harden local ingest workspace (dependency checks, diagnostics, logs, recoverability).
- [ ] [FL-A01-02-04] Build timeline trim/subtitle/export UX around the current local processing pipeline.
- [ ] [FL-A01-02-05] Add durable local cache/queue and retry logic for metadata/upload sync.

## Nice To Have
- [ ] [FL-A01-03-01] Add optional local transcription path (Whisper.cpp) with backend fallback.
- [ ] [FL-A01-03-02] Complete Pro scheduler UX: publish scheduling, polling, and failure visibility.
- [ ] [FL-A01-03-03] Implement licensing/config enforcement and plan-aware feature gating.
- [ ] [FL-A01-03-04] Improve packaging/release UX (desktop artifacts, updater flow, telemetry opt-in).
