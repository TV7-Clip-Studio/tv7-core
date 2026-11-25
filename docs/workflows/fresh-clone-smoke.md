# Fresh clone smoke test

Use a new workspace with sibling checkouts. The browser smoke needs Core, Backend, Engine, and Studio. Conductor is optional. The private Site repository requires separately granted GitHub access and is independent of the browser stack.

```sh
mkdir tv7-smoke
cd tv7-smoke
for repo in core backend engine studio; do
  git clone "https://github.com/TV7-Clip-Studio/tv7-$repo.git"
done
for repo in core backend engine studio; do
  git -C "tv7-$repo" rev-parse HEAD
done
```

Use Python 3.12, Node 22 with npm, a stable Rust toolchain, Git, Make, and FFmpeg with FFprobe. On macOS install the command-line developer tools. On Ubuntu install the standard C build tools, pkg-config, OpenSSL development headers, and Python venv support. Native Tauri packaging has separate prerequisites and is outside this browser smoke.

```sh
(cd tv7-backend && python3.12 -m venv .venv &&
  .venv/bin/python -m pip install -c requirements-dev.lock -e '.[dev]')
(cd tv7-studio && npm ci)
(cd tv7-engine && cargo build --locked -p engine-service)
(cd tv7-core && make check)
```

Check that sibling links such as `.agent` and `docs/core` resolve from Studio, Backend, and Engine. Run this in a shell without production credentials or service overrides. The launcher creates disposable SQLite state under Core's `docs/.tmp/dev-browser-stack`. Keep account passwords, local environment files, database state, licensed media, and model weights outside Git.

Use a temporary password typed into your shell without echo. The launcher creates the disposable login when `TV7_TEST_PASSWORD` is set. The default email is `tv7-automation@example.com`.

```sh
cd tv7-core
make dev-browser-up
make dev-browser-status
```

Status succeeds only when Backend readiness at port 8000, Engine health at 7070, and Studio at 8080 all respond. Inspect service logs under `docs/.tmp/dev-browser-stack` on failure. If ports are occupied by another workspace, coordinate with its owner to free the ports before starting this stack.

Open Studio at `http://127.0.0.1:8080/`. Sign in, import a neutral local fixture, create a timed clip, preview and export it, then decode the output with FFmpeg. For a transcription-dependent path, install the optional Whisper runtime described in [Development](../../DEVELOPMENT.md). YouTube OAuth and publishing require separate configuration. Run `make dev-browser-stop` after the smoke. Record OS, repository heads, dependency versions, and whether this was a health check or a full media journey.

For optional orchestration, clone Conductor as a sibling and follow its bootstrap instructions. A machine-local Agent Orchestrator YAML is optional operator configuration. PostgreSQL migrations and campaign integration need a separate Backend check.
