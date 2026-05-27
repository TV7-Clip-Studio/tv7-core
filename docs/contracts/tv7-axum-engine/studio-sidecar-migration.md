# Studio Sidecar Migration

This document is the Engine-to-Studio handoff for the first mandatory sidecar adoption milestone.

## Product Decision

Studio starts Engine when the app starts. Users should experience TV7 as one app, not as a separate engine process they manage manually.

After this migration, Studio must use Engine for local media compute. Do not keep a direct `ffmpeg`/`ffprobe` fallback path in Flutter.

## Startup Contract

Studio should launch the Engine binary with:

```bash
TV7_ENGINE_HOST=127.0.0.1
TV7_ENGINE_PORT=7070
TV7_ENGINE_WORK_DIR=/absolute/path/to/studio/workspace
TV7_ENGINE_FFMPEG_BIN=/absolute/path/to/bundled/ffmpeg
TV7_ENGINE_FFPROBE_BIN=/absolute/path/to/bundled/ffprobe
TV7_ENGINE_YT_DLP_BIN=/absolute/path/to/bundled/yt-dlp
```

For developer builds, `TV7_ENGINE_FFMPEG_BIN`, `TV7_ENGINE_FFPROBE_BIN`, and `TV7_ENGINE_YT_DLP_BIN` may be omitted to use `PATH`.

After launch, Studio should call:

1. `GET /health` to verify the process is reachable.
2. `GET /v1/diagnostics` to decide whether media operations are ready.

If diagnostics returns `status: "degraded"`, Studio should show repair state from the diagnostics payload. The Engine process should remain running so Studio can inspect and display the problem.

## Diagnostics Example

```http
GET /v1/diagnostics
```

```json
{
  "status": "ready",
  "runtime": {
    "engine_version": "0.1.0",
    "host": "127.0.0.1",
    "port": 7070
  },
  "capabilities": [
    {
      "name": "probe",
      "status": "ready",
      "required_tools": ["ffprobe"]
    },
    {
      "name": "thumbnail",
      "status": "ready",
      "required_tools": ["ffmpeg"]
    },
    {
      "name": "render_clip",
      "status": "ready",
      "required_tools": ["ffmpeg"]
    },
    {
      "name": "url_ingest",
      "status": "ready",
      "required_tools": ["yt-dlp"]
    },
    {
      "name": "transcript",
      "status": "ready",
      "required_tools": ["yt-dlp"]
    }
  ],
  "tools": [
    {
      "name": "ffprobe",
      "available": true,
      "version": "ffprobe version 8.0 ...",
      "required_for": ["probe"],
      "error": null
    },
    {
      "name": "ffmpeg",
      "available": true,
      "version": "ffmpeg version 8.0 ...",
      "required_for": ["thumbnail", "render_clip"],
      "error": null
    },
    {
      "name": "yt-dlp",
      "available": true,
      "version": "yt-dlp 2026.01.01",
      "required_for": ["url_ingest", "transcript"],
      "error": null
    }
  ],
  "work_dir": {
    "path": "/absolute/path/to/studio/workspace",
    "ready": true,
    "error": null
  }
}
```

For `AX-A03`, `yt-dlp` is checked by Engine diagnostics because URL ingest and transcript download are Engine-owned capabilities.

## Flutter Replacement Map

| Current Studio method | Replacement Engine call | Notes |
| --- | --- | --- |
| `ToolRunner.getMediaInfo(path)` | `POST /v1/media/probe` | Use `metadata.duration_seconds`, `width`, `height`, `format`, and `size_bytes`. |
| `ToolRunner.generateThumbnail(videoPath, thumbnailPath)` | `POST /v1/media/thumbnail` | Engine always overwrites `output_path`; Studio owns workspace naming. |
| `ToolRunner.renderClip(sourcePath, start, end, outputPath)` | `POST /v1/media/render-clip` | Engine always overwrites `output_path`; validate user-facing ranges in Studio before calling. |
| `MediaService.prepareIngestFromUrl(url)` | `POST /v1/ingest/url`, then `GET /v1/jobs/{id}` | Engine owns `yt-dlp` metadata and download execution. Studio owns UX and backend sync. |
| `ToolRunner.downloadTranscript(url, outputPath, lang)` | `POST /v1/transcripts/download`, then `GET /v1/jobs/{id}` | Engine owns subtitle download. Studio may still normalize/display returned VTT content until a later normalization endpoint exists. |
| `IngestPage._checkDependencies()` | `GET /v1/diagnostics` | Flutter should not run `which ffmpeg`; use Engine diagnostics. |

