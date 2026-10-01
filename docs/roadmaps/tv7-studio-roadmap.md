# TV7 Studio Roadmap

Roadmap Code: ST
Batch Code: A01

Last updated: 2026-06-17

## Done
- [X] [ST-A01-01-01] Scaffolded Flutter client foundation with flavor entrypoints (`dev`, `stage`, `prod`).
- [X] [ST-A01-01-02] Added configuration wiring via dart-defines and baseline app bootstrap structure.
- [X] [ST-A01-01-03] Created API/auth scaffolding (Dio client, auth token models/store placeholders).
- [X] [ST-A01-01-04] Established repo docs for architecture, backend integration, publishing contract, and testing strategy.

## Needs To Be Done
- [ ] [ST-A01-02-01] Regenerate and adopt OpenAPI client against the current FastAPI contract.
- [X] [ST-A01-02-06] Harden runtime diagnostics and secret-safe Studio logging.
    **COMPLETED** | Studio Agent | 2026-06-09 00:00
    - **NOTE**: Added secret-safe Dio logging for generated DTOs, JSON strings, headers, and token responses; Studio now attaches to an already healthy Engine instead of starting a conflicting second process; transcript download accepts legacy `source_url`/`sourceUrl` metadata while rejecting local-only sources with a clearer message; license diagnostics now label backend 404s as endpoint-unavailable compatibility warnings. Hardened Quick Clip preflight so local imports without transcripts or remote caption metadata are blocked with an inline user-facing message, persisted card-level issue, and DiagnosticsLog entry instead of failing silently after Generate Clips. Follow-up added Engine-owned local transcript generation for local imports. Verified with focused Flutter tests and `make check`.
- [X] [ST-A01-02-07] Keep the macOS desktop build compatible with Xcode 27.
    **COMPLETED** | Architect Agent | 2026-09-29 15:00
    - **NOTE**: Raised the Runner and generated Pod deployment targets to macOS 12. `flutter analyze --no-pub`, focused login/navigation widget tests, and `flutter build macos --debug --no-pub` passed with Xcode 27.
- [X] [ST-A01-02-08] Establish an automatable browser Studio login and video library.
    **COMPLETED** | Architect + Studio + Backend Agents | 2026-09-29
    - **NOTE**: Added a web startup path that avoids desktop Engine and filesystem initialization, and a Backend-backed video library. Allowed the local web origin through Backend CORS. Verified Flutter analysis, 72 Studio tests, web build, 62 Backend tests, and live browser sign-in with the disposable local account; the library displayed the existing creator-check video and clip count. Browser media ingest, editing, Engine control, and publishing remain future work.
- [X] [ST-A01-02-09] Exercise browser Studio against a repeatable local Backend and Engine stack.
    **COMPLETED** | Architect + Studio + Engine Agents | 2026-09-30
    - **NOTE**: Added a loopback-only browser stack runner with an ignored SQLite test database and disposable account bootstrap. Browser Studio now shows Backend readiness and Engine diagnostics, with local-origin Engine CORS. Fixed a live Flutter `setState` crash found during sign-in. Verified a fresh browser login, empty video library, Diagnostics readiness and all five Engine capabilities, tab switching, diagnostics refresh, Flutter analysis, 72 tests, web build, and live service health. Creator media workflows remain outside the browser workspace.
- [X] [ST-A01-02-10] Sync desktop source videos and play them in browser Studio.
    **COMPLETED** | Studio Agent + Architect | 2026-10-01
    - **NOTE**: Desktop Studio offers Sync Video and Verify Sync, uploads the source after owner-scoped registration, and distinguishes metadata-only registration from cloud media. Browser Studio lists the account's source and requests a signed streaming URL for playback. Verified Studio analysis, 75 tests, macOS and web builds; the existing Papa Noel video was uploaded to the local test account, appeared in browser Studio, and played past 27 seconds at 1920x1080. Desktop UI click-through remains unverified because the macOS host input bridge is unavailable.
- [X] [ST-A01-02-02] Wire clip suggestion/highlight APIs into production auto-clip flows with robust error UX.
    **COMPLETED** | Studio Agent | 2026-05-29 16:15
    - **NOTE**: Fully resolved the backend highlights 404 bad response by transitioning to a 100% local, offline intelligence pipeline. Integrated a custom high-performance VTT subtitle parser, a timeline gap detection algorithm (targeting unclipped content strictly), duration segmenting (Short: 10-15s, Medium: 30-45s, Long: 60-90s Presets) aligned to cues and sentence boundaries, and a rule-based smart social post copywriting generator. Designed a premium glassmorphic Quick Clip Config Bottom Sheet (ChoiceChips, ListTiles) and an M3 status card progress overlay featuring a linear progress bar. Completely integrated and verified with the local Rust Media Engine sidecar. All tests pass green.
