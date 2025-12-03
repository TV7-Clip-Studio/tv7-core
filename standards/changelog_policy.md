# Changelog Policy

Per-repo changelog
- Maintain `CHANGELOG.md` per repo with date/version sections.
- Capture: features, fixes, breaking changes, dependency bumps, and cross-repo impacts.

Cross-repo notes
- When a change affects multiple repos (e.g., engine API change requiring app/back-end updates), note it in `meta/decisions_log.md` and reference affected versions.

Process
- Update changelog as part of PRs that change behavior.
- For releases, summarize highlights and breaking changes, linking to detailed ADRs when relevant.
