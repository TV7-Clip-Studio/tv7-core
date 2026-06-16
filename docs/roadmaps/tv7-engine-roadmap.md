# TV7 Engine Roadmap

Roadmap Code: EN
Batch Code: A01

Last updated: 2026-06-10

## Done
- [X] [EN-A01-01-01] Created Rust workspace with `engine-core` and `engine-service` crates.
- [X] [EN-A01-01-02] Added initial `engine-core` media probing stub and basic workspace dependency setup.
- [X] [EN-A01-01-03] Documented local-first architecture intent (loopback sidecar, no business logic in engine).

## Epic EN-A01: Engine Foundation
- [ ] [EN-A01-02-01] Replace stub media probing with real implementations and strong error handling.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Current implementation probes via `ffprobe` and falls back to filesystem metadata. Harden output shape, command abstraction, and error semantics before Studio adopts it.
- [ ] [EN-A01-02-02] Build `engine-service` Axum HTTP surface to match expected local engine contract.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Existing surface has `/health` and `/v1/media/probe`; contract must expand for Studio-owned engine lifecycle and mandatory sidecar usage.
- [ ] [EN-A01-02-03] Add configuration/logging defaults (port, work dir, log level) and startup validation.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Validate loopback binding, absolute work dir, writable output dirs, and required local tools before accepting jobs.
- [ ] [EN-A01-02-04] Introduce trait-driven boundaries in core so service and future FFI integrations share logic.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Use explicit traits for probe, thumbnail, render, diagnostics, ingest, and transcript operations.
- [X] [EN-A01-02-05] Add basic test coverage and command-level verification (`cargo check`, `cargo test`, `cargo clippy`).
    **COMPLETED** | Engine Agent | 2026-06-07 00:00
    - **NOTE**: Added pre-commit-enforced Rust quality gates through `make quality` for format, compile, tests, clippy, cargo-audit advisories, cargo-deny license/source policy, and file hygiene. Added focused core edge coverage, service config/job cancellation coverage, and OpenAPI route/status/required-payload contract alignment tests. Validated with `make quality` and `pre-commit run --all-files`.

## Epic EN-A02: Mandatory Studio Sidecar Adoption
- [X] [EN-A02-01-01] Define the first Studio-facing Engine API contract for probe, thumbnail, render, diagnostics, and health.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Studio will use Engine as mandatory local media boundary once integrated. No direct `ffmpeg`/`ffprobe` fallback after adoption.
    - **NOTE**: Added Engine API contract and service implementation for `/health`, `/v1/diagnostics`, `/v1/media/probe`, `/v1/media/thumbnail`, and `/v1/media/render-clip`. Diagnostics require `ffmpeg`/`ffprobe` for EN-A02 and list `yt-dlp` only as a future `url_ingest` dependency.
- [X] [EN-A02-01-02] Implement `GET /v1/diagnostics` for Engine readiness and local dependency checks.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Studio startup should use diagnostics to decide whether the single app experience is ready or needs user-visible repair instructions.
    - **NOTE**: Diagnostics now report runtime version/host/port, configured `ffmpeg`/`ffprobe` availability, writable work dir state, degraded capability status, and future `yt-dlp` requirement without checking it for EN-A02.
- [X] [EN-A02-01-03] Implement `POST /v1/media/thumbnail` with deterministic path-based output.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Thumbnail generation accepts explicit absolute source/output paths, always overwrites output, validates path safety, and is covered by generated-video ffmpeg integration tests.
- [X] [EN-A02-01-04] Implement `POST /v1/media/render-clip` for frame-accurate local clip export.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Clip rendering accepts explicit absolute source/output paths, always overwrites output, validates path/range safety, and is covered by generated-video ffmpeg integration tests.
- [X] [EN-A02-01-05] Add contract examples and compatibility notes for Studio migration.
    **COMPLETED** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Studio integration should replace `ToolRunner.getMediaInfo`, `generateThumbnail`, and `renderClip` with Engine client calls.
    - **NOTE**: Added Core contract artifacts with Studio startup rules, diagnostics expectations, replacement map, request/response examples, and error code guidance. Archived handoff: `docs/handoffs/archived/engine-to-studio-sidecar-a02.md`. Migration guide hash: `75bd0d4f49fca3132e5bcff0febfcf4a8b3f4ad8a0379f4101400bb9038b46fd`.

