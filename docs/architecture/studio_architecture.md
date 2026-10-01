# TV7 Studio Architecture

This document describes the target creator workflow, including features that are not yet built. The current React/Tauri implementation and verified boundaries are recorded in [Downloadable Studio](downloadable-studio.md).

Primary user interface for the whole workflow.

## 1. Ingestion
Lets user ingest:
- Video URL
- Playlist
- Single video file
- Folder of videos

## 2. Engine Management
- Starts and manages the local Engine process (launch/stop/health-check).
- Sends jobs to the Engine (transcribe, detect clips, render/export).

## 3. Clip Editor
Displays detected clips + transcript; provides a clip editor:
- Adjust start/end times
- Edit transcript text (for subtitles)
- Edit clip title + post description + hashtags
- Approve / reject clips

## 4. Export & Publishing
### Local Export
- Supports local export for approved clips (works offline).

### Post Now
- Immediate posting action (no scheduling).
- Uses the same “posting pipeline” concept as scheduled posts (same payload shape, same tracking), but executes immediately.

### Schedule
Studio contains a scheduler UI and “bulk schedule builder”:
- Aggressive/light cadence
- Day/night windows
- Specific hours
- Timezone

**Behavior:**
- Studio computes a proposed schedule and shows it to the user.
- Studio syncs the schedule with the backend (backend becomes the source of truth).
- **Billing**: Studio checks credit balance and blocks schedule creation if insufficient credits. Shows credits/balance in simple terms.

## 5. Visibility & Tracking
Studio shows the lifecycle of every publish attempt:
- Scheduled time(s)
- Posted time(s)
- Status per attempt (success/failure)
- Errors/logs summary

A single clip/post may be posted multiple times (retries or reposts); Studio must show all attempts.
