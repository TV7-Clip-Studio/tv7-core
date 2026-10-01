# Agent access to the local TV7 stack

Use the browser stack when an agent needs to navigate Studio and verify that it talks to Backend and Engine. Run these commands from `tv7-core`:

```sh
make dev-browser-up
make dev-browser-status
```

The stack binds only to loopback. Its test database is separate from the normal development database. Set `TV7_TEST_EMAIL` and `TV7_TEST_PASSWORD` in the local environment before `make dev-browser-up` to create or reset a disposable login. Keep the password out of shell history, logs, and documentation. The account is needed for authenticated Studio and Backend flows.

| Component | Agent entry point | What it verifies |
| --- | --- | --- |
| Studio | `http://127.0.0.1:8080/` | Same React UI as the packaged Tauri app: local media flow and optional approved cloud handoff. |
| Backend | `http://127.0.0.1:8000/docs` | FastAPI contract and authenticated control-plane calls; `/readyz` is its readiness check. |
| Engine | `http://127.0.0.1:7070/health` | Local compute service readiness; inspect its API surface from the Studio Diagnostics view or Engine contract. |

Open Studio in the Codex in-app browser and test it as a user. A successful `make dev-browser-status` confirms listeners only; verify sign-in, media ingestion, rendering, ownership, and schedule drafts through the UI and authenticated APIs. The browser and desktop package use the same React screens. The packaged app starts its own authenticated Engine child; the development browser uses the shared loopback Engine.

## Native Studio access

The macOS Tauri package was exercised with native Computer Use: local video and caption import, candidate review, timing edit, and captioned render completed. Browser UI tests remain the repeatable path for cross-service workflows. Windows packaging and live platform publishing remain unverified.

After updating Studio, run `make dev-browser-up` to rebuild, then reload the tab. The running `http.server` serves `dist` from disk, so the browser may otherwise show an older build.

Use `make dev-browser-stop` to stop the loopback stack.