## Epic EN-A03: Engine-Owned Ingest And Transcript Path
- [X] [EN-A03-01-01] Define Engine API for URL ingest, local file import normalization, and metadata capture.
    **COMPLETED** | Engine Agent | 2026-05-22 00:00
    - **CROSS-AGENT-NOTES**: Studio starts the Engine; Engine performs local media compute. Backend remains out of ingest/transcode/transcript processing.
    - **NOTE**: Added job-backed `/v1/ingest/url`, `/v1/transcripts/download`, and `/v1/jobs/{id}` contracts to Core OpenAPI and migration docs. Implemented first in-memory Engine job API surface for Studio consumption. Validated with `cargo test`, `cargo clippy --all-targets --all-features -- -D warnings`, and OpenAPI `jq`.
- [P] [EN-A03-01-02] Move `yt-dlp` metadata/download responsibilities into Engine with structured progress and errors.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **NOTE**: First implementation runs `yt-dlp` behind Engine for metadata and download, records coarse queued/running/completed/failed job state, and checks `yt-dlp` in diagnostics. Next hardening: real streamed progress/log capture, richer output path resolution, and cancellation.
- [P] [EN-A03-01-03] Move transcript discovery/download/normalization behind Engine APIs.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **NOTE**: First implementation runs transcript download behind Engine and returns the created VTT path through job result. Next hardening: transcript discovery, language selection details, and normalization output.

## Epic EN-A04: Jobs, Progress, Logs, And Cancellation
- [P] [EN-A04-01-01] Add a durable local job model for long-running Engine operations.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **NOTE**: Added initial in-memory job model for EN-A03 ingest/transcript jobs. Durability remains backlog within this item.
- [P] [EN-A04-01-02] Add job progress, log tailing, status polling, and cancellation endpoints.
    **IN-PROGRESS** | Engine Agent | 2026-05-22 00:00
    - **CROSS-AGENT-NOTES**: Studio should surface progress from Engine instead of parsing process output directly.
    - **NOTE**: Added `GET /v1/jobs/{id}` status polling, `GET /v1/jobs/{id}/logs`, and `POST /v1/jobs/{id}/cancel` with coarse logs and cooperative cancellation state. Process-level `yt-dlp` termination and streamed progress parsing remain to be implemented.
    - **NOTE**: Studio contract now documents current cancellation behavior, path ownership, URL safety rules, and diagnostics expectations. Job IDs now use sequentially consistent atomic ordering to close review feedback, though atomic uniqueness did not depend on this ordering.
    - **NOTE**: Added a hard in-memory job cap in Engine service so terminal TTL cleanup is not the only protection against sustained job growth. Full child-process termination for in-flight `yt-dlp`/`ffmpeg` remains pending in EN-A04.

## Epic EN-A05: Local AI, Transcription, And Clip Intelligence
- [ ] [EN-A05-01-01] Add local transcription backend abstraction and model configuration.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **NOTE**: Keep cloud/business policy out of Engine; Engine executes configured local compute and reports exact model/runtime readiness to Studio.
- [ ] [EN-A05-01-02] Add AI provider configuration and runtime dispatch.
    **BACKLOG** | Engine Agent | 2026-06-03 00:00
    - **CROSS-AGENT-NOTES**: Studio should call Engine for AI work regardless of local/cloud provider. Engine owns provider selection at execution time, local model execution, prompt/context policy, and cloud request shaping. Backend owns TV7 cloud AI credentials, authorization, billing, and metering.
    - **NOTE**: Support one user-facing `ai` capability resolved through provider candidates in order: user local provider such as Ollama, TV7-managed local model, then TV7 cloud AI via Backend. Studio must not collect user DeepSeek credentials.
    - **NOTE**: For TV7 cloud AI, accept short-lived Backend-issued delegation context from Studio, keep it in memory only, and call Backend with Engine-scoped auth. Normalize auth/license/quota/network/provider errors for Studio.
    - **NOTE**: First plumbing added `POST /v1/ai/cloud-token`, `DELETE /v1/ai/cloud-token`, in-memory delegated token storage, Backend `/api/v1/cloud-ai/engine/execute` client boundary, cloud debug error normalization, and first provider-agnostic execution dispatch via `POST /v1/ai/transcript-intelligence`. Follow-up remains: local provider execution dispatch for Ollama/TV7-managed local AI.
- [ ] [EN-A05-01-03] Add transcript intelligence APIs for unified Engine AI providers.
    **BACKLOG** | Engine Agent | 2026-06-03 00:00
    - **NOTE**: Engine should own transcript chunking, summarization, clip suggestion scoring, prompt templates, model-specific request shaping, and structured outputs consumed by Studio. Studio-facing API shape should stay the same whether the provider is local, TV7-managed local, or TV7 cloud AI.
    - **NOTE**: Added initial `POST /v1/ai/transcript-intelligence` contract and cloud-backed execution path returning structured clip suggestions. Follow-up remains: richer transcript chunking/scoring, local provider execution, and production prompt hardening.
