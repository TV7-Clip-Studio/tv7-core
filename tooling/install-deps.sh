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
  PYBIN="${PYTHON_BIN:-}"
  if [ -z "$PYBIN" ]; then
    if command -v python >/dev/null; then
      PYBIN="python"
    elif command -v python3 >/dev/null; then
      PYBIN="python3"
    else
      log_err "Python not found (python/python3). Skipping."
      return 1
    fi
  fi
  if [ -f "pyproject.toml" ] && command -v poetry >/dev/null; then
    POETRY_VIRTUALENVS_IN_PROJECT=1 poetry install --no-root || return $?
  elif [ -f "requirements.txt" ]; then
    "$PYBIN" -m pip install -r requirements.txt || return $?
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
    if [ -f package.json ] && command -v jq >/dev/null; then
      engine_node="$(jq -r '.engines.node // empty' package.json 2>/dev/null || true)"
      engine_npm="$(jq -r '.engines.npm // empty' package.json 2>/dev/null || true)"
      if [ -n "$engine_node" ]; then
        log_warn "package.json engines.node=$engine_node; current node=$(node -v)"
      fi
      if [ -n "$engine_npm" ]; then
        log_warn "package.json engines.npm=$engine_npm; current npm=$(npm -v)"
      fi
    elif [ -f package.json ] && ! command -v jq >/dev/null; then
      log_warn "jq not found; skipping engines check for package.json"
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

while read -r repo_path; do
  repo_name="$(basename "$repo_path")"
  # skip core itself if needed, or non-repo dirs
  [ ! -d "$repo_path/.git" ] && continue

  printf "\n${BOLD}Installing dependencies for ${MAGENTA}%s${RESET}...\n" "$repo_name"
  if [ "$SKIP_DEPS" = "1" ]; then
    log_info "Skipping installs (SKIP_DEPS=1)."
    continue
  fi
  
  rc=0

  # shallow manifest search (prefer repo root, then depth 2)
  manifest_pub=""
  manifest_cargo=""
  manifest_pkg=""
  manifest_py=""

  [ -f "$repo_path/pubspec.yaml" ] && manifest_pub="$repo_path/pubspec.yaml"
  [ -f "$repo_path/Cargo.toml" ] && manifest_cargo="$repo_path/Cargo.toml"
  [ -f "$repo_path/package.json" ] && manifest_pkg="$repo_path/package.json"
  find "$repo_path" -maxdepth 2 -name "pyproject.toml" -o -name "requirements.txt" | head -n 1 | read -r manifest_py || true

  if [ -z "$manifest_pub" ]; then
    find "$repo_path" -maxdepth 2 -name "pubspec.yaml" | head -n 1 | read -r manifest_pub || true
  fi
  if [ -z "$manifest_cargo" ]; then
    find "$repo_path" -maxdepth 2 -name "Cargo.toml" | head -n 1 | read -r manifest_cargo || true
  fi
  if [ -z "$manifest_pkg" ]; then
    find "$repo_path" -maxdepth 2 -name "package.json" | head -n 1 | read -r manifest_pkg || true
  fi

  if [ -n "$manifest_pub" ]; then
    (cd "$(dirname "$manifest_pub")" && install_flutter) || rc=$?
  elif [ -n "$manifest_cargo" ]; then
    (cd "$(dirname "$manifest_cargo")" && install_rust) || rc=$?
  elif [ -n "$manifest_pkg" ]; then
    (cd "$(dirname "$manifest_pkg")" && install_node) || rc=$?
  elif [ -n "$manifest_py" ]; then
    (cd "$(dirname "$manifest_py")" && install_python) || rc=$?
  else
    log_info "Unknown project type. Skipping."
  fi

  if [ "$SKIP_DEPS" = "0" ] && [ "$rc" -ne 0 ]; then
    log_err "Dependency install may have failed for $repo_name."
    failures+=("$repo_name")
  fi
done < <(find "$REPO_ROOT" -maxdepth 1 -mindepth 1 -type d | grep -v "\.git" | sort)

if [ "$SKIP_DEPS" = "0" ] && [ "${#failures[@]}" -gt 0 ]; then
  printf "\n${RED}Install issues for: %s${RESET}\n" "${failures[*]}"
  exit 1
fi
