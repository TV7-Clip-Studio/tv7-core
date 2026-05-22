# TV7 Flutter Studio Roadmap

Roadmap Code: FL
Batch Code: A01

Last updated: 2026-05-21

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

## Epic FL-A02: Mandatory Engine Sidecar Adoption
- [X] [FL-A02-01-01] Add Studio-managed Engine process lifecycle at app startup.
    **COMPLETED** | Studio Agent | 2026-05-21 19:16
    - **CROSS-AGENT-NOTES**: Studio must launch the bundled Engine binary automatically so TV7 behaves as one app for users. Developers/users should not start Engine separately once integrated.
    - **NOTE**: Active handoff: `docs/core/handoffs/active/engine-to-studio-sidecar-a02.md`.
    - **NOTE**: Added Studio-owned Engine startup manager for `engine-service`, loopback env wiring, `/health` + `/v1/diagnostics` probing, degraded startup banner, process shutdown hooks, and focused mocked tests. Removed ingest-time direct shell dependency checks so readiness comes from Engine diagnostics. Validated with `make check`.
- [X] [FL-A02-01-02] Add Engine client and health/diagnostics integration.
    **COMPLETED** | Studio Agent | 2026-05-21 19:45
    - **CROSS-AGENT-NOTES**: Depends on Engine `AX-A02-01-01` and `AX-A02-01-02`. Use Engine diagnostics instead of direct dependency checks in Flutter.
    - **NOTE**: Consume Engine migration guide from `docs/core/contracts/tv7-axum-engine/studio-sidecar-migration.md`.
    - **NOTE**: Added reusable Engine client for `/health` and `/v1/diagnostics`, reused it from startup probing, and wired the app banner to refresh diagnostics from Engine without direct media dependency checks. Validated with `make check`.
- [ ] [FL-A02-01-03] Replace direct `ffprobe` usage with Engine probe API.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **NOTE**: Replace `ToolRunner.getMediaInfo` consumers after Engine contract is stable.
- [ ] [FL-A02-01-04] Replace direct thumbnail generation with Engine thumbnail API.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **NOTE**: Replace `ToolRunner.generateThumbnail` consumers.
- [ ] [FL-A02-01-05] Replace direct clip rendering with Engine render API.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **NOTE**: Replace `ToolRunner.renderClip` consumers. No direct `ffmpeg` fallback after migration.
- [ ] [FL-A02-01-06] Remove user-facing direct media tool dependency checks after Engine adoption.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **NOTE**: Keep user-facing remediation based on Engine diagnostics, not `which ffmpeg`/`which yt-dlp` calls from Flutter.
- [X] [FL-A02-01-07] Add Studio diagnostics pane for runtime visibility.
    **COMPLETED** | Studio Agent | 2026-05-21 20:08
    - **NOTE**: Add a third Diagnostics navigation item for Engine health, diagnostics endpoints, backend reachability, Studio config, workspace/runtime state, and recent app errors.
    - **NOTE**: Added Diagnostics tab with Engine `/health`, Engine `/v1/diagnostics`, backend users endpoint reachability, Studio config/runtime/workspace settings, and recent app errors. User directory failures now show a clearer account-unavailable state with Diagnostics access. Validated with `make check`.
- [X] [FL-A02-01-08] Add manual Engine endpoint smoke diagnostics.
    **COMPLETED** | Studio Agent | 2026-05-21 21:32
    - **NOTE**: Add manual endpoint checks with request/response previews for expected Engine endpoints. Keep exhaustive OpenAPI/contract validation in Engine; Studio diagnostics verify local wiring only.
    - **NOTE**: Added manual Diagnostics endpoint checks for `/health`, `/v1/diagnostics`, `/v1/media/probe`, `/v1/media/thumbnail`, and `/v1/media/render-clip` with method/path/status/latency plus expandable request/response previews. Media checks write only under the diagnostics workspace and are not run on normal refresh. Validated with `make check`.

## Epic FL-A03: Engine-Owned Ingest And Transcript Migration
- [ ] [FL-A03-01-01] Replace direct `yt-dlp` URL ingest with Engine ingest APIs.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Depends on Engine `AX-A03` APIs.
- [ ] [FL-A03-01-02] Replace direct transcript download and VTT normalization workflow with Engine transcript APIs.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **NOTE**: Studio remains responsible for UX and backend metadata sync; Engine owns local compute.
- [ ] [FL-A03-01-03] Surface Engine job progress, logs, and cancellation for long-running media work.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Depends on Engine `AX-A04` job APIs.

## Nice To Have
- [ ] [FL-A01-03-01] Add local transcription path through Engine.
    **BACKLOG** | Studio Agent | 2026-05-21 00:00
    - **NOTE**: Local media compute is mandatory through Engine after sidecar adoption; do not add direct Flutter `whisper.cpp` shell integration.
- [ ] [FL-A01-03-02] Complete Pro scheduler UX: publish scheduling, polling, and failure visibility.
- [ ] [FL-A01-03-03] Implement licensing/config enforcement and plan-aware feature gating.
- [ ] [FL-A01-03-04] Improve packaging/release UX (desktop artifacts, updater flow, telemetry opt-in).
