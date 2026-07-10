# Backend Agent Handoff

Milestone: Unified Engine AI + Cloud Delegation
Repo: `tv7-backend`
Generated from: `make handoff`

## Mission
Finish the Backend cloud AI control plane for Engine delegation.

## Current State
- Branch: `main`
- Git status: 5 pending
- Pull request: none
- Focus: BE-A01-02-01: Finalize and document clip sync contract for Flutter desktop clients. (next, tv7-core/docs/roadmaps/tv7-backend-roadmap.md)
- Resolved Focus: Slice   : Finalize and document clip sync contract for Flutter desktop clients. (dirty)
    Roadmap : Finalize and document clip sync contract for Flutter desktop clients. (BE-A01-02-01)
    Changes : 5 pending changes
- Roadmap counts: 12 completed, 5 required open, 9 other open.

## Roadmap Items
- BE-A01-02-01
- BE-A01-02-02
- BE-A01-02-04
- BE-A01-02-05
- BE-A01-02-06
- BE-A01-02-07

## Contract References
- docs/contracts/tv7-engine/ai-provider-handoff.md
- docs/contracts/openapi/tv7-backend/openapi.json
- docs/roadmaps/tv7-backend-roadmap.md

## Current Code Signals
Detected state:
- Pending uncommitted cloud AI implementation exists; preserve and harden it.
- Engine token endpoint exists.
- Engine execution endpoint exists.
- Studio license readiness endpoint exists.

Dirty files:
-  M src/app/admin/routes.py
-  M src/app/templates/admin/base.html
-  M src/app/templates/admin/user_detail.html
-  M src/app/templates/admin/users.html
-  M tests/test_admin_routes_new.py

Recent commits:
- b542c13 tv7-backend: backend cloud AI control plane (#63)
- 4c0b23f Merge pull request #62 from TV7-Clip-Studio/naming-change-1
- 797141a naming-change-1:   [gemini metrics: model: gemini-2.5-flash, tokens: 9,197, time: 13.3s] Refactor debug and configuration handling
- 5a0a8a1 changes in naming
- 25062ea Merge pull request #33 from TV7-Clip-Studio/codex/batch-tv7-fastapi-backend-20260215-211329

## Tasks
- Preserve the pending cloud AI implementation; do not duplicate or rebuild it from scratch.
- Verify `GET /api/v1/auth/license` remains aligned with `/api/v1/cloud-ai/engine-token` account, license, cloud-AI, and credit readiness rules.
- Harden the existing Backend-issued short-lived Engine delegation tokens scoped to engine:cloud_ai.
- Harden the existing Engine-only cloud AI execution and provider error normalization.
- Keep DeepSeek/provider credentials, billing, quota, and cloud metering inside Backend.
- Expose admin visibility for cloud AI credit balance, usage, provider latency, and failures.
- Regenerate/update Backend OpenAPI after endpoint or schema changes.

## Constraints
- Do not add local media probing, transcription, rendering, or transcript scoring to Backend.
- Do not expose provider secrets in API payloads, logs, diagnostics, tests, or admin pages.
- Do not make Studio call Backend cloud AI execution or debug endpoints directly.

## Validation
- make deps
- make lint
- make type
- make test
- make testcov

## Human Validation
Queue status: pending

- Where: Studio login/license diagnostics and Backend /admin/cloud-ai
- Preconditions:
  1. Start Backend and Postgres.
  2. Use an active development user.
- Steps:
  1. Log in through Studio and confirm /api/v1/auth/license responds without a server error.
  2. Inspect cloud AI readiness with zero and positive credit balances.
  3. Request an Engine delegation token and verify normal user tokens cannot call Engine execution.
  4. Inspect /admin/cloud-ai for balances, request status, latency, and provider errors.
- Expected:
  1. No provider secret or prompt body appears in logs or responses.
  2. License, quota, and inactive-account states are stable and consistent across endpoints.
  3. Cloud AI metering records success and failure outcomes correctly.
- Known limitations:
  - None.

## Deliverables
- Backend endpoints and schemas are stable for Studio -> Backend token minting and Engine -> Backend execution.
- Credit and usage accounting are covered by tests and visible to admins.
- OpenAPI contract is updated in tv7-core.

## Completion Notes
- 2026-07-08: `GET /api/v1/auth/license` is detected as the Studio account/license/cloud-AI readiness endpoint.
- 2026-07-08: `/api/v1/cloud-ai/engine-token` is detected for Backend-issued Engine delegation.
- 2026-07-08: `/api/v1/cloud-ai/engine/execute` is detected as the Engine-only cloud AI execution endpoint.
- 2026-07-08: Cloud AI API tests are detected in `tests/test_cloud_ai_api.py`.
- 2026-07-08: Cloud AI credit/metering migration is detected.
- Follow-up: Studio should call `/api/v1/auth/license` for readiness and request `/api/v1/cloud-ai/engine-token` only when it needs a delegated token for Engine.
- Follow-up: Engine remains the only caller of `/api/v1/cloud-ai/engine/execute`.

## Copy/Paste Prompt
You are the Backend Agent. Work in tv7-backend. Use docs/handoffs/active/backend.md as your operating contract. Do not push. Implement only the assigned roadmap scope, keep contracts updated, and run the listed validation commands.
