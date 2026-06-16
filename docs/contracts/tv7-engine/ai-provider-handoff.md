# Engine AI Provider Handoff

This contract defines how Studio, Engine, and Backend cooperate for TV7 AI features.

## Product Decision

Studio has one integration point for AI: Engine. Studio should not branch between local AI, TV7-managed local AI, and TV7 cloud AI at feature-call sites.

Engine resolves one user-facing `ai` capability in this order:

1. User-installed local AI, such as Ollama with a compatible model.
2. TV7-managed local AI downloaded/imported after explicit user confirmation.
3. TV7 cloud AI through Backend.

TV7 cloud AI can make `ai` ready, but it must not make `offline_creation` ready because it requires internet. `offline_creation` is ready only when local media processing, local transcription, local AI, and local rendering are ready.

## Cross-Repo Responsibilities

| Repo | Owns | Must not own |
| --- | --- | --- |
| Studio | Setup UX, user confirmation, displaying provider/readiness status, passing authenticated license/delegation context to Engine, calling Engine for AI and AI diagnostics. | Direct DeepSeek/OpenAI key entry, provider-specific AI request shaping, direct Backend AI debug calls. |
| Engine | Local provider discovery, TV7-managed local asset verification/download jobs, prompt/context policy, provider dispatch, one Studio-facing AI API, cloud request shaping to Backend. | Backend credentials, billing, quota policy, long-lived user auth storage, control-plane business logic. |
| Backend | User auth/license validation, short-lived Engine cloud AI delegation, TV7 DeepSeek credentials, cloud AI metering, quota/rate limits, admin observability. | Local media probing, local transcription, local rendering, local transcript scoring. |

## Auth And Delegation

TV7 cloud AI should use a delegated Engine credential, not user-entered provider keys.

1. Studio authenticates the user with Backend using the normal app session.
2. Studio requests a short-lived Engine delegation token from Backend after license validation.
3. Studio passes that token to Engine over loopback.
4. Engine keeps the token in memory and uses it only for Backend cloud AI calls.
5. Backend validates token scope, user license, quota, and rate limits on every cloud AI request.

Delegation tokens should have a short TTL, be scoped to `engine:cloud_ai`, avoid embedding provider secrets, and be safe to revoke server-side. Engine should not persist them in config files, diagnostics output, job logs, or crash reports.

## Debug Flow

Studio should route AI diagnostics through Engine:

1. Studio calls Engine setup/status or AI debug endpoints.
2. Engine reports local provider state directly.
3. Engine calls Backend for cloud AI reachability/auth/license/quota checks when cloud diagnostics are requested.
4. Studio displays the Engine-normalized result.

Studio should not call Backend cloud AI debug endpoints directly except for general account/license screens that are not AI execution diagnostics.

## Endpoint Direction

Studio to Engine:

- `GET /v1/setup/manifest`
- `GET /v1/setup/status`
- `POST /v1/ai/cloud-token`: pass a Backend-issued delegated `engine:cloud_ai` bearer token to Engine. Engine stores it in memory only and returns token metadata without the token value.
- `DELETE /v1/ai/cloud-token`: clear the in-memory delegated token on logout, license refresh, or revocation.
- `POST /v1/ai/cloud-debug`: route cloud AI readiness/debug through Engine. Engine checks local delegated-token state and calls Backend cloud AI execution when a valid token is present.
- `POST /v1/ai/transcript-intelligence`: first provider-agnostic AI execution endpoint for Quick Clip-style transcript analysis. Engine owns prompt/context shaping and returns structured clip suggestions.
- Future `POST /v1/setup/ai-provider`: store or apply explicit AI provider selection after setup.
- Future AI execution endpoints such as post copy generation and broader AI diagnostics.

Studio to Backend:

- Existing user auth/session/license APIs.
- Future delegated Engine token request, using the user's normal authenticated session.

Engine to Backend:

- `POST /api/v1/cloud-ai/engine/execute`: Engine-only TV7 cloud AI execution using the delegated bearer token.
- Backend cloud AI execution backs Engine cloud AI diagnostics and transcript intelligence when `tv7_cloud` is the resolved provider.

Backend token minting is published as `POST /api/v1/cloud-ai/engine-token`; Studio calls it with the user's normal authenticated Backend session and passes the returned delegated token to Engine.

## Error Contract

Cloud AI errors should be normalized before they reach Studio. Recommended stable codes:

- `AI_AUTH_REQUIRED`: no valid user session or delegated Engine token.
- `AI_LICENSE_REQUIRED`: authenticated user does not have cloud AI entitlement.
- `AI_QUOTA_EXCEEDED`: license is valid but usage quota or rate limit is exhausted.
- `AI_PROVIDER_UNAVAILABLE`: Backend or DeepSeek provider cannot complete the request.
- `AI_NETWORK_UNAVAILABLE`: Engine cannot reach Backend or the user is offline.
- `AI_CONTEXT_TOO_LARGE`: prompt/context exceeds the provider or TV7 policy limit.

Studio should treat these as feature setup or account states, not Engine startup failures.
