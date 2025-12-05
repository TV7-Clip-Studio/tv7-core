#!/usr/bin/env bash
set -euo pipefail

# Set a GitHub Actions secret across repos using GitHub CLI.
# Usage examples (run from repo root):
#   SECRET_NAME=DEEPSEEK_API_KEY REPOS="tv7-core tv7-fastapi-backend" ./tooling/set-secret.sh
#   SECRET_NAME=DEEPSEEK_API_KEY ALL=1 ./tooling/set-secret.sh   # all repos in ORG
#
# Env vars:
#   ORG          (default: TV7-Clip-Studio)
#   SECRET_NAME  (required, e.g., DEEPSEEK_API_KEY)
#   SECRET_VALUE (optional; if not set, script prompts)
#   REPOS        (space-separated list)
#   ALL          (set to 1 to target all repos in ORG)
#
# Notes:
#   - Requires: gh CLI (authenticated with repo admin), jq.
#   - For private repos, org-level secrets require a paid GitHub plan; this script sets repo-level secrets.

ORG="${ORG:-TV7-Clip-Studio}"
SECRET_NAME="${SECRET_NAME:-}"
REPOS="${REPOS:-}"
ALL="${ALL:-}"
SECRET_VALUE="${SECRET_VALUE:-}"

if [ -z "$SECRET_NAME" ]; then
  echo "SECRET_NAME is required (e.g., DEEPSEEK_API_KEY)." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required; install from https://cli.github.com/" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required; install it first." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "gh is not authenticated; run 'gh auth login' first." >&2
  exit 1
fi

if [ -z "$SECRET_VALUE" ]; then
  read -rsp "Enter value for ${SECRET_NAME}: " SECRET_VALUE
  echo
fi

readarray -t repos <<< "$( \
  if [ -n "$ALL" ]; then
    gh repo list "$ORG" --limit 200 --json name --jq '.[].name'
  elif [ -n "$REPOS" ]; then
    tr ' ' '\n' <<< "$REPOS"
  else
    echo "No repos specified. Set REPOS=\"repo1 repo2\" or ALL=1." >&2
    exit 1
  fi \
)"

for repo in "${repos[@]}"; do
  full="$ORG/$repo"
  echo "Setting $SECRET_NAME in $full"
  gh secret set "$SECRET_NAME" --body "$SECRET_VALUE" --repo "$full" >/dev/null
done

echo "Done. Confirm via: gh secret list -R $ORG/<repo>"
