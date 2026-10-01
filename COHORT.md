# TV7 development cohort

The Architect owns cross-repository decisions and integration. A task gets one named implementation owner. Other agents provide bounded reviews or independent components; they do not silently edit the same files. Read the relevant repository's `AGENTS.md`, current contract, and product boundary in [`docs/architecture/downloadable-studio.md`](docs/architecture/downloadable-studio.md) before work.

| Role | Scope | Evidence to return |
| --- | --- | --- |
| Architect | Choose the next vertical slice; delegate nonoverlapping work; reconcile Studio, Engine, Backend, contracts, and live UI; decide integration. | Changed paths, cross-repo contract impact, commands and real workflow tested, remaining blockers. |
| Studio owner | React/Tauri creator UI, desktop packaging, local Engine and cloud Backend interaction. | `make check`, desktop build when relevant, and a UI walkthrough with actual service responses. |
| Engine owner | Local Rust media import, transcript, candidate, render, and sidecar behavior. | Rust checks/tests and an actual media output probe for changed rendering behavior. |
| Backend owner | Accounts, licensing, owner-scoped storage, scheduling, and platform publishing. No heavy media rendering. | Python checks/tests, migration and API contract changes, plus live endpoint evidence when relevant. |
| Agy UI reviewer | Independent UI critique or bounded alternative design on Studio. | Specific observations and proposed changes; Architect chooses what to apply. |
| DeepSeek reviewer | Optional independent code review after local validation. | Findings tied to current files/diff; Architect verifies each finding. |

## Agent use

- Use Codex subagents for separate implementation scopes. Keep the Architect responsible for integration and user-facing status.
- For Agy UI review, explicitly select a non-Claude model and plan mode. Verified from `tv7-studio`: `agy --model 'Gemini 3.8 Flash (Medium)' --mode plan --sandbox --output-format json --print-timeout 180s --print 'Review the current Studio UI for the creator import-to-render flow. Do not edit files. Return concrete usability issues with file or screen references.'` Check `agy models` if that model changes. For a durable reviewer, resume the conversation ID returned by a successful call with `--conversation ID`. Agy output is advice, not automatic authority to edit. Treat a timed-out JSON result with an empty response and zero turns as a transport failure even if it says `SUCCESS`; never silently switch to Claude.
- Keep Agy's global MCP list small. The retired `tv7-media` registration stalled every prompt while connecting; `agy mcp disable tv7-media` still launched it with CLI 1.2.14, whereas `agy mcp remove tv7-media` restored prompt execution. Use Engine directly for media operations. If Agy stops responding, run a bounded `READY` probe and inspect `agy mcp list` before relying on a review.
- For optional DeepSeek review from `tv7-core`: `python3 tooling/ai_agent.py review --repo tv7-studio --model deepseek --scope worktree`. This uses the configured DeepSeek bridge and consumes API usage. Review mode runs with a read-only Codex sandbox. `resolve` permits workspace edits and requires an explicit scoped implementation decision.
- Never select a Claude model, invoke the Claude CLI, or read/reuse MindDrift's Anthropic key for TV7. MindDrift's workflow was studied as a pattern only. Do not print or copy any provider secret into prompts, reports, or source control.
- Provider reviews do not replace repo checks or product UI testing. Do not automatically commit, push, open, close, or merge PRs as a consequence of an agent review.