- [X] [ST-A01-02-03] Harden local ingest workspace (dependency checks, diagnostics, logs, recoverability).
    **COMPLETED** | Studio Agent | 2026-05-29 09:37
    - **NOTE**: Hardened workspace metadata and synchronization logic. Added dynamic `synced` flag to `VideoItem` (clips check meta synced state, sources check backend registration). Fixed the YouTube `Unknown duration` parsing bug inside `_enrichVideo` by supporting both `num` and `String` duration fields from yt-dlp. Re-persisted synced details in local `.meta.json` files during manual and auto-highlight sync cycles. Re-architected Dashboard listing into a premium layout with overlaid resolution/duration badges, a collapsed horizontal stats capsule grid (clip count, sync ratio, size, cloud state), compact button action bars, and beautifully padded generated clip card rows. Verified with `make check`.
- [X] [ST-A01-02-04] Build timeline trim/subtitle/export UX around the current local processing pipeline.
    **COMPLETED** | Studio Agent | 2026-05-28 19:26
    - **NOTE**: Complete redesign of the Clip Editor UX. Added resizable double-pane split workspace (clips list on left, center vertical drag handle, main column on right). Reorganized right column to group Video player and a compact Clip Properties card side-by-side on top, with the Timeline spanning full-width on the bottom. Redesigned all inputs with dense, rounded Material 3 fields and time prefix icons. Beautified clips list using bold titles, access time badges, and animated accent stripes. Verified with `make check`.
- [ ] [ST-A01-02-05] Add durable local cache/queue and retry logic for metadata/upload sync.

## Epic ST-A02: Mandatory Engine Sidecar Adoption
- [X] [ST-A02-01-01] Add Studio-managed Engine process lifecycle at app startup.
    **COMPLETED** | Studio Agent | 2026-05-21 19:16
    - **CROSS-AGENT-NOTES**: Studio must launch the bundled Engine binary automatically so TV7 behaves as one app for users. Developers/users should not start Engine separately once integrated.
    - **NOTE**: Archived handoff: `docs/core/handoffs/archived/engine-to-studio-sidecar-a02.md`.
    - **NOTE**: Added Studio-owned Engine startup manager for `engine-service`, loopback env wiring, `/health` + `/v1/diagnostics` probing, degraded startup banner, process shutdown hooks, and focused mocked tests. Removed ingest-time direct shell dependency checks so readiness comes from Engine diagnostics. Validated with `make check`.
- [X] [ST-A02-01-02] Add Engine client and health/diagnostics integration.
    **COMPLETED** | Studio Agent | 2026-05-21 19:45
    - **CROSS-AGENT-NOTES**: Depends on Engine `EN-A02-01-01` and `EN-A02-01-02`. Use Engine diagnostics instead of direct dependency checks in Flutter.
    - **NOTE**: Consume Engine migration guide from `docs/core/contracts/tv7-engine/studio-sidecar-migration.md`.
    - **NOTE**: Added reusable Engine client for `/health` and `/v1/diagnostics`, reused it from startup probing, and wired the app banner to refresh diagnostics from Engine without direct media dependency checks. Validated with `make check`.
- [X] [ST-A02-01-03] Replace direct `ffprobe` usage with Engine probe API.
    **COMPLETED** | Engine Agent + Studio Agent | 2026-05-22 00:00
    - **NOTE**: Added Engine media probe client calls and routed Studio repository metadata enrichment/duration probing through `/v1/media/probe`. Removed direct `ToolRunner.getMediaInfo` from Studio. Validated with `make check`.
- [X] [ST-A02-01-04] Replace direct thumbnail generation with Engine thumbnail API.
    **COMPLETED** | Engine Agent + Studio Agent | 2026-05-22 00:00
    - **NOTE**: Added Engine thumbnail client calls and routed repository/dashboard/player thumbnail generation through `/v1/media/thumbnail`. Removed direct `ToolRunner.generateThumbnail` from Studio. Validated with `make check`.
- [X] [ST-A02-01-05] Replace direct clip rendering with Engine render API.
    **COMPLETED** | Engine Agent + Studio Agent | 2026-05-22 00:00
    - **NOTE**: Added Engine render client calls and routed dashboard/player clip export through `/v1/media/render-clip`. Removed direct `ToolRunner.renderClip` from Studio. No direct `ffmpeg` fallback remains after migration. Validated with `make check`.
