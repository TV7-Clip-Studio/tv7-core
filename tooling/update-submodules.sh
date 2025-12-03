#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-..}"
SUBMODULE_PATH="${SUBMODULE_PATH:-00-tv7-core}"
REPOS=${REPOS:-"tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site"}

for repo in $REPOS; do
  path="$REPO_ROOT/$repo"
  if [ ! -d "$path/.git" ]; then
    echo "!! Skipping $repo (missing at $path)"
    continue
  fi
  echo "== Updating $SUBMODULE_PATH in $repo =="
  git -C "$path" submodule update --remote "$SUBMODULE_PATH"
  git -C "$path" add "$SUBMODULE_PATH" || true
done

echo "Done. Commit/push submodule bumps in each repo."
