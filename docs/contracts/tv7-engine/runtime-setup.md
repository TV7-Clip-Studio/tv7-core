# Engine Runtime Setup Contract

This contract defines the first-run setup boundary between Studio and Engine for packaged desktop builds.

## Product Decision

TV7 uses a small installer. Studio launches the bundled Engine as part of the app, then Engine exposes one user-facing AI capability. Engine resolves the backing provider in priority order:

1. User-installed local AI, such as Ollama with a compatible model.
2. TV7-managed local AI downloaded/imported after explicit user confirmation.
3. TV7 cloud AI, where Engine calls Backend and Backend owns the TV7 DeepSeek credentials, authorization, billing, and metering.

Studio owns the setup UX and user confirmation. Engine owns the runtime asset manifest, setup/download execution, verification, prompt/context policy, and AI provider dispatch. Studio should call Engine for AI work regardless of the resolved provider.

No runtime assets should be downloaded silently at app startup. Downloads must happen only after explicit user confirmation.

See `ai-provider-handoff.md` for the cross-repo AI delegation contract.

## Cross-Repo Responsibilities

- Studio owns setup UX, user confirmation, and Engine status display. Studio calls Engine for AI execution and AI diagnostics.
- Engine owns local provider discovery, TV7-managed local setup, prompt/context policy, provider dispatch, and Backend cloud AI request shaping.
- Backend owns user auth/license validation, delegated Engine cloud AI credentials, TV7 DeepSeek credentials, billing, quota, metering, and cloud provider observability.

Studio must not collect user DeepSeek/OpenAI keys for TV7 cloud AI. Engine must not persist long-lived user auth or provider credentials.

## Startup Boundary

Studio still starts Engine with the sidecar startup environment from `studio-sidecar-migration.md`.

Packaged builds should resolve Engine and bundled tool paths from app resources. Developer builds may continue using the sibling Engine repo and `PATH`-resolved tools.

Studio should call setup endpoints only after Engine startup succeeds:

1. `GET /health`
2. `GET /v1/diagnostics`
3. `GET /v1/setup/manifest`
4. `GET /v1/setup/status`

Engine resolves runtime capabilities in this order:

1. User-configured paths and user-installed tools.
2. User-installed local providers such as Ollama.
3. Bundled TV7 app resources, when packaged.
4. TV7-managed downloads after explicit Studio/user confirmation.
5. TV7 cloud AI through Backend when local AI is unavailable or not selected.

Engine must not reinstall or duplicate a compatible user-installed runtime/model. If Ollama already has the selected model, Engine reports that provider as ready. If Ollama exists but the selected model is missing, Studio may offer to use another installed model, ask Ollama to pull the selected model, use a TV7-managed model, or configure later.

## Cloud AI Delegation

TV7 cloud AI uses Backend as the trust boundary:

1. Studio authenticates the user through Backend.
2. Studio obtains a short-lived Backend-issued delegation token scoped to Engine cloud AI after license validation.
3. Studio passes the delegation token to Engine over loopback with `POST /v1/ai/cloud-token`.
4. Engine stores the token in memory only and uses it when calling Backend cloud AI endpoints.
5. Engine clears the token with `DELETE /v1/ai/cloud-token` on logout, license refresh, or revocation.
6. Backend validates token scope, license, quota, and rate limits before calling DeepSeek with TV7-managed credentials.

Studio should route cloud AI debug through Engine with `POST /v1/ai/cloud-debug`. Engine should normalize Backend auth/license/quota/provider errors into stable AI readiness and execution errors for Studio.

## AI Provider Candidates

| Provider | Internet required | Disk cost | Privacy | Notes |
| --- | --- | --- | --- | --- |
| `ollama` | No after user setup | User-owned | Local | Preferred when a compatible user-installed model is available. |
| `tv7_managed` | Only for first-run download/import | TV7-owned local assets | Local | Enables offline AI after setup. |
| `tv7_cloud` | Yes | Low | Sends selected prompt/context to TV7 Backend | Backend owns DeepSeek credentials, authorization, billing, and metering. |

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
- `ai`: transcript intelligence and post generation through the resolved Engine provider.
- `rendering`: final local clip rendering/export.
- `offline_creation`: local media creation workflow without internet after setup.

`ai` can be ready through TV7 cloud AI. `offline_creation` is stricter: it is ready only when local media processing, transcription, local AI, and rendering requirements are satisfied. Cloud AI must not make `offline_creation` ready because it requires internet. URL ingest and social publishing are also excluded because they may require internet.

