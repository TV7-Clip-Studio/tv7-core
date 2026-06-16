# TV7 Cross-Agent Handoffs

Handoffs coordinate work when one repo finishes a producer-side responsibility and another repo must consume it.

Use `make handoff` from `tv7-core` to refresh tracked active handoffs from the latest `make sync` cockpit data. Run `make sync` first when you want fresh repo status, PR context, and roadmap/code focus in the generated handoff files.

Active handoff files are generated artifacts. Do not hand-edit durable content into active handoffs unless the generator is updated to reproduce it.

## Folder Model

- `active/` contains tracked handoffs that still require implementation or validation.
- `archived/` contains completed or superseded handoffs.
- `templates/` contains the standard handoff shape used by agents and generator tooling.

Archive active handoffs after the consumer epic is complete or deliberately superseded. Use a year subfolder, for example `archived/2026/`.

## Granularity

Create one handoff per agent/repo for active cross-repo milestones. Do not create one handoff per small ticket unless the work crosses unrelated contracts.

## Ownership Rules

- The producer agent owns the contract, artifact, compatibility notes, and support for contract defects.
- The consumer agent owns implementation in its repo.
- The producer agent should not edit the consumer repo unless the human explicitly asks for cross-repo implementation.
- The consumer agent should report contract gaps back as blocker notes on the handoff and roadmap.

## Required Sections

Each active handoff should include:

- Mission and current state.
- Roadmap items.
- Current status.
- Contract artifacts and docs.
- Tasks and constraints.
- Validation commands.
- Deliverables and completion notes.

## Current Milestone

The active generated handoffs currently route the cross-repo milestone:

- `Unified Engine AI + Cloud Delegation`

Default generated files:

- `active/backend.md`
- `active/engine.md`
- `active/studio.md`

## Roadmap Links

Producer and consumer roadmaps should link to the active handoff while work is open. When archived, completion notes should link to the archived handoff.

## Cadence

- Start a work session with `SYNC_INTERACTIVE=0 make sync`.
- Before assigning one repo agent, run `make handoff HANDOFF_REPO=<repo>`.
- After that repo agent reports completion, run `SYNC_INTERACTIVE=0 make sync` and `make handoff HANDOFF_REPO=<repo>`.
- Before committing Core orchestration/docs changes, run `make precommit-context`.

`make precommit-context` warns when generated handoffs are stale, but does not fail solely because handoffs need regeneration.
