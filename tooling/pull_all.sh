#!/bin/bash
# tv7-core/tooling/pull_all.sh
# Improved pull-all command for TV7 repositories

set -e

# Colors
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
MAGENTA='\033[35m'
CYAN='\033[36m'
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# Helpers
log_header() { printf "${BOLD}${MAGENTA}== %s ==${RESET}\n" "$1"; }
log_info()   { printf "   ${BLUE}ℹ %s${RESET}\n" "$1"; }
log_success() { printf "   ${GREEN}✓ %s${RESET}\n" "$1"; }
log_warn()   { printf "   ${YELLOW}! %s${RESET}\n" "$1"; }
log_err()    { printf "   ${RED}✗ %s${RESET}\n" "$1"; }

# Configuration
REPO_ROOT="${REPO_ROOT:-..}"
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)
REPOS="${REPOS:-tv7-core tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site}"

for repo in $REPOS; do
    path="$REPO_ROOT/$repo"
    
    # Header for the repo
    # echo ""
    # log_header "Pulling $repo"

    if [ ! -d "$path/.git" ]; then
        log_err "$repo missing at $path"
        continue
    fi

    branch=$(git -C "$path" rev-parse --abbrev-ref HEAD)
    
    # 1. Check upstream
    if git -C "$path" rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
        # Upstream exists
        printf "${CYAN}%-25s${RESET} ${DIM}(${branch})${RESET} " "$repo"
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
        # No upstream, but remote branch exists -> Set upstream and pull
        printf "${CYAN}%-25s${RESET} ${DIM}(${branch})${RESET} " "$repo"
        git -C "$path" branch --set-upstream-to="origin/$branch" "$branch" >/dev/null 2>&1
        
        if output=$(git -C "$path" pull --ff-only 2>&1); then
             echo -e "${GREEN}Upstream set & Updated.${RESET}"
        else
             echo -e "${RED}Upstream set, but Pull Failed.${RESET}"
             echo "$output" | sed 's/^/   /g'
        fi

    else
        # No remote branch
        printf "${CYAN}%-25s${RESET} ${DIM}(${branch})${RESET} ${YELLOW}Skipped (no upstream)${RESET}\n" "$repo"
    fi
done
