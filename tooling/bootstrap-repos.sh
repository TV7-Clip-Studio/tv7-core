#!/usr/bin/env bash
set -euo pipefail

# Clone all TV7 repos (if missing) and ensure the shared submodule is mounted as 00-tv7-core/.
# Leaves existing non-git directories untouched (prints a warning).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Default to parent folder of tv7-core (sibling repos live alongside it)
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR/../..}"
CORE_URL="${CORE_URL:-https://github.com/TV7-Clip-Studio/tv7-core.git}"

quiet="${QUIET:-0}"
log() { [ "$quiet" = "1" ] || echo "$@"; }
warn() { echo "$@" >&2; }

declare -A REPO_URLS=(
  ["tv7-axum-engine"]="https://github.com/TV7-Clip-Studio/tv7-axum-engine.git"
  ["tv7-fastapi-backend"]="https://github.com/TV7-Clip-Studio/tv7-fastapi-backend.git"
  ["tv7-flutter-studio"]="https://github.com/TV7-Clip-Studio/tv7-flutter-studio.git"
  ["tv7-astro-site"]="https://github.com/TV7-Clip-Studio/tv7-astro-site.git"
)

for repo in "${!REPO_URLS[@]}"; do
  url="${REPO_URLS[$repo]}"
  path="$REPO_ROOT/$repo"

  if [ ! -d "$path/.git" ]; then
    if [ -d "$path" ]; then
      warn "!! $repo exists but is not a git repo at $path — skipping. Clean it up or init git manually."
      continue
    fi
    log "== Cloning $repo =="
    git clone "$url" "$path"
  fi

  if [ -d "$path/.git" ]; then
    origin_url="$(git -C "$path" config --get remote.origin.url || true)"
    if [ "$origin_url" != "$url" ]; then
      warn "!! $repo origin mismatch: found '$origin_url', expected '$url' — fixing origin."
      git -C "$path" remote set-url origin "$url"
    fi
    if [ ! -d "$path/00-tv7-core/.git" ] && [ ! -d "$path/00-tv7-core" ]; then
      log "== Adding 00-tv7-core submodule to $repo =="
      git -C "$path" submodule add "$CORE_URL" 00-tv7-core || true
    fi
    log "== Initializing/updating 00-tv7-core in $repo =="
    git -C "$path" submodule update --init --recursive 00-tv7-core
  fi
done

[ "$quiet" = "1" ] || echo "Done. Commit submodule additions in each repo as needed."
