# Studio Testing Strategy

Updated: 2026-10-01. Run `make check` in `tv7-studio` for lint and browser build; run `npm run desktop:build` for package verification. Test creator workflows in the browser UI against the loopback Engine and disposable Backend stack, then verify native-only sidecar startup, authentication, rendering, and shutdown separately in the packaged app.

Check the boundaries independently: a healthy listener does not prove import, rendering, private upload, ownership, schedule persistence, or publication. Inspect the rendered file with FFprobe. Confirm that cloud handoff uploads only an approved finished asset and that a schedule draft remains visibly distinct from a published post. Live platform publishing requires separate provider-side verification.
