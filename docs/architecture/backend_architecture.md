# TV7 Backend Architecture (FastAPI, Cloud Control Plane)

Exists to support account + scheduling + posting execution; not involved in clip detection, LLM, or media generation.

## Responsibilities

### Identity & Access
- User accounts (login/auth)
- Social account connections (OAuth) + secure token storage/refresh

### Billing
- Credits ledger / usage-based billing for scheduling.
- Validates credit availability for schedule creation.

### Scheduling & Posting
- Accepts uploads of rendered clips + metadata from Studio.
- Stores clips temporarily (short-lived retention).
- **Scheduling Source of Truth**: Stores schedule entries (publish time(s), platform, captions).
- **Background Posting Workers**:
    - Execute posts at publish time.
    - Handle retries + status tracking + logs.

### Reporting
- Provide unified posting history for Studio:
    - Scheduled posts
    - “Post now” attempts
    - Multiple attempts per post (retries/reposts)
    - Posted timestamps and result status

## Non-Goals
- **No media processing/transcoding**
- **No LLM calls**
- **No transcript generation**