## API Draft

`GET /v1/setup/manifest`, `GET /v1/setup/status`, `POST /v1/transcripts/generate`, `POST /v1/ai/cloud-token`, `DELETE /v1/ai/cloud-token`, `POST /v1/ai/cloud-debug`, and `POST /v1/ai/transcript-intelligence` are implemented. Mutating local setup/download endpoints remain contract targets for `EN-A06-01-03`.

### `GET /v1/setup/manifest`

Returns the Engine-known setup catalog for the current platform.

```json
{
  "schema_version": 1,
  "platform": "macos-arm64",
  "setup_modes": ["automatic", "disabled"],
  "ai_provider_order": ["ollama", "tv7_managed", "tv7_cloud"],
  "assets": [
    {
      "id": "whisper-runtime.user-path",
      "kind": "transcription_runtime",
      "name": "User-installed Whisper runtime",
      "required_for": ["transcription", "offline_creation"],
      "installable": false,
      "bundled": false,
      "source": "user_path",
      "version": null,
      "download": null
    },
    {
      "id": "ollama.user-runtime",
      "kind": "llm_runtime",
      "name": "User-installed Ollama runtime",
      "required_for": ["ai", "offline_creation"],
      "installable": false,
      "bundled": false,
      "source": "ollama",
      "version": null,
      "download": null
    }
  ]
}
```

Download URLs above are examples. Production manifests must use real TV7-approved origins and checksums.

### `GET /v1/setup/status`

Returns installed/configured status for setup, assets, AI provider candidates, and capabilities.

```json
{
  "schema_version": 1,
  "setup_complete": false,
  "active_ai_provider": "tv7_cloud",
  "assets": [
    {
      "id": "whisper-runtime.user-path",
      "kind": "transcription_runtime",
      "name": "User-installed Whisper runtime",
      "status": "available",
      "source": "user_path",
      "path": "/opt/homebrew/bin/whisper-cli",
      "version": "whisper.cpp",
      "error": null
    },
    {
      "id": "local-llm.tv7-managed.macos-arm64",
      "kind": "llm_model",
      "name": "TV7-managed local LLM",
      "status": "installable",
      "source": "tv7_managed",
      "path": "/Users/example/Library/Application Support/TV7/Engine/models/llm",
      "version": null,
      "error": "download requires explicit user confirmation"
    }
  ],
  "ai_providers": [
    {
      "source": "ollama",
      "status": "missing_assets",
      "required_assets": ["llm_runtime", "llm_model"],
      "requires_internet": false,
      "requires_user_confirmation": true,
      "cost_policy": "user_local",
      "action": "Install Ollama and configure a compatible model."
    },
    {
      "source": "tv7_cloud",
      "status": "ready",
      "required_assets": [],
      "requires_internet": true,
      "requires_user_confirmation": false,
      "cost_policy": "tv7_managed_usage",
      "action": null
    }
  ],
  "capabilities": [
    {
      "name": "ai",
      "status": "ready",
      "provider": "tv7_cloud",
      "missing": [],
      "installable": true,
      "user_action_required": false
    },
    {
      "name": "offline_creation",
      "status": "not_ready",
      "provider": null,
      "missing": ["transcription", "local_ai"],
      "installable": true,
      "user_action_required": true
    }
  ]
}
```

### `POST /v1/setup/start`

Starts a setup job after explicit Studio/user confirmation.

