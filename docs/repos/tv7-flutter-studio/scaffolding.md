# Scaffolding Plan (Flutter project)

## Tooling assumptions
- Flutter stable channel; Dart >= current stable.
- `openapi-generator-cli` pinned (e.g., via `./tools/openapi-generator-cli.sh` wrapper) for reproducible client builds.
- Package manager: `flutter pub`; format/analyze/test in CI.

## Project creation
- Command: `flutter create forgotten_client`
  - Platforms enabled: macOS/Windows/Linux/iOS/Android.
  - Org: `com.forgotten.client` (adjust as needed).
  - L10n, web disabled initially (optional to enable later).

## Flavors/env
- Flavors: `dev`, `stage`, `prod`.
- dart-defines (per flavor): `API_BASE_URL`, `OPENAI_MODE`, `FEATURE_FLAGS_JSON`, `SENTRY_DSN` (optional), `APP_LOG_LEVEL`.
- Use `.env.<flavor>` for local development; load via build scripts into dart-defines.
- Build/run examples:
  - `flutter run --flavor dev --dart-define-from-file=.env.dev` (JSON map file)
  - `flutter build macos --flavor stage --dart-define-from-file=.env.stage` (JSON map file)

## Package layout (suggested)
- `lib/`
  - `main_dev.dart`, `main_stage.dart`, `main_prod.dart` (entrypoints wiring env).
  - `config/` (env, flavor, feature flags).
  - `core/` (logging, theme, routing, error handling).
  - `data/` (api client wrapper, models, repositories, cache).
  - `domain/` (use cases/services: auth, pipeline orchestrator, sync).
  - `features/` (ui modules: auth, dashboard, workspace, settings).
  - `platform/` (binary path discovery, process helpers).
  - `widgets/` (shared UI components).
- `assets/` for icons/fonts; `packages/` optional for modularization later.

## Dependencies (initial set)
- State mgmt: `riverpod` or `flutter_riverpod`.
- HTTP: `dio` (used by generated client) + interceptors for auth/logging.
- JSON: `json_serializable`.
- Local storage: `hive` or `sqlite` (`drift`/`floor`) for cache/queue.
- Env: `flutter_dotenv` or custom dart-define loader.
- Logging: `logger` or custom wrapper.
- Background/process: platform channels/FFI wrappers for running binaries; use `process_run` where appropriate on desktop.
- UI: `go_router` or `beamer` for navigation; `hooks_riverpod` optional for ergonomics.

## OpenAPI client integration
- Canonical spec lives at `docs/contracts/openapi/tv7-fastapi-backend/openapi.json`; copy/sync to `openapi/forgotten-app.json` when generating client SDK.
- Generator config `openapi/config.yaml` (pinned options).
- Generated client lives in `lib/api/generated/`; add thin wrapper in `lib/data/api_client.dart`.
- Provide script `tool/generate_api.sh` to fetch spec and regenerate client; commit generated code.

## Settings & storage
- Secure storage per platform for tokens/OpenAI key (`flutter_secure_storage` with platform key stores).
- Settings persisted in local store with defaults; validate binary paths on change.

## CI hooks
- `flutter format`, `flutter analyze`, `flutter test`.
- `dart run build_runner build --delete-conflicting-outputs` for generated code.
- OpenAPI generation check to ensure spec and generated code stay in sync.

## Immediate next actions
- Verify Flutter SDK availability (`flutter --version`); install if missing.
- Run `flutter create forgotten_client` in repo root.
- Add flavor-specific main files and env loader.
- Add OpenAPI generator config + script placeholders.
