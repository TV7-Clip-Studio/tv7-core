# Publishing Contract (Studio + Backend Worker)

Updated: 2026-10-07. Studio creates and displays creator intent. Backend owns account-bound OAuth credentials, schedule truth, private approved assets, worker execution, provider receipts, and reconciliation.

A creator must approve cloud upload of a finished local render. Studio may create a draft for a target account and UTC time, but must display it as pending until Backend verifies provider publication. Do not treat an HTTP upload response, queued job, or accepted draft as proof of a public post. Backend capabilities must reflect live configured adapters and account connection state.

YouTube publication still requires Google credentials, an owner-bound connection, audit approval for public visibility, and a live end-to-end test. Instagram and TikTok adapters are not yet implemented. Contract changes must update Backend, Studio, and the canonical Core OpenAPI artifact together.


## Social account connections

Account contains creator profiles and their verified provider accounts. Studio uses the shared Backend connection API for YouTube, Instagram, and TikTok:

- `GET /api/v1/social/providers`: provider configuration readiness and an actionable setup message; never credentials.
- `GET /api/v1/social/connections?creator_profile_id=...`: authenticated owner's verified accounts assigned to that profile.
- `POST /api/v1/social/{platform}/connect`: start OAuth with the selected profile; return a provider authorization URL. Platform is `youtube`, `instagram`, or `tiktok`.
- `GET /api/v1/social/{platform}/callback`: exchange the one-time state and code; verify identity and store encrypted credentials. Browser callbacks show a completion page.
- `DELETE /api/v1/social/connections/{connection_id}`: disconnect locally from TV7; does not imply revocation in the provider account.

OAuth state binds the TV7 owner, creator profile, and provider. Tokens stay in Backend. Studio opens the official provider login in a separate browser window, or the system browser in Tauri, then refreshes connection state. Native external opening accepts only allowlisted provider authorization URLs. Existing YouTube routes remain compatible.

`connected` and `publishing_ready` are separate. Instagram and TikTok connections do not enter executable publish plans until their publishing adapters are available. Source discovery does not authorize publishing to that channel.

## Local YouTube pre-upload (2026-10-08)

Studio reviews the exact connected channel and clip post copy before an explicit private upload. Backend POST `/api/v1/youtube/local-uploads` creates a durable idempotent resumable session and returns short-lived transfer credentials with `Cache-Control: no-store`. Engine GET `/v1/media/{id}/transfer-metadata` supplies size and SHA-256; POST `/v1/transfers/youtube` validates that manifest and streams directly to the authorized Google session, probing its existing offset before each attempt. Credentials are not saved in Studio workspace or Engine logs.

Backend `/{upload_id}/verify` uses the authoritative session and channel/private status; completed bytes may remain `processing` until YouTube finishes. Only then are `private_uploaded` or `scheduled` confirmed. Future release uses YouTube `publishAt` and requires API audit approval. Backend stores metadata and encrypted resumable state, not media. Studio can review private test batches up to 25 finished clips and reuse per-clip receipts. These receipts remain distinct from the existing Backend-hosted schedule job executor.
