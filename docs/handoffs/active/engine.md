# Engine Agent Handoff

Milestone: Unified Engine AI + Cloud Delegation
Repo: `tv7-engine`
Generated from: `make handoff`

## Mission
Finish the unified Engine AI runtime boundary.

## Current State
- Branch: `main`
- Git status: 6 pending
- Pull request: none
- Focus: Milestone route: EN-A05-01-02, EN-A05-01-03, EN-A06-01-04, EN-A04-01-02. Latest sync focus outside this handoff: EN-A01-02-01: Replace stub media probing with real implementations and strong error handling. (next, tv7-core/docs/roadmaps/tv7-engine-roadmap.md)
- Resolved Focus: Working on `Replace stub media probing with real implementations and strong error handling.` (next EN-A01-02-01); 6 pending changes
- Roadmap counts: 11 completed, 0 required open, 15 other open.

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
-  M Cargo.lock
-  M Cargo.toml
-  M README.md
-  M engine-core/src/lib.rs
-  M engine-service/Cargo.toml
-  M engine-service/src/main.rs

Recent commits:
- d0fa941 Merge pull request #26 from TV7-Clip-Studio/refactor-engine-code
- bed8f44 refactor-engine-code: Migrate to tv7-engine, enhance build quality, and expand API testing
- 247028d Merge pull request #25 from TV7-Clip-Studio/engine-setup-1

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

## Deliverables
- Engine provides one AI execution/debug integration point for Studio.
- Capability readiness clearly separates local/offline capability from cloud-only availability.
- Engine OpenAPI and core contracts are updated in tv7-core.

## Completion Notes
- Generated handoff has no completion signals yet.
- Run `SYNC_INTERACTIVE=0 make sync` and `make handoff` after the agent reports completion.

## Copy/Paste Prompt
You are the Engine Agent. Work in tv7-engine. Use docs/handoffs/active/engine.md as your operating contract. Do not push. Implement only the assigned roadmap scope, keep contracts updated, and run the listed validation commands.
