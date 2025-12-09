#!/bin/bash
# tv7-core/tooling/install-deps.sh
# Auto-detects project type and installs dependencies.
# Behavior:
# - Visits each repo under REPO_ROOT and installs deps unless SKIP_DEPS=1.
# - Requires relevant package managers to be pre-installed (poetry/pip, npm, cargo, flutter).
# Usage: SKIP_DEPS=1 ./install-deps.sh  # skip installs
#        ./install-deps.sh              # install deps

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR/../..}"
SKIP_DEPS="${SKIP_DEPS:-0}"

RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; MAGENTA='\033[35m'; BOLD='\033[1m'; RESET='\033[0m'
log_info(){ printf " ${BLUE}ℹ %s${RESET}\n" "$1"; }
log_ok()  { printf " ${GREEN}✓ %s${RESET}\n" "$1"; }
log_err() { printf " ${RED}✗ %s${RESET}\n" "$1"; }

install_flutter() {
  log_info "Flutter project detected."
  if command -v flutter >/dev/null; then
    flutter pub get
    return $?
  else
    log_err "Flutter not found. Skipping."
    return 1
  fi
}

install_python() {
  log_info "Python project detected."
  if ! command -v python >/dev/null; then
    log_err "Python not found. Skipping."
    return 1
  fi
  export POETRY_VIRTUALENVS_IN_PROJECT=1
  if [ -f "pyproject.toml" ] && command -v poetry >/dev/null; then
    poetry install --no-root || return $?
  elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt || return $?
  else
    log_info "No supported Python installer found (poetry/pip)."
    return 1
  fi
  return 0
}

install_rust() {
  log_info "Rust project detected."
  if command -v cargo >/dev/null; then
    # We don't necessarily want to build, just fetch deps
    cargo fetch || return $?
  else
    log_err "Cargo not found. Skipping."
    return 1
  fi
  return 0
}

install_node() {
  log_info "Node project detected."
  if command -v npm >/dev/null; then
    if [ -f package.json ]; then
      engine_node="$(jq -r '.engines.node // empty' package.json 2>/dev/null || true)"
      engine_npm="$(jq -r '.engines.npm // empty' package.json 2>/dev/null || true)"
      if [ -n "$engine_node" ]; then
        log_warn "package.json engines.node=$engine_node; current node=$(node -v)"
      fi
      if [ -n "$engine_npm" ]; then
        log_warn "package.json engines.npm=$engine_npm; current npm=$(npm -v)"
      fi
    fi
    npm install || return $?
  else
    log_err "npm not found. Skipping."
    return 1
  fi
  return 0
}

# Iterate through repos
failures=()

find "$REPO_ROOT" -maxdepth 1 -mindepth 1 -type d | grep -v "\.git" | sort | while read -r repo_path; do
  repo_name="$(basename "$repo_path")"
  # skip core itself if needed, or non-repo dirs
  [ ! -d "$repo_path/.git" ] && continue

  printf "\n${BOLD}Installing dependencies for ${MAGENTA}%s${RESET}...\n" "$repo_name"
  if [ "$SKIP_DEPS" = "1" ]; then
    log_info "Skipping installs (SKIP_DEPS=1)."
    continue
  fi
  
  cd "$repo_path"
  rc=0

  # shallow manifest search (depth 2)
  manifest_pub=$(find . -maxdepth 2 -name "pubspec.yaml" | head -n 1)
  manifest_cargo=$(find . -maxdepth 2 -name "Cargo.toml" | head -n 1)
  manifest_pkg=$(find . -maxdepth 2 -name "package.json" | head -n 1)
  manifest_py=$(find . -maxdepth 2 -name "pyproject.toml" -o -name "requirements.txt" | head -n 1)

  if [ -n "$manifest_pub" ]; then
    cd "$(dirname "$manifest_pub")" && install_flutter || rc=$?
  elif [ -n "$manifest_cargo" ]; then
    cd "$(dirname "$manifest_cargo")" && install_rust || rc=$?
  elif [ -n "$manifest_pkg" ]; then
    cd "$(dirname "$manifest_pkg")" && install_node || rc=$?
  elif [ -n "$manifest_py" ]; then
    cd "$(dirname "$manifest_py")" && install_python || rc=$?
  else
    log_info "Unknown project type. Skipping."
  fi

  if [ "$SKIP_DEPS" = "0" ] && [ "$rc" -ne 0 ]; then
    log_err "Dependency install may have failed for $repo_name."
    failures+=("$repo_name")
  fi
done

if [ "$SKIP_DEPS" = "0" ] && [ "${#failures[@]}" -gt 0 ]; then
  printf "\n${RED}Install issues for: %s${RESET}\n" "${failures[*]}"
fi
