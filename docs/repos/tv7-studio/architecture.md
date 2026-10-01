# TV7 Studio Architecture

Updated: 2026-10-01. The live Studio is the React/TypeScript app at the root of `tv7-studio`, packaged for macOS with Tauri. The same screens run in a browser for repeatable testing. The former Flutter app is retired.

Studio owns creator UX and coordinates a local Rust Engine. Engine owns source import, probing, transcript-related work, and rendering. Cloud Backend owns identity, licensing, private approved assets, schedule truth, and publishing. Rendering does not run in Backend.

The packaged app starts an authenticated Engine child on loopback and stops it on exit. Browser development connects to a separately started loopback Engine. A creator must approve transferring a finished render to Backend before creating a schedule draft. A draft does not imply a published post.

See `docs/architecture/downloadable-studio.md` for the product boundary and remaining release gates.
