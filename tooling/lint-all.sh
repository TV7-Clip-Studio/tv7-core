#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-..}"
REPOS=${REPOS:-"tv7-engine tv7-backend tv7-studio tv7-site"}

for repo in $REPOS; do
  path="$REPO_ROOT/$repo"
  if [ ! -d "$path/.git" ]; then
    echo "!! Skipping $repo (missing at $path)"
    continue
  fi
  echo "== Lint $repo =="
  if make -C "$path" -q lint >/dev/null 2>&1; then
    make -C "$path" lint
  elif make -C "$path" -q check >/dev/null 2>&1; then
    make -C "$path" check
  else
    echo "No lint/check target found in $repo; skip."
  fi
done
