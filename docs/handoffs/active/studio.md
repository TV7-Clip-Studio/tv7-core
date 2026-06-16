# Studio Agent Handoff

Milestone: Unified Engine AI + Cloud Delegation
Repo: `tv7-studio`
Generated from: `make handoff`

## Mission
Finish user-facing AI setup, diagnostics, and Engine-only AI calls.

## Current State
- Branch: `clip-editor-flow-1`
- Git status: local branch (rebased onto origin/main, 24 pending)
- Pull request: none
- Focus: ST-A01-02-01: Regenerate and adopt OpenAPI client against the current FastAPI contract. (next, tv7-core/docs/roadmaps/tv7-studio-roadmap.md)
- Resolved Focus: Working on `Regenerate and adopt OpenAPI client against the current FastAPI contract.` (next ST-A01-02-01); 24 pending changes including 3 untracked files
- Roadmap counts: 20 completed, 2 required open, 9 other open.

## Roadmap Items
- ST-A04-01-02
- ST-A04-01-04
- ST-A04-01-05
- ST-A01-02-01

## Contract References
- docs/contracts/tv7-engine/ai-provider-handoff.md
- docs/contracts/tv7-engine/runtime-setup.md
- docs/contracts/openapi/tv7-backend/openapi.json
- docs/contracts/openapi/tv7-engine/openapi.json
- docs/roadmaps/tv7-studio-roadmap.md

## Current Code Signals
Detected state:
- No semantic detector output for this repo.

Dirty files:
-  M AGENTS.md
-  M README.md
-  M forgotten_client/lib/app.dart
-  M forgotten_client/lib/bootstrap.dart
-  M forgotten_client/lib/data/api/api_client.dart
-  M forgotten_client/lib/data/local/engine_client.dart
-  M forgotten_client/lib/data/local/engine_job_poller.dart
-  M forgotten_client/lib/data/local/engine_process_manager.dart
-  M forgotten_client/lib/data/local/local_video_repository.dart
-  M forgotten_client/lib/data/local/media_service.dart
-  M forgotten_client/lib/data/local/studio_diagnostics_service.dart
-  M forgotten_client/lib/features/dashboard/dashboard_page.dart
-  M forgotten_client/lib/features/diagnostics/diagnostics_page.dart
-  M forgotten_client/lib/features/ingest/ingest_page.dart
-  M forgotten_client/test/data/api/api_client_test.dart
-  M forgotten_client/test/data/local/engine_client_test.dart
-  M forgotten_client/test/data/local/engine_job_poller_test.dart
-  M forgotten_client/test/data/local/engine_process_manager_test.dart
-  M forgotten_client/test/data/local/local_video_repository_test.dart
-  M forgotten_client/test/data/local/media_service_test.dart
-  M forgotten_client/test/data/local/studio_diagnostics_service_test.dart
- ?? forgotten_client/lib/data/api/safe_log_interceptor.dart
- ?? forgotten_client/lib/features/dashboard/quick_clip_preflight.dart
- ?? forgotten_client/test/features/dashboard/

Recent commits:
- 674793f Merge pull request #24 from TV7-Clip-Studio/clip-editor-update
- 4d627d3 code review changes
- 3622de9 code review changes III

## Tasks
- Use normal Backend auth/session flow to request an Engine cloud AI delegation token.
- Pass the delegated token to Engine over loopback and clear it on logout, revocation, or account changes.
- Call Engine for AI execution and AI diagnostics, including cloud debug.
- Display AI setup, quota, license, delegated-token, provider, and offline readiness states clearly.
- Regenerate/adopt API clients when Backend or Engine contracts change.

## Constraints
- Do not collect DeepSeek/OpenAI/provider keys from users.
- Do not call Backend cloud AI execution/debug endpoints directly from feature flows.
- Do not treat missing cloud delegation as an Engine startup failure.

## Validation
- make format
- make analyze
- make test
- make check

## Deliverables
- Studio has one AI feature integration surface: Engine.
- Diagnostics and first-run setup show actionable readiness states.
- Quick Clip and AI feature flows use Engine contracts only.

## Completion Notes
- Generated handoff has no completion signals yet.
- Run `SYNC_INTERACTIVE=0 make sync` and `make handoff` after the agent reports completion.

## Copy/Paste Prompt
You are the Studio Agent. Work in tv7-studio. Use docs/handoffs/active/studio.md as your operating contract. Do not push. Implement only the assigned roadmap scope, keep contracts updated, and run the listed validation commands.
