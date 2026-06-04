# Engine Runtime Setup Contract

This contract defines the first-run setup boundary between Studio and Engine for packaged desktop builds.

## Product Decision

TV7 uses a small installer. Studio launches the bundled Engine as part of the app, then first-run setup asks the user which AI mode they want:

- `local`: download or import local runtime assets, then support offline creation.
- `openai`: use the user's OpenAI API key for AI features.
- `deepseek`: use the user's DeepSeek API key for AI features.
- `disabled`: skip AI setup for now.

Studio owns the setup UX, user confirmation, and secrets entry. Engine owns the runtime asset manifest, setup/download execution, verification, prompt/context policy, and AI provider dispatch.

No runtime assets should be downloaded silently at app startup. Downloads must happen only after explicit user confirmation.

## Startup Boundary

Studio still starts Engine with the sidecar startup environment from `studio-sidecar-migration.md`.

Packaged builds should resolve Engine and bundled tool paths from app resources. Developer builds may continue using the sibling Engine repo and `PATH`-resolved tools.

Studio should call setup endpoints only after Engine startup succeeds:

1. `GET /health`
2. `GET /v1/diagnostics`
3. `GET /v1/setup/manifest`
4. `GET /v1/setup/status`

## Provider Modes

| Mode | Internet required | Disk cost | Privacy | Notes |
| --- | --- | --- | --- | --- |
| `local` | Only for first-run download unless assets are imported/bundled | High | Best | Required for offline transcript intelligence and post generation. |
| `openai` | Yes | Low | Sends selected prompt/context to OpenAI | User-provided key. Good quality and convenience. |
| `deepseek` | Yes | Low | Sends selected prompt/context to DeepSeek | User-provided key. Lower-cost cloud option. |
| `disabled` | No | Low | No AI calls | Media import/probe/render/export still works. |

## Runtime Asset Types

Engine setup status should model assets with these stable categories:

- `engine_binary`: the running Engine executable. Packaged with Studio, not downloaded by Engine.
- `media_tool`: command-line media tools such as `ffmpeg`, `ffprobe`, and `yt-dlp`.
- `transcription_runtime`: local transcription runtime such as Whisper or whisper.cpp.
- `transcription_model`: local speech-to-text model files.
- `llm_runtime`: local LLM runtime such as a llama.cpp-style executable or library wrapper.
- `llm_model`: local model files for transcript intelligence and post generation.

The first implementation may report assets that are not yet installable. The contract should distinguish `available`, `missing`, `installable`, and `unsupported` states.

## Capability Groups

Diagnostics and setup status should converge on these capability names:

- `media_core`: local file probe, thumbnail, and render.
- `url_ingest`: public URL ingest through `yt-dlp`.
- `transcription`: local or downloaded transcript generation.
- `local_llm`: local transcript intelligence and post generation.
- `cloud_llm`: configured OpenAI/DeepSeek provider availability.
- `rendering`: final local clip rendering/export.
- `offline_creation`: local media creation workflow without internet after setup.

`offline_creation` is ready only when local media processing, transcription, local LLM, and rendering requirements are satisfied. URL ingest and social publishing are excluded because they may require internet.

## API Draft

These endpoints are contract targets for `AX-A06-01-03`. They may be added to OpenAPI when implementation starts.

### `GET /v1/setup/manifest`

Returns the Engine-known setup catalog for the current platform.

```json
{
  "schema_version": 1,
  "platform": "macos-arm64",
  "provider_modes": ["local", "openai", "deepseek", "disabled"],
  "assets": [
    {
      "id": "ffmpeg.macos-arm64",
      "kind": "media_tool",
      "name": "ffmpeg",
      "required_for": ["media_core", "rendering"],
      "installable": true,
      "bundled": false,
      "version": "8.0",
      "download": {
        "url": "https://downloads.tv7.local/ffmpeg/macos-arm64/ffmpeg",
        "sha256": "example-sha256",
        "size_bytes": 52428800
      }
    },
    {
      "id": "qwen-small.macos-arm64",
      "kind": "llm_model",
      "name": "Qwen small local model",
      "required_for": ["local_llm", "offline_creation"],
      "installable": true,
      "bundled": false,
      "version": "tbd",
      "download": {
        "url": "https://downloads.tv7.local/models/qwen-small.gguf",
        "sha256": "example-sha256",
        "size_bytes": 2147483648
      }
    }
  ]
}
```

