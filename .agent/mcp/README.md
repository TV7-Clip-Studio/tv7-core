# TV7 MCP Servers

This folder contains local MCP servers and a suggested scoping map for TV7 roles
and repos. Use the map to enable only the MCPs needed for the current repo or
agent role.

## MCP 101 (short)
- An MCP server is a local/remote process that exposes tools over a standard
  protocol (often stdio). The client lists tools and calls them by name.
- Clients enable/disable servers per workspace or role using a config file.
- Keep servers focused: smaller tools are easier to secure, upgrade, and debug.

## Servers
- tv7_media: Rust MCP for media analysis + transform operations.

## Recommended MCPs (high value)
- github: PRs, issues, and repo metadata.
- git: local git operations (status/diff/log).
- filesystem: safe read/write with scoped roots.
- fetch: HTTP fetch for docs/specs when needed.
- memory (optional): persistent notes per agent.

These are recommendations only; install/enable them per repo/role in the Codex
app or via CLI config. See scopes.json for the suggested mapping.

## Scoping map
- Defaults: context7 (all roles/repos)
- Architect: tv7_media
- Engine (tv7-axum-engine): tv7_media
- Backend (tv7-fastapi-backend): defaults only
- Studio (tv7-flutter-studio): defaults only
- Site (tv7-astro-site): defaults only
- Core (tv7-core): defaults only

See scopes.json for the exact mapping and defaults.

## Running tv7_media locally
- From repo root: .agent/mcp/tv7-media-mcp/scripts/run-mcp.sh
- Or: (cd .agent/mcp/tv7-media-mcp && cargo run --quiet --bin tv7-media-mcp)

## Safety and path controls
Set TV7_MCP_ALLOWED_ROOTS to a comma-separated list of allowed path prefixes,
for example:
  TV7_MCP_ALLOWED_ROOTS=/Users/you/Documents/TV7,/tmp

If set, all input/output paths must fall under one of those roots.
