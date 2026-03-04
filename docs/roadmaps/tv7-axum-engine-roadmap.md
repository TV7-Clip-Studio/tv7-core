# TV7 Axum Engine Roadmap

Roadmap Code: AX
Batch Code: A01

Last updated: 2026-02-08

## Done
- [X] [AX-A01-01-01] Created Rust workspace with `engine-core` and `engine-service` crates.
- [X] [AX-A01-01-02] Added initial `engine-core` media probing stub and basic workspace dependency setup.
- [X] [AX-A01-01-03] Documented local-first architecture intent (loopback sidecar, no business logic in engine).

## Needs To Be Done
- [ ] [AX-A01-02-01] Replace stub media probing with real implementations and strong error handling.
- [ ] [AX-A01-02-02] Build `engine-service` Axum HTTP surface to match expected local engine contract.
- [ ] [AX-A01-02-03] Add configuration/logging defaults (port, work dir, log level) and startup validation.
- [ ] [AX-A01-02-04] Introduce trait-driven boundaries in core so service and future FFI integrations share logic.
- [ ] [AX-A01-02-05] Add basic test coverage and command-level verification (`cargo check`, `cargo test`, `cargo clippy`).

## Nice To Have
- [ ] [AX-A01-03-01] Add `engine-ffi` crate stub for Flutter/mobile interoperability planning.
- [ ] [AX-A01-03-02] Add benchmark harness for probe/transcode/transcription hot paths.
- [ ] [AX-A01-03-03] Add feature flags for optional GPU acceleration and model backends.
- [ ] [AX-A01-03-04] Publish a compatibility matrix for supported codecs, formats, and platform constraints.
