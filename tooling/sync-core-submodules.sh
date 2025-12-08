#!/bin/bash
# tv7-core/tooling/sync-core-submodules.sh
# Syncs the tv7-core submodule in sibling repositories to the current HEAD of tv7-core.

set -e

# --- Configuration ---
REPO_ROOT="${REPO_ROOT:-..}"
REPO_ROOT=$(cd "$REPO_ROOT" && pwd)
# Default repos (can be overridden by env var)
REPOS="${REPOS:-tv7-axum-engine tv7-fastapi-backend tv7-flutter-studio tv7-astro-site}"
SUBMODULE_PATH="${SUBMODULE_PATH:-00-tv7-core}"

# --- Inputs ---
MODE="${MODE:-sync}" # sync | bump
AUTO_PUSH="${AUTO_PUSH:-0}"
AUTO_PR="${AUTO_PR:-0}"
COMMIT_TO_MAIN="${COMMIT_TO_MAIN:-0}"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# --- Helpers ---
log_info() { echo -e "${BLUE}[INFO]${RESET} $1"; }
log_success() { echo -e "${GREEN}[OK]${RESET} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${RESET} $1"; }
log_err() { echo -e "${RED}[ERR]${RESET} $1"; }

# --- Main Logic ---

# 1. Get current tv7-core HEAD
CORE_SHA=$(git rev-parse HEAD)
CORE_SHORT_SHA=$(git rev-parse --short HEAD)
log_info "Current tv7-core HEAD: ${CORE_SHORT_SHA}"

for repo in $REPOS; do
    repo_path="$REPO_ROOT/$repo"
    echo ""
    log_info "Checking ${repo}..."

    # Safety Check 1: Repo exists
    if [ ! -d "$repo_path/.git" ]; then
        log_warn "Repository not found at $repo_path. Skipping."
        continue
    fi

    # Safety Check 2: Branch is main (unless we don't care, but usually we want to start from main)
    current_branch=$(git -C "$repo_path" rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "main" ]; then
        log_warn "Repo is on branch '${current_branch}', not 'main'. Skipping to avoid conflicts."
        continue
    fi

    # Safety Check 3: Clean working tree
    if [ -n "$(git -C "$repo_path" status --porcelain)" ]; then
        log_warn "Repo has uncommitted changes. Skipping."
        continue
    fi

    # Check if update is needed
    # Get submodule SHA
    sub_sha=$(git -C "$repo_path" ls-tree HEAD "$SUBMODULE_PATH" | awk '{print $3}' || echo "")
    
    if [ -z "$sub_sha" ]; then
         log_warn "Submodule path '$SUBMODULE_PATH' not found in $repo. Skipping."
         continue
    fi

    if [ "$sub_sha" == "$CORE_SHA" ]; then
        log_success "Already up to date."
        continue
    fi

    log_info "Updating submodule from ${sub_sha:0:7} to ${CORE_SHORT_SHA}..."
    
    # Perform Update
    # We use git update-index to be precise, or just cd and checkout.
    # Safest is to cd into submodule and checkout the sha.
    (
        cd "$repo_path/$SUBMODULE_PATH"
        git fetch origin
        git checkout "$CORE_SHA"
    )

    if [ "$MODE" == "sync" ]; then
        log_success "Updated locally. No commit made."
        continue
    fi

    if [ "$MODE" == "bump" ]; then
        branch_name="chore/bump-tv7-core-${CORE_SHORT_SHA}"
        commit_msg="chore: bump tv7-core to ${CORE_SHORT_SHA}"

        if [ "$COMMIT_TO_MAIN" == "1" ]; then
            log_info "Committing directly to main..."
            git -C "$repo_path" add "$SUBMODULE_PATH"
            git -C "$repo_path" commit -m "$commit_msg"
            log_success "Committed to main."
        else
            log_info "Creating branch $branch_name..."
            # Check if branch exists
            if git -C "$repo_path" rev-parse --verify "$branch_name" >/dev/null 2>&1; then
                log_warn "Branch $branch_name already exists. Switching to it."
                git -C "$repo_path" checkout "$branch_name"
            else
                git -C "$repo_path" checkout -b "$branch_name"
            fi
            
            git -C "$repo_path" add "$SUBMODULE_PATH"
            git -C "$repo_path" commit -m "$commit_msg"
            log_success "Committed to $branch_name."
        fi

        if [ "$AUTO_PUSH" == "1" ] || [ "$AUTO_PR" == "1" ]; then
            target_branch="$current_branch"
            if [ "$COMMIT_TO_MAIN" != "1" ]; then
                 target_branch="$branch_name"
            fi
            
            log_info "Pushing $target_branch..."
            git -C "$repo_path" push origin "$target_branch"
            
            if [ "$AUTO_PR" == "1" ] && [ "$COMMIT_TO_MAIN" != "1" ]; then
                log_info "Creating PR..."
                # Check if PR exists
                pr_exists=$(git -C "$repo_path" ls-remote origin "refs/pull/*/head" | grep "$target_branch" || true)
                
                if command -v gh >/dev/null 2>&1; then
                     # We need to run gh from the repo dir
                     (
                         cd "$repo_path"
                         gh pr create --title "$commit_msg" --body "Automated update of tv7-core submodule to ${CORE_SHORT_SHA}." --base main --head "$target_branch" || log_warn "PR creation failed (maybe already exists?)"
                     )
                else
                    log_warn "gh CLI not found. Skipping PR creation."
                fi
            fi
        fi
        
        # Switch back to main if we created a branch
        if [ "$COMMIT_TO_MAIN" != "1" ]; then
            git -C "$repo_path" checkout main
        fi
    fi

done
