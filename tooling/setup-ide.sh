#!/bin/bash
# tv7-core/tooling/setup-ide.sh
# Sets up VSCode configuration for all repositories if not present.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR/../..}"
TEMPLATE_DIR="$SCRIPT_DIR/../templates/vscode"

RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; BOLD='\033[1m'; RESET='\033[0m'
log_info(){ printf " ${BLUE}ℹ %s${RESET}\n" "$1"; }
log_ok()  { printf " ${GREEN}✓ %s${RESET}\n" "$1"; }
log_warn(){ printf " ${YELLOW}! %s${RESET}\n" "$1"; }

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "Template directory not found: $TEMPLATE_DIR"
  exit 1
fi

find "$REPO_ROOT" -maxdepth 1 -mindepth 1 -type d | grep -v "\.git" | sort | while read -r repo_path; do
  repo_name="$(basename "$repo_path")"
  # skip core itself (handled recursively? usually we want core to have it too)
  # core is in the list, so it works.
  [ ! -d "$repo_path/.git" ] && continue

  vscode_dir="$repo_path/.vscode"
  
  printf "\n${BOLD}Configuring IDE for ${MAGENTA}%s${RESET}...\n" "$repo_name"

  if [ -d "$vscode_dir" ]; then
    log_info ".vscode directory exists. Skipping to avoid overwriting custom settings."
    continue
  fi

  mkdir -p "$vscode_dir"
  cp "$TEMPLATE_DIR/extensions.json" "$vscode_dir/extensions.json"
  cp "$TEMPLATE_DIR/settings.json" "$vscode_dir/settings.json"
  log_ok "Applied default VSCode configuration."
done

