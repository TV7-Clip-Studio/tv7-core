#!/bin/bash
# tv7-core/tooling/setup-ide.sh
# Sets up VSCode configuration for all repositories if not present.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR/../..}"
TEMPLATE_DIR="$SCRIPT_DIR/../templates/vscode"

RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; MAGENTA='\033[35m'; BOLD='\033[1m'; RESET='\033[0m'
log_info(){ printf " ${BLUE}ℹ %s${RESET}\n" "$1"; }
log_ok()  { printf " ${GREEN}✓ %s${RESET}\n" "$1"; }
log_warn(){ printf " ${YELLOW}! %s${RESET}\n" "$1"; }

usage() {
  echo "Usage: ./setup-ide.sh [--force] [--dry-run]"
  echo "  --force      Overwrite existing .vscode configurations (creates backups)."
  echo "  --dry-run    Preview changes without applying them."
}

FORCE=0
DRY_RUN=0

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --help) usage; exit 0 ;;
    *) echo "Unknown parameter: $1"; usage; exit 1 ;;
  esac
  shift
done

if [ ! -d "$TEMPLATE_DIR" ]; then
  log_warn "Template directory not found: $TEMPLATE_DIR"
  exit 1
fi

# Validate templates contents
validate_json() {
  if command -v jq >/dev/null; then
    if ! jq empty "$1" 2>/dev/null; then return 1; fi
  elif command -v python3 >/dev/null; then
    if ! python3 -m json.tool "$1" >/dev/null 2>&1; then return 1; fi
  else
    log_warn "Neither jq nor python3 found. Skipping JSON validation."
    return 0
  fi
}

for tpl in extensions.json settings.json; do
  if ! validate_json "$TEMPLATE_DIR/$tpl"; then
     log_warn "Template $tpl is invalid JSON. Skipping setup."
     exit 1
  fi
done

safe_copy() {
  local src="$1"
  local dst="$2"

  if [ -f "$dst" ]; then
    if [ "$FORCE" -eq 1 ]; then
      local backup="${dst}.bak.$(date +%s)_$$"
      if [ "$DRY_RUN" -eq 1 ]; then
        log_info "  [DRY-RUN] Would backup $dst to $backup"
        log_info "  [DRY-RUN] Would overwrite $dst"
      else
        cp "$dst" "$backup"
        cp "$src" "$dst" || { log_warn "Failed to copy to $dst"; return 1; }
        log_ok "  Updated $dst (backup created)"
      fi
    else
      if [ "$DRY_RUN" -eq 1 ]; then
        log_info "  [DRY-RUN] Would skip $dst (exists)"
      else
        log_info "  Skipping $dst (exists)"
      fi
    fi
  else
    if [ "$DRY_RUN" -eq 1 ]; then
      log_info "  [DRY-RUN] Would create $dst"
    else
      cp "$src" "$dst" || { log_warn "Failed to copy to $dst"; return 1; }
      log_ok "  Created $dst"
    fi
  fi
}

# Iterate over all subdirectories in REPO_ROOT
find "$REPO_ROOT" -maxdepth 1 -mindepth 1 -type d | sort | while read -r repo_path; do
  repo_name="$(basename "$repo_path")"
  
  # 1. Skip if it's not a git repository
  [ ! -d "$repo_path/.git" ] && continue
  # 2. Skip symlinks explicitly
  [ -L "$repo_path" ] && continue

  vscode_dir="$repo_path/.vscode"
  
  printf "\n${BOLD}Configuring IDE for ${MAGENTA}%s${RESET}...\n" "$repo_name"

  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$vscode_dir" || { log_warn "Failed to create dir $vscode_dir"; continue; }
  fi

  safe_copy "$TEMPLATE_DIR/extensions.json" "$vscode_dir/extensions.json" || continue
  safe_copy "$TEMPLATE_DIR/settings.json" "$vscode_dir/settings.json" || continue
done