## Probe Example

```http
POST /v1/media/probe
Content-Type: application/json
```

```json
{
  "path": "/absolute/path/to/video.mp4"
}
```

```json
{
  "metadata": {
    "path": "/absolute/path/to/video.mp4",
    "duration_seconds": 120.5,
    "width": 1920,
    "height": 1080,
    "format": "mov",
    "size_bytes": 10485760
  }
}
```

## Thumbnail Example

```http
POST /v1/media/thumbnail
Content-Type: application/json
```

```json
{
  "source_path": "/absolute/path/to/video.mp4",
  "output_path": "/absolute/path/to/video.mp4.thumb.jpg",
  "timestamp_seconds": 1.0
}
```

```json
{
  "result": {
    "output_path": "/absolute/path/to/video.mp4.thumb.jpg"
  }
}
```

## Render Clip Example

```http
POST /v1/media/render-clip
Content-Type: application/json
```

```json
{
  "source_path": "/absolute/path/to/video.mp4",
  "output_path": "/absolute/path/to/video_12_42.mp4",
  "start_seconds": 12.5,
  "end_seconds": 42.5
}
```

## URL Ingest Job Example

```http
POST /v1/ingest/url
Content-Type: application/json
```

```json
{
  "url": "https://example.com/video",
  "output_dir": "/absolute/path/to/workspace",
  "output_template": "%(title).200B.%(ext)s"
}
```

```json
{
  "job": {
    "id": "job_1",
    "kind": "url_ingest",
    "status": "queued",
    "progress": 0.0,
    "logs": ["queued"],
    "result": null,
    "error": null,
    "cancel_requested": false
  }
}
```

Studio should poll:

```http
GET /v1/jobs/job_1
```

Studio may also poll logs separately:

```http
GET /v1/jobs/job_1/logs
```

To request cancellation:

```http
POST /v1/jobs/job_1/cancel
```

Initial AX-A04 cancellation is cooperative at the Engine job state boundary. Process-level termination for an already-running `yt-dlp` child process is a follow-up hardening item.

Successful `result` contains:

```json
{
  "url": "https://example.com/video",
  "media_path": "/absolute/path/to/workspace/video.mp4",
  "metadata": {
    "title": "Video title"
  }
}
```

## Transcript Download Job Example

```http
POST /v1/transcripts/download
Content-Type: application/json
```

```json
{
  "url": "https://example.com/video",
  "output_path": "/absolute/path/to/video.vtt",
  "language": "en"
}
```

Successful job `result` contains:

```json
{
  "transcript_path": "/absolute/path/to/video.en.vtt",
  "language": "en"
}
```

```json
{
  "result": {
    "output_path": "/absolute/path/to/video_12_42.mp4",
    "duration_seconds": 30.0
  }
}
```

## Error Handling

Engine errors use this shape:

```json
{
  "error": "INVALID_TIME_RANGE",
  "message": "expected 0 <= start_seconds < end_seconds"
}
```

Expected first-migration error codes:

- `INVALID_PATH`
- `FILE_NOT_FOUND`
- `NOT_A_FILE`
- `OUTPUT_PARENT_MISSING`
- `SOURCE_OUTPUT_SAME`
- `INVALID_TIME_RANGE`
- `INVALID_URL`
- `COMMAND_FAILED`
- `OUTPUT_INVALID`
- `IO_ERROR`

Studio should display concise user-facing text while preserving the raw error code/message in logs.
