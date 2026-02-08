# Contracts In Core

Cross-repo interface contracts are stored here as canonical artifacts.

## OpenAPI
- `openapi/tv7-fastapi-backend/openapi.json` - canonical FastAPI contract export.

## Ownership
- Each producing repo exports and maintains its contract artifact here.
- Each consuming repo should read contracts from this path (directly or via symlink/workflow sync).

