# TV7 Cross-Agent Handoffs

Handoffs coordinate work when one repo finishes a producer-side responsibility and another repo must consume it.

## Folder Model

- `active/` contains handoffs that still require consumer implementation or validation.
- `archived/` contains completed or superseded handoffs.

Archive active handoffs after the consumer epic is complete or deliberately superseded. Use a year subfolder, for example `archived/2026/`.

## Granularity

Create one handoff per epic. Do not create one handoff per small ticket unless the work crosses unrelated contracts.

## Ownership Rules

- The producer agent owns the contract, artifact, compatibility notes, and support for contract defects.
- The consumer agent owns implementation in its repo.
- The producer agent should not edit the consumer repo unless the human explicitly asks for cross-repo implementation.
- The consumer agent should report contract gaps back as blocker notes on the handoff and roadmap.

## Required Sections

Each active handoff should include:

- Producer and consumer repos/agents.
- Source and target roadmap items.
- Current status.
- Contract artifacts and docs.
- Consumer implementation entry points.
- Validation commands.
- Risks and rollback notes.
- Done criteria.

## Roadmap Links

Producer and consumer roadmaps should link to the active handoff while work is open. When archived, completion notes should link to the archived handoff.
