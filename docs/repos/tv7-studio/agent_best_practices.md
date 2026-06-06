# Agent Best Practices (Flutter client)

## Quick start
- Repo root: run `make help` for common tasks. App lives in `forgotten_client/`.
- Env: copy a JSON env file, e.g. `cp forgotten_client/.env.dev.example forgotten_client/.env.dev`.
- Run desktop (no flavor flag needed on macOS/Windows/Linux): `make run-desktop DEVICE=macos ENV_FILE=.env.dev`.
- Run mobile flavors (once schemes exist): `make run FLAVOR=dev ENV_FILE=.env.dev`.
- Lint/test: `make check` (format + analyze + test).
- OpenAPI: use canonical spec at `docs/contracts/openapi/tv7-backend/openapi.json` and run `make gen-api`.

## What to avoid
- Don’t store platform OAuth tokens or secrets client-side; publishing is backend-owned.
- Don’t commit `.env*` (only `*.example`) or `.metadata`. Generated API code should come from the spec, not manual edits.
- Don’t break desktop-first workflows; mobile can lag while pipeline stabilizes.

## Working assumptions
- Auth flow: JWT login/refresh via backend. Config/feature flags fetched from backend to choose cloud vs local paths.
- Pipeline: local ingest/ffmpeg normalize/render; transcripts are local-first via `whisper.cpp` (cloud/OpenAI fallback if disabled/failing). Sync metadata to backend; assets upload optional until publish phase.
- Binaries: expect `ffmpeg`/`yt-dlp` present or user-provided paths; surface missing deps in settings.

## Useful paths and commands
- App code: `forgotten_client/lib/…`
- Env files: JSON maps at `forgotten_client/.env.*`
- Make targets: `format`, `analyze`, `test`, `check`, `run`, `run-desktop`, `gen-api`.
- Workspace (future): app data dir with `/ingest`, `/normalize`, `/render`, `/logs`; clean per job.

## Coordination with FastAPI
- Backend publishes OpenAPI; client generates Dart SDK from it. If spec missing, request export.
- Publishing contract: see `docs/repos/tv7-studio/publishing_contract.md`; backend owns platform tokens/publish jobs. Client triggers/polls and uploads assets if required.
- Config endpoint needed: `publishing_enabled`, `asset_upload_required`, allowed platforms, size limits, OpenAI policy.

## Flow to bootstrap a feature
1) Ensure env + deps: `make analyze` to pull packages; verify `ffmpeg`/`yt-dlp` availability.
2) If API changes are needed, update/obtain the OpenAPI spec and regen the client.
3) Build UI/state in `forgotten_client/lib/features/...`, wire services in `forgotten_client/lib/data/...` (add domain modules only when needed).
4) Add tests under `forgotten_client/test`, keep `flutter analyze` and `flutter test` green.
