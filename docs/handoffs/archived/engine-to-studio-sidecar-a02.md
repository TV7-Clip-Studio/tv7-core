# Engine To Studio Sidecar Handoff A02

## Status

Status: Archived

Producer: Engine Agent (`tv7-engine`)

Consumer: Studio Agent (`tv7-studio`)

Epic: Mandatory Engine sidecar adoption

## Source Roadmap Items

Engine producer items:

- `EN-A02-01-01`: Define Studio-facing Engine API contract.
- `EN-A02-01-02`: Implement Engine diagnostics.
- `EN-A02-01-03`: Implement thumbnail endpoint.
- `EN-A02-01-04`: Implement render-clip endpoint.
- `EN-A02-01-05`: Add contract examples and compatibility notes.

Studio consumer items:

- `ST-A02-01-01`: Add Studio-managed Engine process lifecycle at app startup.
- `ST-A02-01-02`: Add Engine client and health/diagnostics integration.
- `ST-A02-01-03`: Replace direct `ffprobe` usage with Engine probe API.
- `ST-A02-01-04`: Replace direct thumbnail generation with Engine thumbnail API.
- `ST-A02-01-05`: Replace direct clip rendering with Engine render API.
- `ST-A02-01-06`: Remove user-facing direct media tool dependency checks after Engine adoption.

## Product Decisions

- Studio starts Engine when the app starts.
- Users should experience TV7 as one app, not as separate user-managed processes.
- Engine is mandatory for local media compute after adoption.
- Studio should not keep direct `ffmpeg`/`ffprobe` fallback paths after migration.
- Version stays inside `GET /v1/diagnostics`; do not add a separate `/version` endpoint for this milestone.
- `yt-dlp` is future `EN-A03` ingest work and is not checked by `EN-A02` diagnostics.

## Contract Artifacts

Canonical Core artifacts:

- `docs/core/contracts/openapi/tv7-engine/openapi.json`
- `docs/core/contracts/tv7-engine/studio-sidecar-migration.md`

Canonical workspace paths:

- `tv7-core/docs/contracts/openapi/tv7-engine/openapi.json`
- `tv7-core/docs/contracts/tv7-engine/studio-sidecar-migration.md`

Published staging artifact hash:

```text
75bd0d4f49fca3132e5bcff0febfcf4a8b3f4ad8a0379f4101400bb9038b46fd  docs/core/contracts/tv7-engine/studio-sidecar-migration.md
```

## Engine API Surface

- `GET /health`
- `GET /v1/diagnostics`
- `POST /v1/media/probe`
- `POST /v1/media/thumbnail`
- `POST /v1/media/render-clip`

All media paths must be absolute local filesystem paths.

Thumbnail and render-clip always overwrite output paths.

## Studio Implementation Entry Points

Inspect these Studio files first:

- `tv7-studio/forgotten_client/lib/data/local/tool_runner.dart`
- `tv7-studio/forgotten_client/lib/data/local/media_service.dart`
- `tv7-studio/forgotten_client/lib/data/local/local_video_repository.dart`
- `tv7-studio/forgotten_client/lib/features/ingest/ingest_page.dart`
- `tv7-studio/forgotten_client/lib/bootstrap.dart`
- `tv7-studio/forgotten_client/lib/app.dart`

Expected replacements:

| Current Studio behavior | Engine replacement |
| --- | --- |
| `ToolRunner.getMediaInfo(path)` | `POST /v1/media/probe` |
| `ToolRunner.generateThumbnail(videoPath, thumbnailPath)` | `POST /v1/media/thumbnail` |
| `ToolRunner.renderClip(sourcePath, start, end, outputPath)` | `POST /v1/media/render-clip` |
| `IngestPage._checkDependencies()` direct shell checks | `GET /v1/diagnostics` |

## Suggested Studio Execution Order

1. Claim `ST-A02-01-01`.
2. Add an Engine process manager that starts the Engine binary at app startup.
3. Add health and diagnostics checks after launch.
4. Surface degraded diagnostics in the app without trying direct shell fallbacks.
5. Claim `ST-A02-01-02`.
6. Add an Engine client wrapper for the local HTTP API.
7. Replace probe, thumbnail, and render usage in the smallest safe increments.
8. Remove direct user-facing dependency checks after Engine diagnostics is wired.

## Validation

Engine validation already passed:

- `make check`
- `make test`
- `cargo clippy --all-targets --all-features -- -D warnings`
- `.codex/skills/engine-sidecar-bootstrap/scripts/run_quality_gate.sh`
- `.codex/skills/engine-media-probe-implementation/scripts/run_probe_checks.sh`

Studio validation required after consumer implementation:

- Run from `tv7-studio`: `make check`
- For manual desktop validation: `make run-desktop DEVICE=macos ENV_FILE=.env.dev`

## Risks

- Studio packaging may not yet know where the Engine binary and bundled tools should live.
- macOS app sandboxing/notarization may require a later packaging pass.
- Existing Studio workflows may assume direct process output from `ffmpeg`; Engine currently returns structured success/error only.
- URL ingest still uses direct `yt-dlp` until `EN-A03` and `ST-A03`.

## Rollback

Before Studio removes direct media calls, rollback is to disable Engine startup/client wiring and keep existing `ToolRunner` behavior.

After Studio removes direct media calls, rollback is to revert the Studio sidecar adoption commits or temporarily pin to the pre-sidecar Studio release.

Do not add new direct `ffmpeg`/`ffprobe` fallback logic as rollback behavior.

## Done Criteria

This handoff was archived on 2026-05-22 after:

- `ST-A02-01-01` through `ST-A02-01-06` are complete or deliberately superseded.
- Studio launches Engine on startup.
- Studio uses Engine diagnostics for media readiness.
- Studio uses Engine for probe, thumbnail, and render-clip.
- Studio no longer performs direct `ffmpeg`/`ffprobe` shell calls for these operations.
- Studio validation passes with `make check`.
