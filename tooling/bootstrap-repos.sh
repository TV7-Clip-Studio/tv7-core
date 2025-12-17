#!/usr/bin/env bash
set -euo pipefail

# Clone all TV7 repos (if missing). Leaves existing non-git directories untouched (prints a warning).
# Defaults to SSH URLs (override via TV7_*_URL envs).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Default to parent folder of tv7-core (sibling repos live alongside it)
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR/../..}"
# Override REPO_URLS by exporting REPO_URLS_JSON='{"repo":"url",...}'.

quiet="${QUIET:-0}"
log() { [ "$quiet" = "1" ] || echo "$@"; }
warn() { echo "$@" >&2; }

declare -A REPO_URLS=(
  ["tv7-axum-engine"]="${TV7_AXUM_URL:-git@github.com:TV7-Clip-Studio/tv7-axum-engine.git}"
  ["tv7-fastapi-backend"]="${TV7_FASTAPI_URL:-git@github.com:TV7-Clip-Studio/tv7-fastapi-backend.git}"
  ["tv7-flutter-studio"]="${TV7_FLUTTER_URL:-git@github.com:TV7-Clip-Studio/tv7-flutter-studio.git}"
  ["tv7-astro-site"]="${TV7_ASTRO_URL:-git@github.com:TV7-Clip-Studio/tv7-astro-site.git}"
)

ensure_link() {
  local link_path="$1"
  local target="$2"
  local label="$3"

  local link_dir
  link_dir="$(dirname "$link_path")"
  mkdir -p "$link_dir"

  if [ -L "$link_path" ]; then
    local current
    current="$(readlink "$link_path")"
    if [ "$current" != "$target" ]; then
      rm "$link_path"
      ln -s "$target" "$link_path"
      log "fixed $label symlink -> $target"
    fi
  elif [ -e "$link_path" ]; then
    warn "!! $label exists and is not a symlink at $link_path — please resolve manually"
  else
    ln -s "$target" "$link_path"
    log "added $label symlink -> $target"
  fi
}

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
    log "== $repo ready at $path =="
    ensure_link "$path/docs/core" "../../tv7-core/docs" "$repo docs/core"
    ensure_link "$path/Makefile.core" "../tv7-core/tooling/Makefile.core" "$repo Makefile.core"
  fi
done

[ "$quiet" = "1" ] || echo "Done. Clone tv7-core as a sibling; docs/core and Makefile.core symlinks ensured."
