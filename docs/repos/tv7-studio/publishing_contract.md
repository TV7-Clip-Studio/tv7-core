# Publishing Contract (Studio + Backend Worker)

Last updated: 2026-02-12

Publishing is backend-owned execution. Studio triggers, monitors, and reports status to the user.

## Ownership
- **Backend and worker**: platform OAuth/tokens, publish execution, retries, auditing, and final status updates.
- **Studio client**: local render/export, upload initiation, publish trigger/schedule request, and status/error presentation.

## Current Spec-Aligned Surface
In the checked-in OpenAPI, publishing is currently represented by:
- `POST /api/v1/clips/{clip_id}/publish`
- `PublishJobRead` and `PublishJobStatus` schemas

This supports job-oriented publish triggering and status reporting, even while broader scheduling APIs evolve.

## Contract Rules
- Studio must never store platform OAuth tokens.
- Studio must gate publish UX behind backend config and plan checks.
- Studio must send stable clip identifiers and required metadata for backend job execution.
- Backend must return enough status detail for user-visible progress and failures.

## Target Evolution (Pro Scheduler)
As Pro scheduling matures, preserve backward-safe behavior while adding:
- Dedicated schedule resources (create/read/list by time/platform).
- Explicit publish timestamps and retry metadata.
- Dashboard/WebView connection flow for social account linking.

## Cross-Repo Coordination
For any publish contract changes:
1. Update backend producer and OpenAPI artifact.
2. Regenerate Studio SDK.
3. Update Studio publish UI/data flow.
4. Validate with `make check` in Studio and backend checks in backend repo.
