# TV7 Axum Engine Roadmap

Last updated: 2026-02-08

## Done
- [x] Created Rust workspace with `engine-core` and `engine-service` crates.
- [x] Added initial `engine-core` media probing stub and basic workspace dependency setup.
- [x] Documented local-first architecture intent (loopback sidecar, no business logic in engine).

## Needs To Be Done
- [ ] Replace stub media probing with real implementations and strong error handling.
- [ ] Build `engine-service` Axum HTTP surface to match expected local engine contract.
- [ ] Add configuration/logging defaults (port, work dir, log level) and startup validation.
- [ ] Introduce trait-driven boundaries in core so service and future FFI integrations share logic.
- [ ] Add basic test coverage and command-level verification (`cargo check`, `cargo test`, `cargo clippy`).

## Nice To Have
- [ ] Add `engine-ffi` crate stub for Flutter/mobile interoperability planning.
- [ ] Add benchmark harness for probe/transcode/transcription hot paths.
- [ ] Add feature flags for optional GPU acceleration and model backends.
- [ ] Publish a compatibility matrix for supported codecs, formats, and platform constraints.
