# Repo Docs In Core

Repo-scoped documentation that is useful across teams lives here and is canonical.

## Current Repos
- `tv7-flutter-studio/` - architecture, integration docs, plans, and workflows for the Flutter client.
- `tv7-fastapi-backend/` - guides and setup docs for the FastAPI control plane.

## Workflow Docs
- `repo-policy.md` - branch/check/commit/PR standard for all repos.
- `cross-repo-policy.md` - required coordination rules for multi-repo changes.
- `batch-pr-runbook.md` - how to run and troubleshoot the batch PR automation.

## Rule
- If a doc affects cross-repo understanding, put it under `docs/repos/<repo>/`.
- Keep only runtime/local developer essentials inside downstream repos; avoid duplicated canonical docs.
