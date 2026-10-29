# TV7 Product Roadmap

Roadmap Code: CO
Batch Code: M01


## Per-Repo Roadmaps (Source of Truth)
- `tv7-core`: `docs/roadmaps/tv7-core-roadmap.md`
- `tv7-core` orchestration initiative: `docs/roadmaps/core/agent-orchestration-roadmap.md`
- `tv7-core` Project Conductor migration: `docs/roadmaps/core/project-conductor-roadmap.md`
- `tv7-conductor`: `../tv7-conductor/docs/roadmaps/tv7-conductor-roadmap.md`
- `tv7-backend`: `docs/roadmaps/tv7-backend-roadmap.md`
- `tv7-backend` off-roadmap: `docs/roadmaps/tv7-backend-off-roadmap.md`
- `tv7-studio`: `docs/roadmaps/tv7-studio-roadmap.md`
- `tv7-site`: `docs/roadmaps/tv7-site-roadmap.md`
- `tv7-engine`: `docs/roadmaps/tv7-engine-roadmap.md`

### Task Model & Coordination Rules
All tasks in this roadmap must follow this strict format to ensure visibility across agents.
ID shape: `REPO-BATCH-EPIC-TICKET` (example: `CO-M01-04-01`).
Repo and batch mappings are defined in `../tv7-conductor/tooling/orchestrator/roadmap_ids.toml`.

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
- [ ] [CO-M01-03-01] Ensure `tv7-studio` implements the "Post Now" vs "Schedule" distinction correctly.
    **BACKLOG** | Studio Agent | 2025-12-17 15:20
- [ ] [CO-M01-03-02] Verify `tv7-engine` API surface matches the "local compute only" mandate.
    **BACKLOG** | Engine Agent | 2025-12-17 15:20
- [ ] [CO-M01-03-03] Validate `tv7-backend` credit ledger implementation.
    **BACKLOG** | Backend Agent | 2025-12-17 15:20

## Phase 3: Feature Development
- [x] [CO-M01-04-01] Optimize reusable DeepSeek review payload to avoid oversized API requests and skipped PR comments.
    **COMPLETED** | Architect Agent | 2026-02-08 12:15
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: Removed repo-wide file map context, excluded deleted-file hunks from diff payload (`--diff-filter=ACMRTUXB`), capped docs/diff context size, and switched DeepSeek request body to `--data-binary @payload_file` to avoid `curl` argv overflow.
- [x] [CO-M01-04-02] Fix reusable DeepSeek review comment normalizer step to be self-contained in child repos
    **COMPLETED** | Architect Agent | 2026-05-25 18:42
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: Converted the `Normalize DeepSeek review comment` step in the reusable workflow to an inline Python script. This removes dependencies on external helper scripts in workspace paths, fixing execution across all child repositories.
- [x] [CO-M01-04-03] Address DeepSeek code review findings for local-dev-stack branch
    **COMPLETED** | Architect Agent | 2026-05-25 18:48
    - **CROSS-AGENT-NOTES**: Applies to all repos in local-dev-stack branch context.
    - **NOTE**: Fixed startup race condition in `dev-stack.sh` by sleeping `0.5s` before checking if the PID is still alive, ensuring immediate failures are successfully caught and reported. Widened exception handling in `reviews.py` repo loop to catch any unexpected error and skip the repo cleanly.
- [x] [CO-M01-04-04] Enhance DeepSeek review to follow-up on history and refine layout
    **COMPLETED** | Architect Agent | 2026-05-25 18:52
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: Integrated PR comment/review history parsing using the `gh` CLI and inlined Python logic. Previous reviews are now automatically injected into the DeepSeek system prompt to perform target checks on whether past findings were successfully resolved (under a new `### Follow-up on Previous Review` section). Completely removed the robotic `### Model narrative` wrapper heading and transitioned layout to clean Markdown `###` section headers.
- [x] [CO-M01-04-05] Fix here-doc delimiter indentation in deepseek-review.yml
    **COMPLETED** | Architect Agent | 2026-05-25 19:03
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: Aligned the Python script here-document block and its closing delimiter `PY` to column 0 in the generated shell script (exactly 10 spaces of base indentation under YAML multiline `run: |` block). Verified syntactical correctness and execution logic locally using `bash -n`.
- [x] [CO-M01-04-06] Address follow-up DeepSeek code review findings
    **COMPLETED** | Architect Agent | 2026-05-25 19:11
    - **CROSS-AGENT-NOTES**: Applies to all repos in local-dev-stack context.
    - **NOTE**: Addressed key follow-up findings from the review: (1) Added structural comments explaining mandatory process decisions in `dev-stack.sh` (why `exec` is required to prevent daemon orphans, and why we do a liveness check instead of a retry loop). (2) Replaced `compgen` in `dev-stack.sh` logs with a portable shell glob expansion check. (3) Increased pagination limit in `reviews.py` from `3` to `10` pages (up to 1,000 items). (4) De-duplicated fields list in `reviews.py` by removing `files`, `comments`, and `reviews` from the `gh pr view` call, speeding up API runs.
