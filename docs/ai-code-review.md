# AI Code Review (DeepSeek)

`tv7-core` provides a reusable GitHub Actions workflow to run **DeepSeek** as the sole AI reviewer on pull requests. Other TV7 repos can consume it via `uses:` without duplicating logic.

## How the reusable workflow works
- Location: `.github/workflows/deepseek-review.yml` (type: `workflow_call`).
- Guardrails: only runs when the PR base branch matches `run_on_branches` (default `main`) and when the total changed lines (added + deleted) meets `min_changed_lines` (default `5`).
- Scope: fetches and sends only the PR diff (truncated to 120KB) to control cost.
- Output: posts a single PR comment with DeepSeek’s feedback.

## Enable in another repo
Create `.github/workflows/ai-review.yml` in the target repo:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  deepseek-review:
    uses: TV7-Clip-Studio/tv7-core/.github/workflows/deepseek-review.yml@main
    secrets: inherit
```

### Optional inputs (cost guardrails)
- `run_on_branches` (default: `"main"`): limit reviews to specific base branches (comma/space separated).
- `min_changed_lines` (default: `5`): skip tiny diffs.

Example override:

```yaml
jobs:
  deepseek-review:
    uses: TV7-Clip-Studio/tv7-core/.github/workflows/deepseek-review.yml@main
    secrets: inherit
    with:
      run_on_branches: "main release/*"
      min_changed_lines: 10
```

## Required secret
- `DEEPSEEK_API_KEY` must be defined at the org or repo level.
  - Org-level: Settings → Secrets and variables → Actions → New organization secret (scope it to all TV7 repos or select ones).
  - Repo-level: Repo Settings → Secrets and variables → Actions → New repository secret.
- The wrapper uses `secrets: inherit`, so the reusable workflow can read `DEEPSEEK_API_KEY` and the built-in `GITHUB_TOKEN`.

### CLI helper to set secrets in bulk
- Script: `tooling/set-secret.sh` (generic; pass `SECRET_NAME`/`SECRET_VALUE`).
- Requirements: `gh` CLI authenticated with admin rights on target repos, `jq` installed.
- Usage examples:
  - `SECRET_NAME=DEEPSEEK_API_KEY REPOS="tv7-core tv7-fastapi-backend" ./tooling/set-secret.sh`
  - `SECRET_NAME=DEEPSEEK_API_KEY ALL=1 ./tooling/set-secret.sh` (applies to all repos in org `TV7-Clip-Studio`; ensure your plan allows private repo secrets)
- The script prompts for the secret value if not provided; it sets repo-level secrets (org-level secrets for private repos require a paid plan).

## Notes on cost and behavior
- The workflow sends only the diff (not the whole repo) and truncates to 120KB to reduce token use.
- Guardrails prevent runs on unintended branches or tiny changes.
- The prompt asks for concise, high-signal findings (bugs, security, edge cases, maintainability) in Markdown.
