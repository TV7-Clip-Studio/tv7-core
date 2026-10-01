# TV7 Core Roadmap

Roadmap Code: CO
Batch Code: A01

Last updated: 2026-05-21

## Done
- [X] [CO-A01-01-01] Established `tv7-core` as the shared docs/tooling repo with symlink-first workflow.
- [X] [CO-A01-01-02] Standardized sibling workspace layout across `tv7-*` repositories.
- [X] [CO-A01-01-03] Added shared Make targets for cross-repo bootstrap/sync/status flows.
- [X] [CO-A01-01-04] Consolidated global architecture and agent workflow docs into core-managed paths.

## Needs To Be Done
- [ ] [CO-A01-02-01] Complete docs reorganization so every active reference resolves without legacy fallbacks.
- [X] [CO-A01-02-02] Keep the product coordination roadmap current with active owners and status updates.
    **COMPLETED** | Architect Agent | 2026-07-09 00:00
    - **NOTE**: Clarified cockpit next-action ordering for dirty open-PR branches so validated local follow-up work proceeds toward human validation or commit before PR review/merge decisions. Validated with targeted cockpit tests, Python compilation, and `make precommit-context`.
- [ ] [CO-A01-02-03] Add a stable index for standards, architecture, and runbooks to reduce path drift.
- [ ] [CO-A01-02-04] Tighten governance around what is allowed in repo-local docs vs core docs.
- [X] [CO-A01-02-05] Document shared symlink coordination and Codex app visibility caveats.
    **COMPLETED** | Core Agent | 2026-05-21 00:00
    - **CROSS-AGENT-NOTES**: Applies to all TV7 product repos using `.agent`, `docs/core`, and `Makefile.core` symlinks.
    - **NOTE**: Added `docs/repos/symlink-coordination.md`, indexed it from `docs/repos/README.md`, and updated `.agent/rules/project-context.md` to tell agents to verify symlinks from the terminal when the Codex app file tree hides them.
- [X] [CO-A01-02-06] Establish a repeatable agent access path across Studio, Backend, and Engine.
    **COMPLETED** | Architect Agent | 2026-10-01 10:30
    - **CROSS-AGENT-NOTES**: Studio browser workflow implementation is owned by the Studio Agent; Core records entry points and verification.
    - **NOTE**: Added `docs/repos/agent-access.md` and verified browser Studio sign-in, one-second video upload, source playback, User license state, and Diagnostics showing Backend and Engine ready. Native Computer Use times out on both TV7 Studio and a fresh Flutter macOS sample; desktop-only flows remain unverified.
- [P] [CO-A01-02-07] Prove one shared downloadable Studio UI with local media processing and cloud scheduling boundaries.
    **IN-PROGRESS** | Architect Agent | 2026-10-01 11:08
    - **CROSS-AGENT-NOTES**: Studio owns the React/Tauri proof, Engine owns local media import and selected channel jobs, Backend owns truthful scheduling foundations. Architect owns the cross-repo contract and integrated verification.
    - **NOTE**: React/Tauri runs the same UI on browser port 8080 and in a packaged macOS app. Browser Computer Use imported/probed a synthetic MP4, discovered 25 channel videos, and reached explicit selected-download confirmation without downloading. Native Computer Use verified a bundled Engine child, video and VTT import, candidate review, timing adjustment, and captioned render; quitting stopped the child. A random per-session bearer token protects every packaged Engine route; missing/wrong tokens returned 401. Flutter was retired; Windows build, bundled runtime dependencies, durable editing, and real scheduled publishing remain open.

- [X] [CO-A01-02-08] Retire Flutter Studio and align active repos, tooling, and agent guidance with the React/Tauri root app.
    **COMPLETED** | Architect Agent | 2026-10-01 12:45
    - **CROSS-AGENT-NOTES**: Studio removed the old client and promoted Tauri; Backend removed unused media storage/debug code; Engine ignored generated local assets; Core updated dev entry points and canonical docs.
    - **NOTE**: Core browser stack restarted from the Studio root; Vite :5173 showed Engine connected; Core's 69 tests, media MCP check, Backend 76 tests, Engine workspace check, Studio browser and macOS package checks passed. Packaging dependencies and product workflow gaps remain separately tracked.

## Nice To Have
- [ ] [CO-A01-03-01] Add a docs link checker in CI for all markdown links and symlink targets.
- [ ] [CO-A01-03-02] Publish shared templates for recurring deliverables (roadmap updates, ADRs, handoffs).
- [ ] [CO-A01-03-03] Add a single command for validating all repo symlinks and reporting drift.
    **BACKLOG** | Core Agent | 2026-05-21 00:00
    - **NOTE**: Should verify `.agent`, `docs/core`, `Makefile.core`, and repo-specific contract symlinks where applicable.
