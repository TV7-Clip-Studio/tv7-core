#!/bin/bash
# tv7-core/tooling/status.sh
# Improved status reporting for TV7 repositories

set -e

# Colors and Styles
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# Colors
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
MAGENTA='\033[35m'
CYAN='\033[36m'
WHITE='\033[37m'

# Backgrounds (optional, for badges)
BG_RED='\033[41m'
BG_GREEN='\033[42m'

# Icons
ICON_CHECK="✓"
ICON_X="✗"
ICON_SYNC="ok"
ICON_UP="↑"
ICON_DOWN="↓"
ICON_WARN="!"
ICON_DIRTY="*"

# Configuration
REPO_ROOT="${REPO_ROOT:-..}"
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)
REPOS="${REPOS:-tv7-core tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site}"
SUBMODULE_PATH="${SUBMODULE_PATH:-00-tv7-core}"

# Header
printf "${BOLD}%-25s %-20s %-30s %-20s${RESET}\n" "REPOSITORY" "BRANCH" "SYNC STATUS" "CHANGES"
printf "${DIM}%s${RESET}\n" "----------------------------------------------------------------------------------------------------"

for repo in $REPOS; do
    path="$REPO_ROOT/$repo"
    
    # 1. Check existence
    if [ ! -d "$path/.git" ]; then
        printf "${RED}%-25s ${DIM}%-20s ${RED}%-30s ${DIM}%-20s${RESET}\n" "$repo" "-" "MISSING" "-"
        continue
    fi

    # 2. Get Branch
    branch=$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'detached')
    
    # 3. Get Upstream & Sync Status
    upstream=$(git -C "$path" rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || true)
    sync_str=""
    sync_color="$GREEN"
    
    if [ -n "$upstream" ]; then
        # Count ahead/behind
        counts=$(git -C "$path" rev-list --left-right --count "$upstream...HEAD" 2>/dev/null || echo "0 0")
        behind=$(echo "$counts" | awk '{print $1}')
        ahead=$(echo "$counts" | awk '{print $2}')
        
        if [ "$ahead" -eq 0 ] && [ "$behind" -eq 0 ]; then
            sync_str="${GREEN}${ICON_SYNC}${RESET}"
        else
            if [ "$ahead" -gt 0 ]; then
                sync_str="${sync_str}${BLUE}${ICON_UP}${ahead}${RESET} "
            fi
            if [ "$behind" -gt 0 ]; then
                sync_str="${sync_str}${RED}${ICON_DOWN}${behind}${RESET} "
            fi
        fi
    else
        sync_str="${DIM}no upstream${RESET}"
    fi

    # 4. Check Working Directory (Staged, Unstaged, Untracked)
    staged=$(git -C "$path" diff --cached --name-only | wc -l | tr -d ' ')
    unstaged=$(git -C "$path" diff --name-only | wc -l | tr -d ' ')
    untracked=$(git -C "$path" ls-files --others --exclude-standard | wc -l | tr -d ' ')
    
    changes_str=""
    if [ "$staged" -eq 0 ] && [ "$unstaged" -eq 0 ] && [ "$untracked" -eq 0 ]; then
        changes_str="${DIM}clean${RESET}"
    else
        if [ "$staged" -gt 0 ]; then changes_str="${changes_str}${GREEN}+${staged}${RESET} "; fi
        if [ "$unstaged" -gt 0 ]; then changes_str="${changes_str}${YELLOW}~${unstaged}${RESET} "; fi
        if [ "$untracked" -gt 0 ]; then changes_str="${changes_str}${RED}?${untracked}${RESET} "; fi
    fi

    # 5. Check Submodule (tv7-core)
    # Only check if it's NOT tv7-core itself (avoid recursion confusion, though technically it doesn't have itself as submodule usually)
    # Actually, tv7-core is the parent, other repos have it as submodule.
    # But the list includes tv7-core. tv7-core doesn't have 00-tv7-core submodule.
    
    sub_status=""
    if [ "$repo" != "tv7-core" ]; then
         if [ -d "$path/$SUBMODULE_PATH" ]; then
            subdirty=$(git -C "$path" status --porcelain "$SUBMODULE_PATH" | wc -l | tr -d ' ')
            if [ "$subdirty" -gt 0 ]; then
                sub_status="${RED}(sub: dirty)${RESET}"
            fi
         else
             # Some repos might not have it yet or it's optional? Assuming standard structure.
             # If it's missing but expected, maybe warn. For now, ignore if not found to avoid noise.
             :
         fi
    fi

    # 6. Last Commit Age
    last_commit_time=$(git -C "$path" log -1 --format="%cr" 2>/dev/null || echo "-")
    
    # Repo Name Color
    repo_color="$CYAN"
    if [ "$repo" == "tv7-core" ]; then repo_color="$MAGENTA"; fi

    # Print Row
    # Format: REPO | BRANCH | SYNC | CHANGES | TIME
    printf "${repo_color}%-25s${RESET} ${WHITE}%-20s${RESET} %-40b %-30b ${DIM}%s${RESET}\n" \
        "$repo" \
        "${branch:0:19}" \
        "$sync_str" \
        "$changes_str $sub_status" \
        "$last_commit_time"

done
printf "\n"
