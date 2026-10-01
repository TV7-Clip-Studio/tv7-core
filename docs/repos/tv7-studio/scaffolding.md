# Studio Structure and Commands

Updated: 2026-10-01. The repository root contains `package.json`, Vite configuration, and `src/` for the shared React UI. `src-tauri/` contains the desktop shell and Engine sidecar integration. There is no Flutter project or generated Dart SDK.

Run `npm install`, `npm run dev` for browser development, `npm run build` for the browser bundle, and `npm run desktop:build` for the macOS package. Run `make check` from the Studio repository for its standard validation. From Core, `make dev-browser-up` serves a production UI build on `:8080` with Backend and Engine; `make dev-studio` starts Vite on `:5173`.

Keep `node_modules/`, `dist/`, `src-tauri/target/`, local media, and credentials out of Git. The canonical Backend and Engine OpenAPI contracts live in `tv7-core/docs/contracts/openapi/`.
