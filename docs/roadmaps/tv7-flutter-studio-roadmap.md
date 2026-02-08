# TV7 Flutter Studio Roadmap

Last updated: 2026-02-08

## Done
- [x] Scaffolded Flutter client foundation with flavor entrypoints (`dev`, `stage`, `prod`).
- [x] Added configuration wiring via dart-defines and baseline app bootstrap structure.
- [x] Created API/auth scaffolding (Dio client, auth token models/store placeholders).
- [x] Established repo docs for architecture, backend integration, publishing contract, and testing strategy.

## Needs To Be Done
- [ ] Regenerate and adopt OpenAPI client against the current FastAPI contract.
- [ ] Wire clip suggestion/highlight APIs into production auto-clip flows with robust error UX.
- [ ] Harden local ingest workspace (dependency checks, diagnostics, logs, recoverability).
- [ ] Build timeline trim/subtitle/export UX around the current local processing pipeline.
- [ ] Add durable local cache/queue and retry logic for metadata/upload sync.

## Nice To Have
- [ ] Add optional local transcription path (Whisper.cpp) with backend fallback.
- [ ] Complete Pro scheduler UX: publish scheduling, polling, and failure visibility.
- [ ] Implement licensing/config enforcement and plan-aware feature gating.
- [ ] Improve packaging/release UX (desktop artifacts, updater flow, telemetry opt-in).
