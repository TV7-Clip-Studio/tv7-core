# Contracts In Core

Cross-repo interface contracts are stored here as canonical artifacts.

## OpenAPI
- `openapi/tv7-backend/openapi.json` - canonical FastAPI contract export.
- `openapi/tv7-engine/openapi.json` - canonical local Engine sidecar contract export.

## Engine Handoffs
- `tv7-engine/studio-sidecar-migration.md` - historical Flutter-to-Engine migration record; not current implementation guidance.
- `tv7-engine/runtime-setup.md` - Engine-managed runtime asset manifest and first-run setup contract.
- `tv7-engine/ai-provider-handoff.md` - Studio/Engine/Backend responsibilities for unified AI provider dispatch and TV7 cloud AI delegation.

## Ownership
- Each producing repo exports and maintains its contract artifact here.
- Each consuming repo should read contracts from `docs/core/contracts/...` inside its repo, or from canonical `tv7-core/docs/contracts/...`.
- Product repos should not keep duplicate contract artifacts under repo-local `docs/contracts` unless they are generated scratch output that is immediately published to Core.
