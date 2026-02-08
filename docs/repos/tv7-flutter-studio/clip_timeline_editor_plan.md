# Clip Timeline & Clip Editing Plan

## Goals
- Let users scrub the full video with a visual timeline that overlays all clips.
- Enable editing of clip metadata (start/end, title, description, hook) with immediate feedback.
- Keep flows inside the existing player page so dashboard stays lightweight.

## Scope & Assumptions
- Works for local videos and clips already shown in the dashboard.
- Reuse existing upload/sync flows; no backend schema changes planned yet.
- Timeline interactions: select clip, drag handles to adjust, seek via playhead; snap to small increments.

## Tasks
- [x] Entry point + scaffolding: add “Edit Clips” navigation from the dashboard, pass an edit-mode flag into the player, and reserve space for the upcoming timeline/editor layout.
- [x] Timeline track: render full-duration bar, clip spans, playhead, selection, and drag handles with snapping plus scrubbing to seek.
- [x] Inspector: editable fields for title/description/hook and start/end inputs; validation (end > start, within duration).
- [ ] Save/Delete flows: wire updates to backend or local metadata (optimistic updates, error handling); handle delete or re-create when no update endpoint exists.
- [ ] UX safeguards: duration probing fallback, overlap warnings, disable/save states, revert button per clip.
- [ ] Tests/QA: unit tests for time conversion/clamping, gesture math where feasible, and manual checklist for editor flows.

## Notes
- Prefer reusing `VideoPlayerPage` for the editor view; dashboard only links in.
- If backend lacks clip update, keep local edits and re-sync via existing upsert path.
