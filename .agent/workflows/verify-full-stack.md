---
description: Verify the Studio, Engine, and Backend integration boundaries.
---

# Verify Full Stack

1. In `tv7-backend`, run `make lint`, `make type`, and `make test`.
2. In `tv7-engine`, run `cargo check --workspace --all-targets` and `cargo test --workspace`.
3. In `tv7-studio`, run `make check`; run `make package` when desktop code changes.
4. From `tv7-core`, run `make dev-browser-up` and `make dev-browser-status`. Use the browser UI to verify import, render, approved private upload, and schedule draft status. Native-only Engine sidecar behavior needs a separate packaged-app check.
5. Compare Backend and Engine endpoints consumed by Studio with the checked-in Core OpenAPI artifacts. Treat a draft, queued job, and public provider post as distinct states.
