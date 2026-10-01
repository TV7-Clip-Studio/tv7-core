# Backend Integration (Studio ↔ FastAPI)

Updated: 2026-10-01. Studio uses Backend for identity, licensing, approved private assets, schedule drafts, and publishing status. Local media ingestion and rendering are Engine calls. The canonical Backend contract is `docs/contracts/openapi/tv7-backend/openapi.json`.

Current cloud handoff: sign in; fetch only the creator-approved rendered asset from Engine; upload it to the owner's private Backend storage; register owner-scoped source video and clip metadata with fractional timing; create and refresh a schedule draft. Check account ownership at every lookup. A pending draft has no remote post ID.

When changing an endpoint, update Backend implementation and its canonical OpenAPI artifact, then update Studio's typed calls and verify the browser flow. There is no Flutter SDK regeneration step.