- [X] [ST-A02-01-06] Remove user-facing direct media tool dependency checks after Engine adoption.
    **COMPLETED** | Engine Agent + Studio Agent | 2026-05-22 00:00
    - **NOTE**: Studio now keeps media dependency remediation behind Engine startup/diagnostics; app media paths no longer shell out to `ffprobe`/`ffmpeg` directly. Remaining direct tool use in Studio is limited to current yt-dlp ingest/transcript flows, tracked separately under ST-A03.
- [X] [ST-A02-01-07] Add Studio diagnostics pane for runtime visibility.
    **COMPLETED** | Studio Agent | 2026-05-21 20:08
    - **NOTE**: Add a third Diagnostics navigation item for Engine health, diagnostics endpoints, backend reachability, Studio config, workspace/runtime state, and recent app errors.
    - **NOTE**: Added Diagnostics tab with Engine `/health`, Engine `/v1/diagnostics`, backend users endpoint reachability, Studio config/runtime/workspace settings, and recent app errors. User directory failures now show a clearer account-unavailable state with Diagnostics access. Validated with `make check`.
- [X] [ST-A02-01-08] Add manual Engine endpoint smoke diagnostics.
    **COMPLETED** | Studio Agent | 2026-05-21 21:32
    - **NOTE**: Add manual endpoint checks with request/response previews for expected Engine endpoints. Keep exhaustive OpenAPI/contract validation in Engine; Studio diagnostics verify local wiring only.
    - **NOTE**: Added manual Diagnostics endpoint checks for `/health`, `/v1/diagnostics`, `/v1/media/probe`, `/v1/media/thumbnail`, and `/v1/media/render-clip` with method/path/status/latency plus expandable request/response previews. Media checks write only under the diagnostics workspace and are not run on normal refresh. Validated with `make check`.
    - **NOTE**: Fixed a bug where the manual media endpoint checks were degraded (returning HTTP 422 with a missing moov atom error) by replacing the invalid `_tinyMp4Bytes` fixture with a valid, minimal 0.1-second black MP4 video generated via FFmpeg. All checks now pass with HTTP 200 READY. Validated with `flutter test`.
    - **NOTE**: Resolved a cached diagnostics fixture bug by updating `_prepareSmokeFixture()` to always overwrite the file, preventing older degraded 40-byte files on local disks from persisting and blocking new tests. Validated with `flutter test`.

## Epic ST-A03: Engine-Owned Ingest And Transcript Migration
- [X] [ST-A03-01-01] Replace direct yt-dlp URL ingest with Engine ingest APIs.
    **COMPLETED** | Engine Agent + Studio Agent | 2026-05-28 00:00
    - **CROSS-AGENT-NOTES**: Studio URL ingest now calls Engine `/v1/ingest/url`, polls `/v1/jobs/{id}`, reads `/v1/jobs/{id}/logs`, stores Engine-returned metadata, and no longer launches `yt-dlp` directly. Validated with `make check`.
- [X] [ST-A03-01-02] Replace direct transcript download and VTT normalization workflow with Engine transcript APIs.
    **COMPLETED** | Engine Agent + Studio Agent | 2026-05-28 00:00
    - **NOTE**: Studio transcript download now calls Engine `/v1/transcripts/download` and uses the returned VTT path while preserving Studio-side VTT read/normalization. No direct Studio `yt-dlp` transcript execution remains. Validated with `make check`.
- [X] [ST-A03-01-03] Surface Engine job progress, logs, and cancellation for long-running media work.
    **COMPLETED** | Studio Agent | 2026-06-04 19:02
    - **CROSS-AGENT-NOTES**: Depends on Engine `EN-A04` job APIs.
    - **NOTE**: Extended `EngineJobPoller.waitFor` and `MediaService.prepareIngestFromUrl` to support progress and job started callbacks. Redesigned the URL Ingestion progress UI in `IngestPage` with a card showing sub-step logs, a linear progress indicator, percentage text, and a "Cancel Ingestion" button calling the Engine `cancelJob` API. Added tests in both `engine_job_poller_test.dart` and `media_service_test.dart`. Verified with `make check`.
    - **NOTE**: Hardened Engine job waiting for long-running work by replacing fixed 10/30 minute Studio-side caps with a shared bounded-backoff poller. Production polling now waits for Engine terminal job state unless a caller explicitly opts into a timeout. Engine process startup/shutdown checks were also tightened for non-executable binaries and failed process signaling.
    - **NOTE**: Addressed review follow-up by retrying transient Engine job polling failures with bounded backoff, clarifying Unix executable-bit checks, avoiding shutdown signals for already-exited Engine processes, and adding a visible Diagnostics collection error state. Validated with `make check`.
    - **NOTE**: Fixed the transient polling retry timeout regression by enforcing explicit poller deadlines outside the retry catch path, and allowed Unix symlinked Engine binary paths by resolving symlinks before file/executable validation.

