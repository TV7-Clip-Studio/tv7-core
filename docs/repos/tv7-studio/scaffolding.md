# Studio Scaffolding and Conventions

Last updated: 2026-02-12

This document describes the current repository structure and the expected development conventions.

## Repo Layout
- Flutter app root: `forgotten_client/`
- Makefile entrypoint (repo root): `Makefile`
- Canonical backend contract artifact: `docs/contracts/openapi/tv7-backend/openapi.json`

## Current App Structure
- Entrypoints: `forgotten_client/lib/main_dev.dart`, `forgotten_client/lib/main_stage.dart`, `forgotten_client/lib/main_prod.dart`
- App bootstrap: `forgotten_client/lib/bootstrap.dart`, `forgotten_client/lib/app.dart`
- Feature modules: `forgotten_client/lib/features/{auth,dashboard,ingest,player,user}`
- Data modules: `forgotten_client/lib/data/{api,auth,config,local}`
- Generated API SDK: `forgotten_client/lib/api/generated/`
- Tests: `forgotten_client/test/`

## Environment and Run Commands
- Env templates: `forgotten_client/.env.dev.example`, `forgotten_client/.env.stage.example`, `forgotten_client/.env.prod.example`
- Desktop run (recommended): `make run-desktop DEVICE=macos ENV_FILE=.env.dev`
- Flavor run: `make run FLAVOR=dev ENV_FILE=.env.dev`

## Quality Commands
- Format: `make format`
- Analyze: `make analyze`
- Test: `make test`
- Full check gate: `make check`

## OpenAPI Client Workflow
- Sync canonical spec into app input:
  - `./.codex/skills/studio-openapi-sync/scripts/sync_spec.sh`
- Regenerate client:
  - `make gen-api` (calls `forgotten_client/tool/generate_api.sh`)
- Treat `forgotten_client/lib/api/generated/` as generated-only code.
- Apply handwritten adapters in `forgotten_client/lib/data/api/` and feature/repository consumers.

## Conventions
- Keep desktop-first workflows stable; mobile parity can follow.
- Keep external-process and local media interactions in `lib/data/local/`.
- Keep test doubles/fakes in `forgotten_client/test/` to avoid real external dependencies in CI.
