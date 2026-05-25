# TV7 Axum Engine Roadmap

Roadmap Code: AX
Batch Code: A01

Last updated: 2026-05-21

## Done
- [X] [AX-A01-01-01] Created Rust workspace with `engine-core` and `engine-service` crates.
- [X] [AX-A01-01-02] Added initial `engine-core` media probing stub and basic workspace dependency setup.
- [X] [AX-A01-01-03] Documented local-first architecture intent (loopback sidecar, no business logic in engine).

## Epic AX-A01: Engine Foundation
- [ ] [AX-A01-02-01] Replace stub media probing with real implementations and strong error handling.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Current implementation probes via `ffprobe` and falls back to filesystem metadata. Harden output shape, command abstraction, and error semantics before Studio adopts it.
- [ ] [AX-A01-02-02] Build `engine-service` Axum HTTP surface to match expected local engine contract.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Existing surface has `/health` and `/v1/media/probe`; contract must expand for Studio-owned engine lifecycle and mandatory sidecar usage.
- [ ] [AX-A01-02-03] Add configuration/logging defaults (port, work dir, log level) and startup validation.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Validate loopback binding, absolute work dir, writable output dirs, and required local tools before accepting jobs.
- [ ] [AX-A01-02-04] Introduce trait-driven boundaries in core so service and future FFI integrations share logic.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Use explicit traits for probe, thumbnail, render, diagnostics, ingest, and transcript operations.
- [ ] [AX-A01-02-05] Add basic test coverage and command-level verification (`cargo check`, `cargo test`, `cargo clippy`).
    **BACKLOG** | Engine Agent | 2026-05-21 00:00

## Epic AX-A02: Mandatory Studio Sidecar Adoption
- [X] [AX-A02-01-01] Define the first Studio-facing Engine API contract for probe, thumbnail, render, diagnostics, and health.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Flutter Studio will use Engine as mandatory local media boundary once integrated. No direct `ffmpeg`/`ffprobe` fallback after adoption.
    - **NOTE**: Added Engine API contract and service implementation for `/health`, `/v1/diagnostics`, `/v1/media/probe`, `/v1/media/thumbnail`, and `/v1/media/render-clip`. Diagnostics require `ffmpeg`/`ffprobe` for AX-A02 and list `yt-dlp` only as a future `url_ingest` dependency.
- [X] [AX-A02-01-02] Implement `GET /v1/diagnostics` for Engine readiness and local dependency checks.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Studio startup should use diagnostics to decide whether the single app experience is ready or needs user-visible repair instructions.
    - **NOTE**: Diagnostics now report runtime version/host/port, configured `ffmpeg`/`ffprobe` availability, writable work dir state, degraded capability status, and future `yt-dlp` requirement without checking it for AX-A02.
- [X] [AX-A02-01-03] Implement `POST /v1/media/thumbnail` with deterministic path-based output.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Thumbnail generation accepts explicit absolute source/output paths, always overwrites output, validates path safety, and is covered by generated-video ffmpeg integration tests.
- [X] [AX-A02-01-04] Implement `POST /v1/media/render-clip` for frame-accurate local clip export.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Clip rendering accepts explicit absolute source/output paths, always overwrites output, validates path/range safety, and is covered by generated-video ffmpeg integration tests.
- [X] [AX-A02-01-05] Add contract examples and compatibility notes for Studio migration.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Studio integration should replace `ToolRunner.getMediaInfo`, `generateThumbnail`, and `renderClip` with Engine client calls.
    - **NOTE**: Added Core contract artifacts with Studio startup rules, diagnostics expectations, replacement map, request/response examples, and error code guidance. Archived handoff: `docs/handoffs/archived/engine-to-studio-sidecar-a02.md`. Migration guide hash: `75bd0d4f49fca3132e5bcff0febfcf4a8b3f4ad8a0379f4101400bb9038b46fd`.

## Epic AX-A03: Engine-Owned Ingest And Transcript Path
- [X] [AX-A03-01-01] Define Engine API for URL ingest, local file import normalization, and metadata capture.
    **COMPLETED** | Engine Agent | 2026-05-22 00:00
    - **CROSS-AGENT-NOTES**: Studio starts the Engine; Engine performs local media compute. Backend remains out of ingest/transcode/transcript processing.
    - **NOTE**: Added job-backed `/v1/ingest/url`, `/v1/transcripts/download`, and `/v1/jobs/{id}` contracts to Core OpenAPI and migration docs. Implemented first in-memory Engine job API surface for Studio consumption. Validated with `cargo test`, `cargo clippy --all-targets --all-features -- -D warnings`, and OpenAPI `jq`.
- [P] [AX-A03-01-02] Move `yt-dlp` metadata/download responsibilities into Engine with structured progress and errors.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **NOTE**: First implementation runs `yt-dlp` behind Engine for metadata and download, records coarse queued/running/completed/failed job state, and checks `yt-dlp` in diagnostics. Next hardening: real streamed progress/log capture, richer output path resolution, and cancellation.
- [P] [AX-A03-01-03] Move transcript discovery/download/normalization behind Engine APIs.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **NOTE**: First implementation runs transcript download behind Engine and returns the created VTT path through job result. Next hardening: transcript discovery, language selection details, and normalization output.

## Epic AX-A04: Jobs, Progress, Logs, And Cancellation
- [P] [AX-A04-01-01] Add a durable local job model for long-running Engine operations.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **NOTE**: Added initial in-memory job model for AX-A03 ingest/transcript jobs. Durability remains backlog within this item.
- [P] [AX-A04-01-02] Add job progress, log tailing, status polling, and cancellation endpoints.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **CROSS-AGENT-NOTES**: Studio should surface progress from Engine instead of parsing process output directly.
    - **NOTE**: Added `GET /v1/jobs/{id}` status polling, `GET /v1/jobs/{id}/logs`, and `POST /v1/jobs/{id}/cancel` with coarse logs and cooperative cancellation state. Process-level `yt-dlp` termination and streamed progress parsing remain to be implemented.

## Epic AX-A05: Local Transcription And Clip Intelligence
- [ ] [AX-A05-01-01] Add local transcription backend abstraction and model configuration.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Keep cloud/business policy out of Engine; Engine only executes configured local compute.
- [ ] [AX-A05-01-02] Add local clip detection interfaces for transcript-to-segment workflows.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Coordinate with Backend/Studio if cloud highlight APIs remain available for paid or fallback workflows.

## Epic AX-A06: Packaging, Distribution, And Future FFI
- [ ] [AX-A06-01-01] Package Engine binary for Studio-managed startup on desktop.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Studio must launch Engine automatically at app startup so TV7 behaves as one app for users.
- [ ] [AX-A06-01-02] Add benchmark harness for probe/transcode/transcription hot paths.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
- [ ] [AX-A06-01-03] Add `engine-ffi` crate stub for Flutter/mobile interoperability planning.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
- [ ] [AX-A06-01-04] Add feature flags for optional GPU acceleration and model backends.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
- [ ] [AX-A06-01-05] Publish a compatibility matrix for supported codecs, formats, and platform constraints.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
