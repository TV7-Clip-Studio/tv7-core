# TV7 Product Roadmap

### Task Model & Coordination Rules
All tasks in this roadmap must follow this strict format to ensure visibility across agents.

#### Task Format
```markdown
- [ ] Task Title
    **STATUS** | [Agent Name] | [YYYY-MM-DD HH:MM]
    - **CROSS-AGENT-NOTES**: ... (Omit if N/A)
    - **BLOCKER**: ... (Omit if N/A)
    - **PR**: ... (Omit if N/A)
    - **NOTE**: ... (Omit if N/A)
    - **CODE-REVIEW-NOTES**: ... (Omit if N/A)
```

#### Workflow Rules
1.  **Start**: Change checkbox to `[/]`. Set `STATUS: IN-PROGRESS`. Assign `AGENT` and `DATE`.
    *   *Rule*: Only one agent allowed per task.
2.  **Block**: Set `STATUS: BLOCKED`. Use `NOTE` to specify the blocker.
3.  **Finish**: Change checkbox to `[x]`. Set `STATUS: COMPLETED`. Update `DATE`. Add `NOTE` with completion summary.
4.  **Integrity**: Do not reorder sections or rewrite text outside your active task.



## Phase 1: Technical Debt & Cleanup (Immediate Priority)

### Backend Legacy Cleanup
> **Context**: The backend contains legacy code that must be removed before further feature development.
- [x] Audit existing endpoints for unused legacy logic (removed ingestion/AI/admin pipeline paths).
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Cleaned up `main.py` and `api/v1/routes.py`
- [x] Remove unused media processing code (since backend is now control-plane only).
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Deleted `services/{ai,ingest,transcription}.py` and related tests
- [ ] Remove any legacy scheduling logic that predates the "credits" system if applicable.
    **TO-DO** | Backend Agent | 2025-12-17 15:20
- [x] Verify `dramatiq` worker setup focuses **only** on posting, not processing.
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Removed `tasks.py` and legacy worker scripts
- [x] Restore a minimal admin UI to review schedules/publish jobs and user metrics (control-plane only).
    **COMPLETED** | Backend Agent | 2025-12-17 15:20
    - **NOTE**: Updated `admin/routes.py` and templates

## Phase 2: Architecture Sync
- [ ] Ensure `tv7-flutter-studio` implements the "Post Now" vs "Schedule" distinction correctly.
    **BACKLOG** | Studio Agent | 2025-12-17 15:20
- [ ] Verify `tv7-engine` API surface matches the "local compute only" mandate.
    **BACKLOG** | Engine Agent | 2025-12-17 15:20
- [ ] Validate `tv7-fastapi-backend` credit ledger implementation.
    **BACKLOG** | Backend Agent | 2025-12-17 15:20

## Phase 3: Feature Development
*To be populated after cleanup.*
