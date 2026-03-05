# TV7 System Flow (Big Picture)

## Purpose
Give every agent a concise system map so repo-local work stays within correct boundaries.

## Core Components
1. **Studio (`tv7-flutter-studio`)**: user-facing workflow and local orchestration.
2. **Engine (`tv7-axum-engine`)**: local compute sidecar for media-heavy operations.
3. **Backend (`tv7-fastapi-backend`)**: cloud control plane for auth, billing, scheduling, posting.
4. **Site (`tv7-astro-site`)**: marketing/docs/download surface.
5. **Core (`tv7-core`)**: shared docs, contracts, guardrails, and tooling.

## Primary End-to-End Flows
1. **Local-first creation flow**
   - User operates Studio.
   - Studio coordinates Engine for ingest/probe/transcription/render.
   - User can complete ingest -> detect -> edit -> export locally without backend dependency.
2. **Scheduling/publishing flow**
   - Studio submits schedule/post intents to Backend.
   - Backend stores schedule truth, enforces billing/credits, and executes posting workflow.
   - Studio reads status/history from Backend for visibility.
3. **Docs/contracts/governance flow**
   - Cross-repo rules and canonical artifacts live in `tv7-core`.
   - Repo agents consume via symlinked `docs/core` and `.agent`.

## Ownership Boundaries
- **Studio owns UX and local workflow orchestration.**
- **Engine owns local media compute.**
- **Backend owns account/billing/schedule truth and posting execution.**
- **Site owns public web experience.**
- **Core owns shared standards and cross-repo coordination assets.**

## Agent Scope Guidance
- Architect Agent: coordinator across repos; does multi-repo edits only when task explicitly requires.
- Per-repo Agent: implements within its repo by default; checks cross-repo impacts before finishing.
- Code Reviewer prompt is standalone in GitHub Actions (DeepSeek), not part of repo execution prompts.

## Cross-Repo Change Checklist
1. Confirm producer/consumer contract impact.
2. Update canonical artifacts in `tv7-core` when interfaces change.
3. Link related PRs across affected repos.
4. Run repo-specific checks before merge.

