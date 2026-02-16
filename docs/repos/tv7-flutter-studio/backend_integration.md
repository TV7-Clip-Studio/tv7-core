# Backend Integration (Studio ↔ FastAPI)

Last updated: 2026-02-12

System source of truth: `docs/architecture/tv7_high_architecture.md`.
Contract artifact source of truth: `docs/contracts/openapi/tv7-fastapi-backend/openapi.json`.

## Current OpenAPI Surface (What Exists Today)
The checked-in spec currently exposes these Studio-relevant groups:
- **Auth**: `/api/v1/auth/login`, `/api/v1/auth/refresh`
- **Config**: `/api/v1/config`
- **AI**: `/api/v1/ai/execute`
- **Ingest and video metadata**: `/api/v1/videos/ingest/upload`, `/api/v1/videos/ingest/youtube`, `/api/v1/videos/local`, `/api/v1/videos/{video_id}`, `/api/v1/videos/{video_id}/clips`
- **Clip operations**: `/api/v1/clips/{clip_id}`, `/api/v1/clips/{clip_id}/publish`
- **Uploads**: `/api/v1/uploads/assets`

## Integration Rules for Studio
- Treat `forgotten_client/lib/api/generated/` as generated code; do not hand-edit endpoint/model files.
- Regenerate SDK after any contract update:
  - `./.codex/skills/studio-openapi-sync/scripts/sync_spec.sh`
  - `make gen-api`
- Keep handwritten integration logic in `forgotten_client/lib/data/api/` and feature/repository consumers.
- Maintain compatibility across repos by updating the contract artifact first, then producer/consumer code.

## Expected Contract Additions (Still Pending)
These are architecture-aligned expectations not yet complete in the current spec:
- License/trial/activation endpoints and plan-aware policy fields.
- Dedicated highlight contract (`transcript + prompt -> clip segments`) if replacing or aliasing `/api/v1/ai/execute`.
- First-class scheduling resource(s) for Pro publishing lifecycle visibility.

## Change Protocol
When backend contract changes are required:
1. Update backend implementation in `tv7-fastapi-backend`.
2. Export updated OpenAPI into `docs/contracts/openapi/tv7-fastapi-backend/openapi.json`.
3. Regenerate Studio SDK (`make gen-api`) and patch handwritten consumers.
4. Run Studio checks: `make check`.
5. Link related backend/client PRs per `docs/repos/cross-repo-policy.md`.
