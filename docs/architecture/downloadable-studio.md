# Downloadable Studio decision proof

Status: implementation proof in progress (2026-10-01). This document defines the product boundary for the next integrated slice; it does not claim the full workflow is already implemented.

## Product shape

TV7 is a downloadable macOS and Windows creator app. Media acquisition, transcription, candidate selection, editing, caption burn-in, and rendering run on the creator's computer. The cloud Backend handles identity, licensing, private storage of approved rendered assets needed for unattended schedules, scheduled post state, and platform publishing. A scheduled post must execute after Studio closes; only approved finished assets need cloud storage.

The Studio frontend is one React/TypeScript UI across the packaged Tauri app and browser-based development/agent tests. The earlier Flutter desktop app and separate Flutter web shell were retired after the shared UI completed a real local Engine render in both browser and macOS desktop tests. This is a focused implementation slice, not a shipped product.

## Local import and batch contract

1. **Computer file:** Studio sends selected bytes to a bounded, streaming Engine import endpoint. Engine owns the resulting file path and returns an opaque media/job reference. The browser never supplies an arbitrary local path.
2. **Single URL:** Studio submits one user-selected video URL to Engine and displays job progress, result, and failure.
3. **Channel URL:** Engine discovers a bounded page of video metadata. Studio displays checkboxes, counts, and an explicit confirmation. Only the selected video IDs start download jobs; further pages require deliberate selection. Cancellation and restart must not duplicate completed media.
4. **Rights and distribution:** The local prototype may offer user-initiated downloads of media the creator is authorized to use. YouTube's API policies prohibit API clients from downloading/importing YouTube audiovisual content without prior written approval. A commercial release must either obtain that approval or use channel discovery for metadata and import creator-supplied originals. Do not promise that any channel URL alone supplies usable source binaries. See [YouTube API developer policies](https://developers.google.com/youtube/terms/developer-policies).

YouTube publication has a separate gate: [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert) says uploads from unverified API projects created after July 2020 are restricted to private viewing until the project passes an audit. A successful API upload is therefore not proof that TV7 can publish a public Short.

Engine's loopback HTTP interface is an implementation boundary, not a public network service. It must reject unsafe paths, enforce byte/job limits, and bind to loopback. Exact browser origins are allowed for development; CORS does not authenticate local callers. Add a per-install/session authorization mechanism before shipping a packaged app or exposing mutation endpoints to arbitrary web origins.

## Creator and cloud state

The persistent local workflow is: imported source → transcript → candidate ranges → saved edit → deterministic rendered variant → user approval. A candidate is not a rendered clip. Saving an edit must persist a draft without creating a misleading ready asset. One approved clip may produce different platform variants and captions.

The cloud workflow begins only when a creator elects to schedule or publish: connect a platform account → upload the approved rendered asset to private owner-scoped storage → create a scheduled post for a target account and UTC time → execute an idempotent publish attempt → record remote post ID and outcome. Backend feature flags must reflect real adapters. There is no posting claim until the provider confirms success.

## Decision proof gates

- The same Studio screens and workflow code run in a browser test and a macOS desktop build; a Windows build is required before choosing the production frontend.
- A computer-selected video reaches Engine through Studio, can be probed, and produces a playable local result without Backend media compute.
- A channel URL yields a paged preselection; cancelling changes nothing; confirming selected items creates only their jobs.
- Automated UI tests can navigate the meaningful workflow through the browser build. Desktop behavior is checked separately on macOS and Windows.
- The proof identifies packaging for the Engine binary, FFmpeg, yt-dlp, optional transcription model, updates, and per-platform signing. Missing dependencies appear as actionable setup states.

Do not relabel this slice as a shipped product until the remaining gates pass. Windows packaging, clean-install media dependencies, durable editing, and live publishing are still open.

## Current local proof

`make dev-browser-yt-dlp` installs a pinned yt-dlp and its JavaScript support into an ignored, isolated environment. `make dev-browser-up` serves Studio at `http://127.0.0.1:8080` alongside Backend and the loopback Engine; `make dev-studio` starts its Vite development server at `http://127.0.0.1:5173`. Node 22 or newer, FFmpeg, and FFprobe are still host prerequisites. This is a development setup, not a packaged dependency strategy. The React/Tauri app is at the root of `tv7-studio`.

On macOS the release `.app` now bundles and starts an Engine child on a dynamically allocated loopback port. Native UI completed video import/probe, bounded VTT import, deterministic candidate review, timing adjustment, and a captioned MP4 render; FFprobe reported 0.8 seconds. Quitting the app stopped the Engine child while the independent development Engine stayed healthy. The packaged app sets a random per-session bearer token for every Engine route; browser development mode is explicitly unprotected. This proves the local desktop media path, not clean-install readiness: FFmpeg, FFprobe, yt-dlp, their runtime, signing, updater, and Windows packaging still need product-grade handling.
