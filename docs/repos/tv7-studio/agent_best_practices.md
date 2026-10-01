# Studio Agent Guidance

Updated: 2026-10-01. Work in `tv7-studio` for UI and Tauri changes. Read its `AGENTS.md` and `README.md`, then use `make check` and the documented desktop build. Use `tv7-core/docs/contracts/openapi/` when changing API consumers and coordinate contract changes with Backend or Engine owners.

Keep heavy media work in the local Engine and posting execution in Backend. Do not store platform OAuth secrets in Studio. Do not present a schedule draft as a completed post, or a deterministic timing range as a viral quality score. Browser and desktop share screens, but their Engine startup and authentication paths differ; verify both when changing connection logic.
