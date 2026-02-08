# Testing Strategy (Flutter client)

## Layers and scope
- Unit tests (pure Dart): config/env loading, token storage, API client interceptors, pipeline arg builders/state machines. No Flutter bindings.
- Widget tests: individual screens/components with fakes (auth form validation, progress UI, settings forms). Use `pumpWidget` with stub view models; avoid real HTTP/processes.
- Service/infra tests: fake process runner for pipeline (build ffmpeg/yt-dlp args, parse logs, state transitions); no real binaries in CI. Fake dio handler to test auth headers/refresh logic.
- Integration tests (limited): only high-value flows (e.g., login + metadata fetch) against a mock/local backend. Keep minimal to avoid flakiness.
- Golden tests (optional): only for stable UI pieces; skip while UI is in flux.
- Contract checks: regenerate/diff OpenAPI client; keep generated SDK in sync with spec.

## What to avoid
- Don’t call real backends or spawn real ffmpeg/yt-dlp/whisper in CI.
- Don’t couple tests to volatile UI visuals; prefer behavior assertions over pixel-perfect checks unless golden is deliberate.

## Where to put tests
- Unit/service tests: `forgotten_client/test/`
- Integration (if needed): `forgotten_client/integration_test/` with `integration_test` package.
- Keep helpers/fakes under `test/` (e.g., `test/fakes/`, `test/utils/`).

## Focus areas to cover early
- Config/env: `AppConfig.fromEnvironment` parsing and fallback.
- Auth: token store behavior; auth interceptor attaches headers; refresh flow behavior with fakes.
- Pipeline orchestration: builds correct command args; handles state transitions and error mapping using fake process runner/log stream.
- Widget basics: auth form validation, progress UI, settings forms using stub view models.

## Running tests
- From repo root: `make test` (runs `flutter test`), `make analyze` for static checks, `make check` for format+analyze+test.

## Agent notes
- Use fakes/mocks; no external network or binaries. Keep tests fast and deterministic.
- If adding new service APIs, include a small unit test for interceptors/helpers and update any API regen checks once the OpenAPI spec is available.
