# TV7 — Local-first video clipping studio

TV7 is an independent multi-repository engineering project maintained by [Joaquin Astelarra](https://github.com/joaquinlarra). It combines a creator interface, local media processing, and a cloud control plane with shared API contracts and validation workflows.

## Source repositories

| Repository | Responsibility | Main technologies |
| --- | --- | --- |
| [Studio](https://github.com/TV7-Clip-Studio/tv7-studio) | Creator interface and local workflow orchestration | React, TypeScript, Tauri |
| [Engine](https://github.com/TV7-Clip-Studio/tv7-engine) | Loopback media compute, ingest, transcription dispatch, rendering | Rust, Axum, FFmpeg integration |
| [Backend](https://github.com/TV7-Clip-Studio/tv7-backend) | Authentication, private assets, clip metadata, scheduling | Python, FastAPI, PostgreSQL, Alembic |
| [Core](https://github.com/TV7-Clip-Studio/tv7-core) | Architecture, API contracts, cross-repository tooling | OpenAPI, Python, shell |
| [Conductor](https://github.com/TV7-Clip-Studio/tv7-conductor) | Agent workflow orchestration, validation and review lifecycle | Python |
| [Site](https://github.com/TV7-Clip-Studio/tv7-site) | Marketing and documentation website | Astro, TypeScript, Tailwind |

## Engineering work

My work spans architecture and service boundaries, implementation and integration, API contracts, tests, CI, code review, and coordination across the repositories. AI coding tools assist development; engineering changes still require review and validation.

Relevant areas for code review include Engine media job handling, Backend authentication and asset ownership, Studio API orchestration, and Conductor validation/review transitions. Tests live beside each component; each README describes its checks.

## Status and limitations

This is source for a project in development, not a production service or supported public binary release. Current component READMEs describe implemented paths and outstanding work. A schedule draft does not establish successful provider publishing. Browser/component checks do not establish clean-install desktop readiness.

Clone the repositories as siblings and start with [DEVELOPMENT.md](DEVELOPMENT.md). Some optional agent governance files refer to private workspace tooling; that tooling is not part of this public release.

## Publication and licensing

These repositories are being made public in October 2026 with existing Git history retained. Publication does not imply that the repositories were public throughout their development. The MIT license covers TV7 source; third-party packages, host binaries, models, and services retain their own licenses and terms.