- [x] [CO-M01-04-08] Implement multi-turn agentic code reviewer and QA memory
    **COMPLETED** | Architect Agent | 2026-05-27 22:25
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: Upgraded the GHA reviewer into a multi-turn agentic system (max 2 turns) using standard Python runner inside GHA runner. The reviewer can request up to 3 local files inside the workspace dynamically to clarify symbols and resolve false positives. Integrated full PR QA and discussion thread reconstruction using inlined Python and `gh` CLI JSON comments, helping the bot respect previous developer/reviewer interactions.
- [X] [CO-M01-04-09] Harden DeepSeek follow-up review against stale repeated findings.
    **COMPLETED** | Architect Agent | 2026-06-03 00:00
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: DeepSeek follow-up reviews now attach current snippets for files cited by the prior review, resolve Core docs by basename anywhere under `docs/`, and explicitly require previous findings to be revalidated before being repeated as active blockers. Engine review context now passes `engine_architecture.md`. Validated with workflow YAML parsing, inline runner Python compilation, helper script `py_compile`, doc lookup smoke, and `git diff --check`.
- [X] [CO-M01-04-10] Rebuild DeepSeek multi-round review context as structured current-source checklist.
    **COMPLETED** | Architect Agent | 2026-06-04 00:00
    - **CROSS-AGENT-NOTES**: Applies to all repos consuming `tv7-core/.github/workflows/deepseek-review.yml`.
    - **NOTE**: Replaced raw previous-review prose injection with `tooling/deepseek_review_context.py`, which extracts only prior Findings into a structured checklist and attaches current source snippets for cited files. The reusable workflow now passes checklist/current-source context to DeepSeek, not prior Recommendations/Risks/final verdict prose. Added unit tests for Markdown/plain heading extraction, recommendation exclusion, finding splitting, and current snippet attachment. Validated with `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests -p 'test_*.py'`, workflow YAML parse, inline runner compile, `py_compile`, and `git diff --check`.
- [X] [CO-M01-04-11] Address DeepSeek review findings for Core developer Git tooling.
    **COMPLETED** | Architect Agent | 2026-06-07 22:18
    - **CROSS-AGENT-NOTES**: Applies to `tv7-core` developer tooling that coordinates sibling repos and optionally calls `tv7-conductor`.
    - **NOTE**: Added explicit Conductor availability checks and consistent Conductor wrappers in `tooling/git-dev.sh`, made stash-pop conflicts visible instead of swallowed, added an explicit Bash/POSIX-mode guard, kept Bash array usage behind that guard, and added `tooling/pr-info.sh` fallback behavior for GitHub CLI versions without `--state all`. Validated with `bash -n tooling/git-dev.sh tooling/pr-info.sh`, `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests -p 'test_*.py'`, `git diff --check`, and `sh tooling/git-dev.sh` guard smoke test.
- [X] [CO-M01-04-12] Address DeepSeek follow-up recommendations for Core developer Git tooling.
    **COMPLETED** | Architect Agent | 2026-06-08 00:00
    - **CROSS-AGENT-NOTES**: Applies to `tv7-core` developer tooling that coordinates sibling repos.
    - **NOTE**: Added `--non-interactive`, `GIT_DEV_NON_INTERACTIVE`, `CI`, and no-TTY guards to `tooling/git-dev.sh` so automated contexts skip cleanly instead of blocking on prompts. Replaced Bash-only ANSI `$'...'` assignments in the `Makefile` sync target with POSIX-compatible `printf` assignments. Validated with `bash -n tooling/git-dev.sh tooling/pr-info.sh`, `CI=true bash tooling/git-dev.sh`, `bash tooling/git-dev.sh --non-interactive`, `make -n sync`, `/bin/sh` color-assignment smoke test, `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests -p 'test_*.py'`, and `git diff --check`.
- [X] [CO-M01-04-13] Address DeepSeek review findings for PR info compatibility.
    **COMPLETED** | Architect Agent | 2026-06-07 22:40
    - **CROSS-AGENT-NOTES**: Applies to `tv7-core` developer tooling that reports PR state across sibling repos.
    - **CODE-REVIEW-NOTES**: DeepSeek flagged Bash ANSI assignments and newline handling in `tooling/pr-info.sh`, plus an inaccurate roadmap note about `git-dev.sh` array usage.
    - **NOTE**: Added a POSIX-safe Bash re-exec guard to `tooling/pr-info.sh`, replaced Bash `$'...'` ANSI assignments with `printf` assignments, restored newline-terminated PR info output, and corrected the prior roadmap note to state that `git-dev.sh` keeps Bash array usage behind its Bash guard. Validated with `bash -n tooling/git-dev.sh tooling/pr-info.sh`, `sh tooling/pr-info.sh tv7-core main`, a fake-`gh` Python-branch newline smoke test, `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests -p 'test_*.py'`, and `git diff --check`.
- [X] [CO-M01-04-14] Resolve valid DeepSeek findings for sync and review tooling.
    **COMPLETED** | Architect Agent | 2026-07-04 00:00
    - **CROSS-AGENT-NOTES**: Applies to `tv7-core` developer tooling only.
    - **CODE-REVIEW-NOTES**: Only the contract-shaped review test fixture and bounded untracked-file fingerprinting findings were classified as valid.
    - **NOTE**: Added bounded/binary-safe untracked file fingerprinting in `tooling/sync.py` and replaced fragile `object()` test placeholders with contract-shaped fixtures in `tooling/tests/test_review.py`. Validated with `PYTHONPATH=tooling python3 -m unittest tooling/tests/test_review.py`, `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests -p 'test_*.py'`, and `python3 -m py_compile tooling/sync.py tooling/review.py tooling/tests/test_review.py`.
- [P] [CO-M01-04-15] Add an optional DeepSeek reasoning profile for Codex.
    **IN-PROGRESS** | Architect Agent | 2026-07-04 00:00
    - **CROSS-AGENT-NOTES**: Applies only to optional `tv7-core` developer tooling and user-level Codex configuration; the existing OpenAI default and GitHub DeepSeek reviewer remain unchanged.

## Public Source Release

- [P] [CO-M01-05-01] Publish the six TV7 source repositories under MIT.
    **IN-PROGRESS** | CV Publication Agent | 2026-10-29
    - **NOTE**: Human approved publication and MIT licensing. Scope excludes .github-private and uncommitted local work.
