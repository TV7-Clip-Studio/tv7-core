# TV7 Agent Manifesto

## 1. Prime Directive
**Plan First. Execute Second. Read Global. Write Local.**

## 2. The Immutable Laws
1.  **Never Execute Without Approval**: You must ALWAYS output a numbered **Implementation Plan** and wait for the user to give permission to proceed. Treat approvals like "execute", "go", "proceed", or similar as valid. For explicit bug-fix requests, proceed directly with the fix once the plan is shared (no extra "execute" gate).
2.  **Respect Boundaries**: You may READ `tv7-core` and other repos for context, but you must ONLY WRITE to your active repository.
3.  **Secrets are Fatal**: If you see a secret or token, STOP. Never log it, never commit it.

## 3. The Standard Workflow
1.  **Claim**: Check `tv7-core/docs/roadmaps/roadmap.md`. Mark your task `IN_PROGRESS` (Rule: One owner only).
2.  **Plan**: Analyze the request. Check `tv7-core/docs` for architecture. Output a clear Plan.
3.  **Wait**: Do not touch a single code file until the user approves (approval can be "execute", "go", "proceed", or similar; bug-fix requests are pre-approved once the plan is shared).
4.  **Execute**: Implement the plan step-by-step.
5.  **Verify**: Run the project-specific linter/test command.
6.  **Complete**: Mark `roadmap.md` task `DONE` and add status subtitle (`**STATUS** | AGENT | DATE`).

## 4. Cross-Repo Protocol
- **Need to change shared docs?** → Ask user to switch to `tv7-core` (or use the Architect Agent).
- **Need to change the backend API?** → Plan the change, implement in Backend, then handoff to Flutter agent.
- **NEVER** try to refactor the whole ecosystem in one go (unless you are the **Architect Agent** handling a multi-repo task).

## 5. Coding Philosophy
- **Testing Standard**: Code first, then tests. Iterate. Code is not "done" without coverage.
- **Observability**: Logs are your eyes. Log significant events so we can debug later.
- **Readability**: Code must tell a story. Use human-readable variable names.
    - Write for the next human, not the compiler.
    - Comments: Only when needed. Explain *why*, not *what*.

## 6. The 3 Pillars of Speed
1.  **Search**: Use `grep_search` and `find_by_name` to orient yourself before reading.
2.  **View**: Use `view_file_outline` to understand a file's structure before `view_file`.
3.  **Edit**: Use `multi_replace_file_content` for non-contiguous changes to save time and tokens.

## 8. Custom MCP Tools
This workspace includes custom Model Context Protocol (MCP) servers to bridge the gap between AI agents and local engines.
- **`tv7-media-mcp`**: Provides high-performance media probing and clipping. ALWAYS check if a media task can be performed via this tool before attempting raw FFMPEG commands.
- **Location**: `.agent/mcp/tv7-media-mcp`
- **Python (`tv7-fastapi-backend`)**:
    - `make check` (Run all checks) or individual: `make fmt`, `make lint`, `make type`, `make sec`, `make test`
    - **Note**: `make up` to start services.
- **Flutter (`tv7-flutter-studio`)**:
    - `make check` (Format, Analyze, Test)
    - **Note**: `make run-desktop` to launch.
    - **Workflow**: Use `/sync-backend-to-flutter` after backend changes.
- **Rust (`tv7-axum-engine`)**:
    - *Tooling pending.* Use `cargo check` / `cargo clippy` for now.
- **Astro (`tv7-astro-site`)**:
    - `npm run lint`, `npm run format` (Standard)
