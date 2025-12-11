# TV7 Backend Architecture (Control Plane)

Context
- Lives in `tv7-fastapi-backend`; serves authentication, licensing, scheduling, and Pro-only posting.
- No heavy media work; all processing is local in the engine/app.

Processes
- API (`fastapi`): auth, license issuance, optional clip suggestion fallback, Pro clip upload, scheduling CRUD, social OAuth flows.
- Worker (`dramatiq`): posts scheduled clips at `publish_at`, handles retries/failures, updates status.

Data plane
- Postgres: users, licenses, scheduled posts, social connections.
- Object storage (S3-compatible): short-lived clip files for Pro scheduling.

Security + access
- JWT-like license tokens; HTTPS everywhere.
- Social tokens stored server-side for Pro posting.

Out of scope
- No media processing/rendering.
- No local engine orchestration (handled by Flutter/engine).