Download URLs above are examples. Production manifests must use real TV7-approved origins and checksums.

### `GET /v1/setup/status`

Returns installed/configured status for setup, assets, providers, and capabilities.

```json
{
  "schema_version": 1,
  "setup_complete": false,
  "selected_provider": null,
  "assets": [
    {
      "id": "ffmpeg.macos-arm64",
      "kind": "media_tool",
      "name": "ffmpeg",
      "status": "available",
      "path": "/Applications/TV7 Studio.app/Contents/Resources/bin/ffmpeg",
      "version": "8.0",
      "error": null
    },
    {
      "id": "qwen-small.macos-arm64",
      "kind": "llm_model",
      "name": "Qwen small local model",
      "status": "missing",
      "path": null,
      "version": null,
      "error": "model not installed"
    }
  ],
  "providers": [
    {
      "mode": "local",
      "status": "missing_assets",
      "required_assets": ["qwen-small.macos-arm64"]
    },
    {
      "mode": "openai",
      "status": "missing_api_key",
      "required_assets": []
    },
    {
      "mode": "deepseek",
      "status": "missing_api_key",
      "required_assets": []
    }
  ],
  "capabilities": [
    {
      "name": "media_core",
      "status": "ready",
      "missing": []
    },
    {
      "name": "offline_creation",
      "status": "not_ready",
      "missing": ["transcription_model", "llm_model"]
    }
  ]
}
```

### `POST /v1/setup/start`

Starts a setup job after explicit Studio/user confirmation.

```json
{
  "provider_mode": "local",
  "asset_ids": [
    "whisper-small.macos-arm64",
    "qwen-small.macos-arm64"
  ],
  "confirm_download": true
}
```

```json
{
  "job": {
    "id": "job_42",
    "kind": "setup",
    "status": "queued",
    "progress": 0.0
  }
}
```

Setup jobs should reuse the Engine job API:

- `GET /v1/jobs/{id}`
- `GET /v1/jobs/{id}/logs`
- `POST /v1/jobs/{id}/cancel`

### `POST /v1/setup/provider`

Stores or applies the selected provider mode after setup.

```json
{
  "provider_mode": "openai",
  "api_key_ref": "studio-secure-store:openai",
  "model": "gpt-4.1-mini"
}
```

Studio should not send raw API keys unless the final implementation explicitly chooses one-shot key forwarding. The preferred contract is a secure key reference or session-scoped secret handoff owned by Studio.

## Setup Rules

- Engine must not download assets unless `confirm_download` is true.
- Engine must validate expected checksums before marking assets available.
- Engine must fail with an actionable error when disk space is insufficient.
- Engine should clean up partial downloads after failed or canceled jobs when safe.
- Engine should support retry. Resume is preferred when the download mechanism supports it.
- Engine should report installed asset paths, versions, and verification status.
- Engine should never require cloud keys for local media import/probe/render/export.

## Fresh-Install Readiness

A fresh packaged install should satisfy these expectations:

- Studio starts bundled Engine automatically.
- Engine diagnostics are reachable on loopback.
- Media operations do not depend on developer repo paths.
- First-run setup can be skipped, completed with local assets, or configured for OpenAI/DeepSeek.
- Offline creation becomes ready after local transcription and local LLM assets are installed or imported.
- URL ingest and social publishing may remain internet-dependent.

## Security And Privacy

- Cloud AI is opt-in.
- Studio must explain that OpenAI/DeepSeek modes send selected transcript/context to the provider.
- Local mode must not call cloud AI providers.
- API keys should not appear in logs, diagnostics, job logs, crash reports, or persisted Engine config.
- Downloaded assets must come from approved origins and be checksum-verified.
