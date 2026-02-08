# Desktop ↔ Backend clip coordination plan

Goal: let the Flutter desktop app register locally-created clips without uploading source video assets to the server, while keeping the admin UI usable.

## Backend contracts (FastAPI)
- Auth: call `/api/v1/auth/login` and send `Authorization: Bearer <access_token>` on all requests.
- Create video metadata manually (no auto-upload):
  - `POST /api/v1/videos/local` with `source_url`, `title` (mapped to `original_filename`), optional `duration_seconds`/`file_size_bytes`, `transcript_text` (plain text) + `transcript_language`, `clip_generation_mode=replace`, and `metadata_only=true` (no source media stored; status becomes `ready`).
- Per-clip sync:
  - `POST /api/v1/videos/{id}/clips` with `start_sec`, `end_sec`, `caption_text`, `status=ready`, `thumbnail_path` (URL or data URL) for artwork; optional `asset_url`/`local_path` if you have a playable preview; optional sizing metadata.
- Sync-all/reset:
  - `DELETE /api/v1/videos/{id}` to remove an existing video + clips, then recreate via `/api/v1/videos/local` and repost clips.

## Admin UI behavior after backend changes
- If `metadata_only` was used and no `local_path` is stored, the admin page shows a placeholder instead of the source video player but still lists clips.
- Clip cards will show a thumbnail when `thumbnail_path` is provided, even if there is no preview video.
- Transcript is displayed as text; no binary upload expected.

## Manual sync flow (desktop client)
- Do not auto-upload clips. Present:
  - Per-clip “Sync” button → create video if needed, then post that clip.
  - “Sync all” button → delete backend video if it exists, recreate via `/videos/local`, repost all clips.
- Highlights: call `/api/v1/ai/highlights` with `transcript`, `duration_seconds`, optional `transcript_language`, optional `max_clips`. On 422, surface the error and do not create clips. Use returned clips to render locally, then POST to `/videos/{id}/clips` with thumbnails.

## Client expectations
- No automatic uploads; only sync on user action (per-clip or sync-all).
- Do not upload source video files; send metadata only.
- Always include `title` and `thumbnail_path` when syncing so Library cards render properly.
- Use JWT on all calls; handle 422 from highlights gracefully (no fallback clip creation).