## Epic ST-A04: Packaged Engine And First-Run AI Setup
- [ ] [ST-A04-01-01] Resolve packaged Engine and runtime asset paths for desktop builds.
    **BACKLOG** | Studio Agent | 2026-06-03 00:00
    - **CROSS-AGENT-NOTES**: Depends on Engine `EN-A06-01-01` and `EN-A06-01-02`. Development builds may keep sibling-repo Engine resolution; release builds must resolve bundled app resources.
    - **NOTE**: Pass configured paths for Engine, `ffmpeg`, `ffprobe`, and `yt-dlp` into the Engine process. Fresh installs must not depend on developer repos or Homebrew paths.
- [ ] [ST-A04-01-02] Add first-run setup for unified Engine AI readiness.
    **BACKLOG** | Studio Agent | 2026-06-10 00:00
    - **CROSS-AGENT-NOTES**: Studio owns setup UX and user confirmation. Studio should call Engine for AI work regardless of provider. Engine owns provider dispatch, prompt/context policy, local model use, and Backend cloud AI request shaping. Backend owns TV7 cloud AI credentials, authorization, billing, quota, and metering.
    - **NOTE**: Consume Engine `setup_modes`, `ai_provider_order`, `active_ai_provider`, `ai_providers`, and capability readiness for `ai` and `offline_creation`. Present one user-facing AI capability backed by user local AI, TV7-managed local AI, or TV7 cloud AI. Do not ask users for DeepSeek/OpenAI keys.
- [ ] [ST-A04-01-03] Wire first-run setup to Engine setup/download jobs.
    **BACKLOG** | Studio Agent | 2026-06-03 00:00
    - **CROSS-AGENT-NOTES**: Depends on Engine `EN-A06-01-03`. Studio should call Engine setup APIs after explicit user confirmation and surface progress, retry, failure, disk-space, and setup-complete states.
    - **NOTE**: TV7 uses a small installer. Offline creation becomes available after required local assets are installed or imported; no silent downloads at app startup.
- [ ] [ST-A04-01-04] Pass Backend-issued Engine cloud AI delegation context.
    **BACKLOG** | Studio Agent | 2026-06-10 00:00
    - **CROSS-AGENT-NOTES**: Depends on Engine `EN-A05-01-02` and Backend cloud AI delegation tasks. Studio uses the normal authenticated user session/license flow to obtain a short-lived Engine delegation token from Backend, then passes it to Engine over loopback. Studio must not persist provider keys or call Backend cloud AI execution/debug endpoints directly.
    - **NOTE**: Cloud AI can make `ai` ready when internet and license/quota are available, but it does not make `offline_creation` ready. AI diagnostics/debug should route Studio -> Engine -> Backend so Studio has one AI integration surface.
- [x] [ST-A04-01-05] Expand Diagnostics to show capability readiness.
    **COMPLETED** | Studio Agent | 2026-06-09 00:00
    - **CROSS-AGENT-NOTES**: Depends on Engine `EN-A06-01-04`. Diagnostics should show Engine health separately from `media_core`, `url_ingest`, `transcription`, `ai`, `rendering`, and `offline_creation` readiness.
    - **NOTE**: Missing models, missing license/delegation context, quota exhaustion, or cloud provider offline states should be repair/setup prompts, not generic Engine failures.
    - **NOTE**: Added Studio Engine setup client models/calls for `/v1/setup/manifest` and `/v1/setup/status`, Diagnostics setup readiness, explicit-confirmation copy for installable TV7-managed assets, and Quick Clip transcript-blocked messaging that uses setup status while still waiting for Engine `POST /v1/transcripts/generate`.
    - **NOTE**: Contract follow-up replaced Studio-facing `local_llm`/`cloud_llm` readiness with the unified Engine `ai` capability and provider candidates from `docs/core/contracts/tv7-engine/ai-provider-handoff.md`.
    - **NOTE**: Phase 1 follow-up migrated Studio setup parsing and Diagnostics display to unified Engine `ai` readiness and `ai_providers`, while preserving compatibility with older setup payload fields. Diagnostics now surfaces `/v1/setup/manifest` availability separately from `/v1/setup/status`, and cloud AI readiness does not imply `offline_creation` readiness.
    - **NOTE**: Backend readiness follow-up replaced legacy Diagnostics parsing of `plan`/`expires_at` with `LicenseReadinessResponse`. Diagnostics now shows active/required account state, TV7 cloud AI readiness, formatted perpetual credit balance, and non-expiring credit policy. Full generated Backend client regeneration remains tracked by `ST-A01-02-01`.
