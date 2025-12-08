#!/bin/bash
# tv7-core/tooling/setup-secrets.sh
# Interactive wrapper to set up .env files and configure secrets across repos.
# Behavior:
# - Copies .env.example to .env if missing (never overwrites existing .env).
# - Prompts can be added later; current mode is “copy defaults.”
# Usage: ./setup-secrets.sh [--defaults]
# Requires: standard shell utils; run from tv7-core or with REPO_ROOT set.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR/../..}"
USE_DEFAULTS=0

RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; MAGENTA='\033[35m'; BOLD='\033[1m'; RESET='\033[0m'
log_info(){ printf " ${BLUE}ℹ %s${RESET}\n" "$1"; }
log_ok()  { printf " ${GREEN}✓ %s${RESET}\n" "$1"; }
log_warn(){ printf " ${YELLOW}! %s${RESET}\n" "$1"; }

usage() {
  echo "Usage: ./setup_secrets.sh [--defaults]"
  echo "  --defaults   Skip prompts and use default/example values where possible."
}

if [ "${1:-}" == "--defaults" ]; then
  USE_DEFAULTS=1
  log_info "Running in non-interactive mode (using defaults)."
elif [ "${1:-}" == "--help" ]; then
  usage
  exit 0
fi

# 1. Ensure tv7-core secrets (if any needed globally)
# (Currently core mainly manages workflows, but we can verify DEEPSEEK_API_KEY if we want)

# 2. Iterate repos looking for .env.example
find "$REPO_ROOT" -maxdepth 2 -name ".env.example" | while read -r example_file; do
  repo_dir="$(dirname "$example_file")"
  repo_name="$(basename "$repo_dir")"
  env_file="$repo_dir/.env"

  printf "\n${BOLD}Configuring secrets for ${MAGENTA}%s${RESET}...\n" "$repo_name"

  if [ -f "$env_file" ]; then
    log_warn ".env already exists; leaving it unchanged."
  else
    cp "$example_file" "$env_file"
    log_ok "Created .env from .env.example"
  fi

  # Basic parser to find keys with empty or placeholder values could go here.
  # For now, we'll implement specific prompts for known critical keys.

  # Example: DEEPSEEK_API_KEY for everyone (if used locally)
  # Example: SUPABASE_URL for backend
done

# TODO: Add specific prompts for critical secrets if not present in env
