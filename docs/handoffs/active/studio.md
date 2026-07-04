# Studio Agent Handoff

Milestone: Unified Engine AI + Cloud Delegation
Repo: `tv7-studio`
Generated from: `make handoff`

## Mission
Finish user-facing AI setup, diagnostics, and Engine-only AI calls.

## Current State
- Branch: `main`
- Git status: clean
- Pull request: none
- Focus: ST-A01-02-01: Regenerate and adopt OpenAPI client against the current FastAPI contract. (next, tv7-core/docs/roadmaps/tv7-studio-roadmap.md)
- Resolved Focus: Slice: Regenerate and adopt OpenAPI client against the current FastAPI contract.
Roadmap: ST-A01-02-01: Regenerate and adopt OpenAPI client against the current FastAPI contract.
Changes: No pending changes (repository is clean).
Signals: Quick Clip flow and diagnostics integration already exist; preserve and validate them.
Next: Preserve the existing Quick Clip flow while regenerating the OpenAPI client and adapting it to match the FastAPI contract.
- Roadmap counts: 21 completed, 2 required open, 8 other open.

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
- None.

Recent commits:
- a07e47c tv7-studio: studio Quick Clip and diagnostics integration (#26)
- f8a4717 Merge pull request #25 from TV7-Clip-Studio/clip-editor-flow-1
- 2917857 chore: resolve DeepSeek review findings
- de64024 tv7-studio: studio Quick Clip and diagnostics integration
- 674793f Merge pull request #24 from TV7-Clip-Studio/clip-editor-update

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

## Human Validation
Queue status: pending

- Where: Studio > Videos > Quick Clip and Studio > Diagnostics
- Preconditions:
  1. Start Backend, Engine, and Studio from tv7-core.
  2. Use a local imported video without a transcript.
- Steps:
  1. Open Quick Clip for the local video.
  2. Verify the setup-required message and its Diagnostics/setup action.
  3. With Engine transcription configured, start generation and observe job progress.
  4. Confirm the generated transcript is attached and Quick Clip becomes available.
- Expected:
  1. Studio never runs transcription tools directly.
  2. Setup-required, progress, success, and failure states are actionable and do not crash the app.
  3. Diagnostics agrees with the Quick Clip readiness state.
- Known limitations:
  1. Without configured Whisper assets, only the setup-required path can pass.

## Deliverables
- Studio has one AI feature integration surface: Engine.
- Diagnostics and first-run setup show actionable readiness states.
- Quick Clip and AI feature flows use Engine contracts only.

## Completion Notes
- Generated handoff has no completion signals yet.
- Run `SYNC_INTERACTIVE=0 make sync` and `make handoff` after the agent reports completion.

## Copy/Paste Prompt
You are the Studio Agent. Work in tv7-studio. Use docs/handoffs/active/studio.md as your operating contract. Do not push. Implement only the assigned roadmap scope, keep contracts updated, and run the listed validation commands.
