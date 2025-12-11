# Symlink Map and Repo Handoff

Authoritative instructions for how other TV7 repos mount `tv7-core` via symlinks.

## Workspace layout (required)
Clone all repos as siblings:
```
./TV7/
  tv7-core/
  tv7-fastapi-backend/
  tv7-astro-site/
  tv7-flutter-studio/
  tv7-axum-engine/
```
- Supported: macOS, Linux, WSL2/Ubuntu. Native Windows is not supported for symlinks.

## Symlink map (per repo)
- `docs/core -> ../tv7-core/docs`
- `docs/high-architecture -> ../tv7-core/docs/high-architecture`
- `docs/roadmaps -> ../tv7-core/docs/roadmaps`
- `Makefile.core -> ../tv7-core/tooling/Makefile.core`

## Migration steps for repo agents
1) Remove the `tv7-core` submodule (from repo root):
```
git submodule deinit -f tv7-core
git rm -f tv7-core
rm .gitmodules  # only if core was the sole submodule entry
```
2) Add symlinks (from repo root):
```
ln -s ../tv7-core/docs docs/core
ln -s ../tv7-core/docs/high-architecture docs/high-architecture
ln -s ../tv7-core/docs/roadmaps docs/roadmaps
ln -s ../tv7-core/tooling/Makefile.core Makefile.core
```
3) Commit in the downstream repo (symlinks only).

## Makefile guardrail (per repo)
Add to the downstream repo `Makefile`:
```
CORE_DIR := ../tv7-core
ifeq ("$(wildcard $(CORE_DIR))","")
$(error tv7-core not found. Please clone it as a sibling directory: ../tv7-core)
endif
```
Optional helpers:
- `core-status`: `cd ../tv7-core && git status`
- `core-commit`: `cd ../tv7-core && git commit -am "Update from $(shell basename $$PWD)"`

## Editing workflow
- Edit shared docs/tooling through the symlink inside the downstream repo.
- Changes are recorded in `tv7-core`; commit/push from `tv7-core`.
- Downstream repo remains clean except for the symlink pointers.
