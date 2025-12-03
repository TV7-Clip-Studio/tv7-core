# Versioning Rules

Policy
- SemVer per repo: `MAJOR.MINOR.PATCH`.
- Breaking API/contract changes → increment `MAJOR`.
- Backwards-compatible features → increment `MINOR`.
- Fixes/non-breaking tweaks → increment `PATCH`.

Coordination
- If a change impacts cross-repo contracts (e.g., engine API, backend contract consumed by Flutter), document it in `meta/decisions_log.md` and communicate in release notes.
- Tag releases in each repo; avoid a global mono-version.

Release artifacts
- Backend: tag Git, build/publish container.
- Engine: tag Git, build signed binaries as applicable.
- Flutter: tag Git, produce desktop/mobile builds with matching engine version pin.
- Astro site: tag Git, deploy static build.