```json
{
  "setup_mode": "automatic",
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

### `POST /v1/setup/ai-provider`

Stores or applies the selected AI provider after setup.

```json
{
  "provider": "ollama",
  "model": "gemma4"
}
```

Studio should not collect or forward raw DeepSeek API keys. For `tv7_cloud`, Engine calls Backend and Backend owns provider credentials, authorization, billing, and metering.

### `POST /v1/transcripts/generate`

Starts job-backed local transcript generation for an imported local media file. Studio should call this when a local import has no adjacent or known transcript and Quick Clip needs one.

Engine queues a job only when the `transcription` setup capability is ready. Transcription readiness currently requires an explicit user-configured Whisper-compatible runtime and model through Engine setup state. Engine must not auto-download models from this endpoint.

```json
{
  "media_path": "/absolute/path/to/video.mp4",
  "output_path": "/absolute/path/to/video.vtt",
  "language": "en"
}
```

Accepted response:

```json
{
  "job": {
    "id": "job_42",
    "kind": "transcript_generate",
    "status": "queued",
    "progress": 0.0,
    "logs": ["queued"],
    "result": null,
    "error": null,
    "cancel_requested": false
  }
}
```

If setup is missing, Engine returns HTTP `409` and does not create a job:

```json
{
  "error": "TRANSCRIPTION_SETUP_REQUIRED",
  "message": "Local transcription requires a configured runtime and model.",
  "missing": ["transcription_runtime", "transcription_model"],
  "setup_capability": "transcription"
}
```

Successful job result:

```json
{
  "transcript_path": "/absolute/path/to/video.vtt",
  "format": "vtt",
  "language": "en"
}
```

Developer builds use `TV7_ENGINE_WHISPER_BIN` for the Whisper-compatible runtime and `TV7_ENGINE_WHISPER_MODEL` for the model path. Studio should poll `GET /v1/jobs/{id}` until the job reaches `succeeded`, then attach/use `result.transcript_path`.

### `POST /v1/ai/cloud-token`

Stores a Backend-issued delegated Engine cloud AI token in memory only.

```json
{
  "token": "backend-issued-delegated-token",
  "token_type": "bearer",
  "scope": "engine:cloud_ai",
  "expires_in_seconds": 900,
  "credits_remaining": 100
}
```

```json
{
  "status": {
    "state": "configured",
    "scope": "engine:cloud_ai",
    "token_type": "bearer",
    "expires_in_seconds": 899,
    "credits_remaining": 100
  }
}
```

Engine must never return the token value from this endpoint, setup status, diagnostics, job logs, or errors.

### `DELETE /v1/ai/cloud-token`

Clears the in-memory delegated token. Studio should call this during logout, license refresh, or token revocation.

### `POST /v1/ai/cloud-debug`

Checks TV7 cloud AI readiness through Engine. If a valid delegated token is present, Engine sends a minimal Engine-shaped health prompt to Backend `POST /api/v1/cloud-ai/engine/execute`.

```json
{
  "provider": "tv7_cloud",
  "status": "not_ready",
  "error": "AI_QUOTA_EXCEEDED",
  "token": {
    "state": "configured",
    "scope": "engine:cloud_ai",
    "token_type": "bearer",
    "expires_in_seconds": 899,
    "credits_remaining": 0
  }
}
```

### `POST /v1/ai/transcript-intelligence`

Generates structured Quick Clip-style suggestions from transcript cues through the resolved Engine AI provider. Engine owns prompt/context shaping. The first executable provider path is `tv7_cloud`; local AI execution remains a follow-up under `EN-A05-01-02`.

```json
{
  "transcript": [
    {
      "start_seconds": 1.0,
      "end_seconds": 5.0,
      "text": "This is a useful hook."
    }
  ],
  "clip_duration": "medium",
  "timeline_target": "entire_video",
  "existing_clips": [],
  "max_suggestions": 3
}
```

```json
{
  "provider": "tv7_cloud",
  "model": "deepseek-chat",
  "clips": [
    {
      "title": "Strong opening",
      "start_seconds": 1.0,
      "end_seconds": 31.0,
      "reason": "Clear hook and useful standalone segment.",
      "score": 0.91
    }
  ],
  "usage": {
    "credits_charged": 1,
    "credits_remaining": 99,
    "prompt_tokens": 1200,
    "completion_tokens": 180,
    "total_tokens": 1380,
    "latency_ms": 840
  }
}
```

The response must not expose delegated tokens or Backend provider credentials. Backend receives already-shaped messages through `POST /api/v1/cloud-ai/engine/execute`.

## Setup Rules

- Engine must not download assets unless `confirm_download` is true.
- Engine must prefer compatible user-installed runtimes/models before bundled or TV7-managed assets.
- Engine must report TV7-managed assets as `installable`, not `available`, until download/import verification succeeds.
- Engine may report `ai` ready through TV7 cloud AI, but cloud AI must not satisfy `offline_creation`.
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
- First-run setup can be skipped, completed with local assets, or use TV7 cloud AI for online AI features.
- Offline creation becomes ready only after local transcription and local AI assets are installed or imported.
- URL ingest and social publishing may remain internet-dependent.

## Security And Privacy

- Cloud AI uses TV7 Backend as the trust boundary.
- Studio must explain that TV7 cloud AI sends selected transcript/context to TV7 Backend for processing.
- Offline creation mode must not call cloud AI providers.
- API keys, delegated Engine tokens, and auth headers should not appear in logs, diagnostics, job logs, crash reports, or persisted Engine config.
- Downloaded assets must come from approved origins and be checksum-verified.