- [ ] [EN-A05-01-04] Add post copy generation APIs for selected clips.
    **BACKLOG** | Engine Agent | 2026-06-03 00:00
    - **NOTE**: Generate platform-aware titles, hooks, descriptions, captions, hashtags, and variants from selected clips/transcripts while reporting provider/model used.
- [ ] [EN-A05-01-05] Add local clip detection interfaces for transcript-to-segment workflows.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Coordinate with Studio on UX and with Backend only for publishing/scheduling boundaries. Backend must not own local transcript analysis or clip scoring.

## Epic EN-A06: Packaging, First-Run Setup, Distribution, And Future FFI
- [ ] [EN-A06-01-01] Package Engine binary for Studio-managed startup on desktop.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Studio must launch Engine automatically at app startup so TV7 behaves as one app for users.
- [X] [EN-A06-01-02] Define Engine-managed runtime asset manifest and setup contract.
    **COMPLETED** | Engine Agent | 2026-06-03 00:00
    - **CROSS-AGENT-NOTES**: Studio first-run setup calls Engine setup APIs and displays one AI capability backed by provider candidates. Engine installs/verifies approved local runtime assets and reports progress/readiness.
    - **NOTE**: Track Engine binary version, media tools (`ffmpeg`, `ffprobe`, `yt-dlp`), Whisper runtime/model assets, local LLM runtime/model assets, checksums, disk requirements, and install locations. No silent startup downloads.
    - **NOTE**: Added `docs/contracts/tv7-engine/runtime-setup.md` defining AI provider candidates, runtime asset categories, capability readiness groups, setup endpoint drafts, download/verification rules, fresh-install expectations, and privacy constraints. Linked it from the Core contracts index.
- [ ] [EN-A06-01-03] Add Engine setup/download job APIs for first-run local asset installation.
    **BACKLOG** | Engine Agent | 2026-06-03 00:00
    - **NOTE**: Support explicit user-confirmed downloads, progress/logs, retry/resume where practical, checksum validation, disk-space failures, partial download cleanup, and setup-complete status.
- [P] [EN-A06-01-04] Extend diagnostics with capability readiness groups.
    **IN-PROGRESS** | Engine Agent | 2026-06-09 00:00
    - **CROSS-AGENT-NOTES**: Studio diagnostics should distinguish app/Engine health from capability readiness. Missing local LLM, missing Whisper model, missing cloud delegation/license, quota exhaustion, or cloud provider offline states should be shown as feature setup states, not Engine startup failure.
    - **NOTE**: Report `media_core`, `url_ingest`, `transcription`, `ai`, `rendering`, and `offline_creation` readiness with exact missing assets/configuration.
    - **NOTE**: Added first setup readiness resolver and `/v1/setup/{manifest,status}` endpoints. Engine now reports one `ai` capability with provider candidates in order: Ollama/user local, TV7-managed local model, then TV7 cloud AI via Backend. Cloud AI can make `ai` ready only when a valid delegated Engine token is present, but must not make `offline_creation` ready. Added `POST /v1/ai/cloud-debug` for the Studio -> Engine -> Backend cloud AI debug path. Follow-up: fold all capability groups into `/v1/diagnostics` and add mutating setup/download jobs.
- [ ] [EN-A06-01-05] Add benchmark harness for probe/transcode/transcription/LLM hot paths.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
- [ ] [EN-A06-01-06] Add `engine-ffi` crate stub for Flutter/mobile interoperability planning.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
- [ ] [EN-A06-01-07] Add feature flags for optional GPU acceleration and model backends.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00
- [ ] [EN-A06-01-08] Publish a compatibility matrix for supported codecs, formats, AI runtimes, and platform constraints.
    **BACKLOG** | Engine Agent | 2026-05-21 00:00

## Cross-Repo Milestone: Unified Engine AI + Cloud Delegation
- **Active handoff**: `docs/handoffs/active/engine.md`
- **Engine route**: Own the unified Studio-facing AI boundary: provider dispatch, in-memory cloud delegation token handling, Backend cloud request shaping, AI diagnostics, capability readiness, and transcript intelligence.
- **Primary roadmap items**: `EN-A05-01-02`, `EN-A05-01-03`, `EN-A06-01-04`, `EN-A04-01-02`.
- **Boundary**: Engine must not own Backend credentials, billing, quota policy, long-lived user auth storage, or Studio setup UX.
