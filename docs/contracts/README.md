# Contracts In Core

Cross-repo interface contracts are stored here as canonical artifacts.

## OpenAPI
- `openapi/tv7-fastapi-backend/openapi.json` - canonical FastAPI contract export.
- `openapi/tv7-axum-engine/openapi.json` - canonical local Engine sidecar contract export.

## Engine Handoffs
- `tv7-axum-engine/studio-sidecar-migration.md` - Engine-to-Studio migration contract for mandatory sidecar adoption.

## Ownership
- Each producing repo exports and maintains its contract artifact here.
- Each consuming repo should read contracts from `docs/core/contracts/...` inside its repo, or from canonical `tv7-core/docs/contracts/...`.
- Product repos should not keep duplicate contract artifacts under repo-local `docs/contracts` unless they are generated scratch output that is immediately published to Core.
