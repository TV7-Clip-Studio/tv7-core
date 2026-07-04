# Engine Agent Handoff

Milestone: Unified Engine AI + Cloud Delegation
Repo: `tv7-engine`
Generated from: `make handoff`

## Mission
Finish the unified Engine AI runtime boundary.

## Current State
- Branch: `main`
- Git status: clean
- Pull request: none
- Focus: Milestone route: EN-A05-01-02, EN-A05-01-03, EN-A06-01-04, EN-A04-01-02. Latest sync focus outside this handoff: EN-A01-02-01: Replace stub media probing with real implementations and strong error handling. (next, tv7-core/docs/roadmaps/tv7-engine-roadmap.md)
- Resolved Focus: Slice: Engine transcript generation contract
Roadmap: EN-A01-02-01: Replace stub media probing with real implementations and strong error handling.
Changes: No pending changes (repository is clean).
Signals: Current Git worktree is clean; semantic implementation signals require direct code inspection.
Next: Start EN-A01-02-01: Replace stub media probing with real implementations and strong error handling.
- Roadmap counts: 11 completed, 0 required open, 14 other open.

## Roadmap Items
- EN-A05-01-02
- EN-A05-01-03
- EN-A06-01-04
- EN-A04-01-02

## Contract References
- docs/contracts/tv7-engine/ai-provider-handoff.md
- docs/contracts/tv7-engine/runtime-setup.md
- docs/contracts/openapi/tv7-engine/openapi.json
- docs/roadmaps/tv7-engine-roadmap.md

## Current Code Signals
Detected state:
- No semantic detector output for this repo.

Dirty files:
- None.

Recent commits:
- 7f68789 tv7-engine: engine transcript generation contract (#27)
- d0fa941 Merge pull request #26 from TV7-Clip-Studio/refactor-engine-code
- bed8f44 refactor-engine-code: Migrate to tv7-engine, enhance build quality, and expand API testing
- 247028d Merge pull request #25 from TV7-Clip-Studio/engine-setup-1
- 73f9963 code review changes II

## Tasks
- Own provider dispatch for one Studio-facing AI surface.
- Keep Backend-issued cloud delegation tokens in memory only and clear them on request.
- Call Backend cloud AI execution only through the Engine-scoped delegated token.
- Normalize auth, license, quota, network, provider, and context-size failures for Studio.
- Expose setup/status and diagnostics readiness for ai and offline_creation without conflating them.
- Keep transcript intelligence provider-agnostic for Studio.

## Constraints
- Do not persist delegated cloud tokens.
- Do not own Backend credentials, billing, quota policy, or user auth storage.
- Do not make cloud AI readiness imply offline_creation readiness.

## Validation
- make fmt-check
- make check
- make test
- make clippy

## Human Validation
Queue status: pending

- Where: Studio > Diagnostics and Studio > Videos > Quick Clip
- Preconditions:
  1. Start Backend, Engine, and Studio from tv7-core.
  2. Keep transcription unconfigured for the setup-required check.
  3. Optionally configure TV7_ENGINE_WHISPER_BIN and TV7_ENGINE_WHISPER_MODEL for the success path.
- Steps:
  1. Open Diagnostics and confirm Engine health is ready while transcription readiness is not_ready.
  2. Open a local imported video without a transcript and launch Quick Clip.
  3. Confirm the app explains that transcript generation is supported after explicit transcription setup.
  4. When Whisper is configured, start transcript generation and poll the Engine job to completion.
- Expected:
  1. Missing setup produces TRANSCRIPTION_SETUP_REQUIRED without creating a job or downloading assets.
  2. Configured setup produces a transcript_generate job and a result.transcript_path VTT file.
  3. Engine health remains ready independently of transcription readiness.
- Known limitations:
  1. A missing Whisper runtime/model is an expected setup state, not a failed Engine implementation.

## Deliverables
- Engine provides one AI execution/debug integration point for Studio.
- Capability readiness clearly separates local/offline capability from cloud-only availability.
- Engine OpenAPI and core contracts are updated in tv7-core.

## Completion Notes
- Generated handoff has no completion signals yet.
- Run `SYNC_INTERACTIVE=0 make sync` and `make handoff` after the agent reports completion.

## Copy/Paste Prompt
You are the Engine Agent. Work in tv7-engine. Use docs/handoffs/active/engine.md as your operating contract. Do not push. Implement only the assigned roadmap scope, keep contracts updated, and run the listed validation commands.
