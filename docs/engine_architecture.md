# TV7 Engine Architecture (Rust / Axum Sidecar, Local)

Runs locally on the user machine; treated as a local service by Studio.

## Responsibilities
Performs compute-heavy work:
- Ingest/download support as needed
- Transcription/subtitles generation
- Clip detection (AI/LLM logic stays local)
- Rendering/exporting final clips
- Generating assets like thumbnails/subtitle burn-in (if applicable)

Produces final rendered clip files + metadata that Studio can export locally or send to backend.

## Non-Goals
Does **not** handle:
- User accounts
- Payments/credits
- Scheduling logic (time/calendar decisions)
- Posting to social platforms
