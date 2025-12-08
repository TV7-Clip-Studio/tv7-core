#!/bin/bash
# tv7-core/tooling/install_deps.sh
# Auto-detects project type and installs dependencies.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR/../..}"

RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; BOLD='\033[1m'; RESET='\033[0m'
log_info(){ printf " ${BLUE}ℹ %s${RESET}\n" "$1"; }
log_ok()  { printf " ${GREEN}✓ %s${RESET}\n" "$1"; }
log_err() { printf " ${RED}✗ %s${RESET}\n" "$1"; }

install_flutter() {
  log_info "Flutter project detected."
  if command -v flutter >/dev/null; then
    flutter pub get
  else
    log_err "Flutter not found. Skipping."
  fi
}

install_python() {
  log_info "Python project detected."
  if [ -f "pyproject.toml" ] && command -v poetry >/dev/null; then
    poetry install
  elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
  else
    log_info "No supported Python installer found (poetry/pip)."
  fi
}

install_rust() {
  log_info "Rust project detected."
  if command -v cargo >/dev/null; then
    # We don't necessarily want to build, just fetch deps
    cargo fetch
  else
    log_err "Cargo not found. Skipping."
  fi
}

install_node() {
  log_info "Node project detected."
  if command -v npm >/dev/null; then
    npm install
  else
    log_err "npm not found. Skipping."
  fi
}

# Iterate through repos
find "$REPO_ROOT" -maxdepth 1 -mindepth 1 -type d | grep -v "\.git" | sort | while read -r repo_path; do
  repo_name="$(basename "$repo_path")"
  # skip core itself if needed, or non-repo dirs
  [ ! -d "$repo_path/.git" ] && continue

  printf "\n${BOLD}Installing dependencies for ${MAGENTA}%s${RESET}...\n" "$repo_name"
  
  cd "$repo_path"

  if [ -f "pubspec.yaml" ]; then
    install_flutter
  elif [ -f "Cargo.toml" ]; then
    install_rust
  elif [ -f "package.json" ]; then
    install_node
  elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
    install_python
  else
    log_info "Unknown project type. Skipping."
  fi
done
