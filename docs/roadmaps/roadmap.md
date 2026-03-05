# TV7 Product Roadmap

Roadmap Code: CO
Batch Code: M01


## Per-Repo Roadmaps (Source of Truth)
- `tv7-core`: `docs/roadmaps/tv7-core-roadmap.md`
- `tv7-core` orchestration initiative: `docs/roadmaps/core/agent-orchestration-roadmap.md`
- `tv7-core` Project Conductor migration: `docs/roadmaps/core/project-conductor-roadmap.md`
- `tv7-fastapi-backend`: `docs/roadmaps/tv7-fastapi-backend-roadmap.md`
- `tv7-fastapi-backend` off-roadmap: `docs/roadmaps/tv7-fastapi-backend-off-roadmap.md`
- `tv7-flutter-studio`: `docs/roadmaps/tv7-flutter-studio-roadmap.md`
- `tv7-astro-site`: `docs/roadmaps/tv7-astro-site-roadmap.md`
- `tv7-axum-engine`: `docs/roadmaps/tv7-axum-engine-roadmap.md`

### Task Model & Coordination Rules
All tasks in this roadmap must follow this strict format to ensure visibility across agents.
ID shape: `REPO-BATCH-EPIC-TICKET` (example: `CO-M01-04-01`).
Repo and batch mappings are defined in `tooling/orchestrator/roadmap_ids.toml`.

#### Task Format
```markdown
- [ ] [XX-M01-01-01] Task Title
    **STATUS** | [Agent Name] | [YYYY-MM-DD HH:MM]
    - **CROSS-AGENT-NOTES**: ... (Omit if N/A)
    - **BLOCKER**: ... (Omit if N/A)
    - **PR**: ... (Omit if N/A)
    - **NOTE**: ... (Omit if N/A)
    - **CODE-REVIEW-NOTES**: ... (Omit if N/A)
```

Roadmap metadata (required near top of file):
```markdown
Roadmap Code: XX
Batch Code: M01
```

Status markers in checkbox position:
- `[ ]` backlog / ready
- `[P]` in progress
- `[X]` completed

#### Workflow Rules
1.  **Start**: Set checkbox to `[P]`. Set `STATUS: IN-PROGRESS`. Assign `AGENT` and `DATE`.
    *   *Rule*: Only one agent allowed per task.
2.  **Block**: Set `STATUS: BLOCKED`. Use `NOTE` to specify the blocker.
3.  **Finish**: Set checkbox to `[X]`. Set `STATUS: COMPLETED`. Update `DATE`. Add `NOTE` with completion summary.
4.  **Integrity**: Do not reorder sections or rewrite text outside your active task.



## Phase 1: Technical Debt & Cleanup (Immediate Priority)

### Backend Legacy Cleanup
> **Context**: The backend contains legacy code that must be removed before further feature development.
- [x] [CO-M01-02-01] Audit existing endpoints for unused legacy logic (removed ingestion/AI/admin pipeline paths).
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Cleaned up `main.py` and `api/v1/routes.py`
- [x] [CO-M01-02-02] Remove unused media processing code (since backend is now control-plane only).
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Deleted `services/{ai,ingest,transcription}.py` and related tests
- [ ] [CO-M01-02-03] Remove any legacy scheduling logic that predates the "credits" system if applicable.
    **TO-DO** | Backend Agent | 2025-12-17 15:20
- [x] [CO-M01-02-04] Verify `dramatiq` worker setup focuses **only** on posting, not processing.
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Removed `tasks.py` and legacy worker scripts
- [x] [CO-M01-02-05] Restore a minimal admin UI to review schedules/publish jobs and user metrics (control-plane only).
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Updated `admin/routes.py` and templates

## Phase 2: Architecture Sync
- [ ] [CO-M01-03-01] Ensure `tv7-flutter-studio` implements the "Post Now" vs "Schedule" distinction correctly.
    **BACKLOG** | Studio Agent | 2025-12-17 15:20
- [ ] [CO-M01-03-02] Verify `tv7-engine` API surface matches the "local compute only" mandate.
    **BACKLOG** | Engine Agent | 2025-12-17 15:20
- [ ] [CO-M01-03-03] Validate `tv7-fastapi-backend` credit ledger implementation.
    **BACKLOG** | Backend Agent | 2025-12-17 15:20

## Phase 3: Feature Development
- [x] [CO-M01-04-01] Optimize reusable DeepSeek review payload to avoid oversized API requests and skipped PR comments.
    **COMPLETED** | Architect Agent | 2026-02-08 12:15
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: Removed repo-wide file map context, excluded deleted-file hunks from diff payload (`--diff-filter=ACMRTUXB`), capped docs/diff context size, and switched DeepSeek request body to `--data-binary @payload_file` to avoid `curl` argv overflow.