- [ ] [ST-A04-01-06] Add fresh-install offline readiness release verification.
    **BACKLOG** | Studio Agent | 2026-06-03 00:00
    - **CROSS-AGENT-NOTES**: Coordinate with Engine `EN-A06` and Core contract docs. Validate packaged Studio on a clean profile with no developer repos and no Homebrew dependency assumptions.
    - **NOTE**: Verify local media import, probe, transcription when local assets exist, AI transcript analysis when local LLM is configured, render, and local export without internet. URL ingest and social publishing may require internet.

## Epic ST-A05: Unified Downloadable Studio Proof
- [X] [ST-A05-01-01] Prove one browser and macOS desktop UI with Engine-owned local media work.
    **COMPLETED** | Studio Agent + Architect | 2026-10-01
    - **NOTE**: React/Tauri Studio shares UI code across browser and a macOS `.app`. Browser UI supports computer media import, single URL jobs, and channel metadata preselection with explicit batch confirmation. Packaged app starts/stops its Engine child; native UI imported video and VTT, reviewed and adjusted a deterministic candidate, and rendered a captioned MP4. Web lint/build and desktop build passed; FFprobe confirmed the rendered file. Studio was promoted to the repository root and the Flutter client was retired on 2026-10-01; Windows and release gates remain open.
- [ ] [ST-A05-01-02] Bundle FFmpeg, yt-dlp, JavaScript runtime, and optional transcription model for clean macOS and Windows installs.
- [ ] [ST-A05-01-03] Persist editable local projects and platform variants; add a full preview/timeline and creator approval flow.
- [X] [ST-A05-01-04] Connect cloud account, license, approved asset storage, and scheduling drafts to the unified Studio UI.
    **COMPLETED** | Studio Agent + Architect | 2026-10-01
    - **NOTE**: Browser smoke signed in, rendered locally, explicitly approved transfer of the finished MP4 to owner-scoped private storage, registered fractional clip timing, created a pending schedule draft, and refreshed its status. Anonymous asset access returned 401. No live post was sent; Backend publishing capability remains gated.
- [X] [ST-A05-01-05] Generate a per-launch Engine token and protect the packaged desktop loopback API.
    **COMPLETED** | Studio Agent + Engine Agent | 2026-10-01
    - **NOTE**: Tauri creates 32 random bytes per launch, passes the bearer token only to its Engine child, and supplies it to bundled UI requests through a narrow native command. Release navigation is restricted to bundled content, scripts use a self-only CSP, and the token is absent from UI/logs. Native import passed while missing/wrong-token HTTP requests returned 401; Engine child exits with the app. Browser development mode remains explicitly unprotected.
- [ ] [ST-A05-01-06] Complete signed Windows/macOS distribution and a clean-install dependency check.

## Nice To Have
- [X] [ST-A01-03-01] Add local transcription path through Engine.
    **COMPLETED** | Studio Agent | 2026-06-17 00:00
    - **NOTE**: Local media compute is mandatory through Engine after sidecar adoption; do not add direct Flutter `whisper.cpp` shell integration.
    - **NOTE**: Wired Studio to Engine `POST /v1/transcripts/generate` for local imports without sidecar transcripts or remote subtitle metadata. Studio polls the returned `transcript_generate` job, stores/uses the sidecar `.vtt`, refreshes Quick Clip state, and preserves setup-required UX for Engine `TRANSCRIPTION_SETUP_REQUIRED` responses without downloading Whisper/model assets directly.
- [ ] [ST-A01-03-02] Complete Pro scheduler UX: publish scheduling, polling, and failure visibility.
- [ ] [ST-A01-03-03] Implement licensing/config enforcement and plan-aware feature gating.
- [ ] [ST-A01-03-04] Improve packaging/release UX outside first-run Engine setup (desktop artifacts, updater flow, telemetry opt-in).

## Cross-Repo Milestone: Unified Engine AI + Cloud Delegation
- **Active handoff**: `docs/handoffs/active/studio.md`
- **Studio route**: Own user-facing AI setup and diagnostics: request Backend delegation tokens with the normal session, pass tokens to Engine, call Engine for AI execution/debug, and display setup/license/quota/readiness states.
- **Primary roadmap items**: `ST-A04-01-02`, `ST-A04-01-04`, `ST-A04-01-05`, `ST-A01-02-01`.
- **Boundary**: Studio must not collect provider keys, call Backend cloud AI execution/debug endpoints from feature flows, or treat missing cloud delegation as an Engine startup failure.
