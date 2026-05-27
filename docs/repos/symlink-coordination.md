# Symlink Coordination

TV7 uses repo-local symlinks so each product repo can access shared Core guidance without duplicating files.

## Standard Symlinks

Every product repo should expose:

```text
.agent -> ../tv7-core/.agent
docs/core -> ../../tv7-core/docs
Makefile.core -> ../tv7-core/tooling/Makefile.core
```

Some repos may also expose contract-specific symlinks. For example, the FastAPI backend exposes:

```text
openapi.json -> ../tv7-core/docs/contracts/openapi/tv7-fastapi-backend/openapi.json
```

## Purpose

- `.agent` provides shared prompts, rules, skills, workflows, and MCP configuration.
- `docs/core` provides shared architecture, roadmaps, contracts, handoffs, and repo runbooks.
- `Makefile.core` provides shared workspace commands.

Agents should prefer repo-local symlink paths when working inside a product repo:

```text
./.agent/rules/project-context.md
./docs/core/agent-best-practices.md
./docs/core/contracts/...
./docs/core/roadmaps/<repo-roadmap>.md
./docs/core/handoffs/active/<handoff>.md
```

If a symlink is missing or broken, use the canonical `../tv7-core/...` path and report the drift.

## Contract Artifacts

Canonical interface contracts live under:

```text
docs/core/contracts/...
```

Do not create repo-local duplicate contract folders such as `docs/contracts` for long-lived artifacts. If a producing repo generates contract output locally, publish it into `docs/core/contracts/...` and remove or ignore the scratch output.

## Codex App Visibility

The Codex app file tree may not display symlinked directories such as `docs/core` or dot-directories such as `.agent`, even when those paths exist on disk. VS Code may show them because its explorer follows or marks symlinks differently.

This is a UI visibility issue, not proof that the coordination symlink is missing.

When a symlink is not visible in the Codex app file tree:

1. Verify it from the terminal.
2. Use the repo-local symlink path directly in shell commands.
3. Use absolute file links in final responses when referring to files.
4. Do not duplicate Core files into the product repo to make them visible.

## Verification Commands

From a product repo:

```bash
ls -la .agent docs/core Makefile.core
readlink .agent
readlink docs/core
readlink Makefile.core
```

From the workspace root:

```bash
find . -maxdepth 3 -type l -ls
```

Expected examples:

```text
tv7-axum-engine/.agent -> ../tv7-core/.agent
tv7-axum-engine/docs/core -> ../../tv7-core/docs
tv7-axum-engine/Makefile.core -> ../tv7-core/tooling/Makefile.core
```

## Agent Rule

If the file tree and terminal disagree, trust the terminal. The coordination contract is the filesystem symlink, not whether a specific UI chooses to display it.
