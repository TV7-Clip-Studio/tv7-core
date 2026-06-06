#!/bin/bash
# tv7-core/tooling/pull-all.sh
# Pull all TV7 repositories with safety flags and readable output.
#
# Usage:
#   ./pull_all.sh [--repos "tv7-core tv7-engine"] [--repos-file path] [--no-color] [--dry-run] [--help]
# Env vars:
#   REPO_ROOT   : base directory containing repos (default: ..)
#   REPOS       : space-separated repos to pull (fallback if no --repos/--repos-file)
# Exit codes:
#   0 on success; non-zero if any pull fails.

set -euo pipefail

# Defaults
REPO_ROOT="${REPO_ROOT:-..}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
DEFAULT_REPOS="tv7-core tv7-engine tv7-backend tv7-studio tv7-site"
REPOS="${REPOS:-$DEFAULT_REPOS}"
REPOS_FILE=""
USE_COLOR=1
DRY_RUN=0

usage() {
  cat <<'EOF'
Pull all TV7 repositories.
Options:
  --repos "r1 r2"     Space-separated repo list (overrides env/default)
  --repos-file FILE   File with repo names (one per line, # comments allowed)
  --no-color          Disable ANSI colors
  --dry-run           Show what would be pulled without executing
  -h, --help          Show this help
Env:
  REPO_ROOT           Base directory containing repos (default: ..)
  REPOS               Space-separated repo list (fallback)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repos) REPOS="$2"; shift 2 ;;
    --repos-file) REPOS_FILE="$2"; shift 2 ;;
    --no-color) USE_COLOR=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

# Colors
if [ "$USE_COLOR" -eq 1 ] && [ -t 1 ] && [ "${TERM:-}" != "dumb" ] && [ "${NO_COLOR:-0}" = "0" ]; then
  RED='\033[31m'; GREEN='\033[32m'; YELLOW='\033[33m'; BLUE='\033[34m'; MAGENTA='\033[35m'; CYAN='\033[36m'; RESET='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'
else
  RED=''; GREEN=''; YELLOW=''; BLUE=''; MAGENTA=''; CYAN=''; RESET=''; BOLD=''; DIM=''
fi

# Helpers
log_header() { printf "${BOLD}${MAGENTA}== %s ==${RESET}\n" "$1"; }
log_info()   { printf "   ${BLUE}ℹ %s${RESET}\n" "$1"; }
log_success(){ printf "   ${GREEN}✓ %s${RESET}\n" "$1"; }
log_warn()   { printf "   ${YELLOW}! %s${RESET}\n" "$1"; }
log_err()    { printf "   ${RED}✗ %s${RESET}\n" "$1"; }

load_repos() {
  if [ -n "$REPOS_FILE" ] && [ -f "$REPOS_FILE" ]; then
    grep -Ev '^\s*(#|$)' "$REPOS_FILE"
  else
    echo "$REPOS"
  fi
}

load_repos | while read -r repo; do
  [ -z "$repo" ] && continue
  path="$REPO_ROOT/$repo"

  if [ ! -d "$path/.git" ]; then
    log_err "$repo missing at $path"
    continue
  fi

  branch=$(git -C "$path" rev-parse --abbrev-ref HEAD)
  printf "${CYAN}%-25s${RESET} ${DIM}(${branch})${RESET} " "$repo"

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "${YELLOW}dry-run${RESET}"
    continue
  fi

  if git -C "$path" rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
    if output=$(git -C "$path" pull --ff-only 2>&1); then
      if [[ "$output" == *"Already up to date."* ]]; then
        echo -e "${GREEN}Already up to date.${RESET}"
      else
        echo -e "${GREEN}Updated.${RESET}"
        echo "$output" | sed 's/^/   /g'
      fi
    else
      echo -e "${RED}Failed.${RESET}"
      echo "$output" | sed 's/^/   /g'
    fi

  elif git -C "$path" ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
    git -C "$path" branch --set-upstream-to="origin/$branch" "$branch" >/dev/null 2>&1
    if output=$(git -C "$path" pull --ff-only 2>&1); then
      echo -e "${GREEN}Upstream set & Updated.${RESET}"
    else
      echo -e "${RED}Upstream set, but Pull Failed.${RESET}"
      echo "$output" | sed 's/^/   /g'
    fi

  else
    echo -e "${YELLOW}Skipped (no upstream)${RESET}"
  fi
done
