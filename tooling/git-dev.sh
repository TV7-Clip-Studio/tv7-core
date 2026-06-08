#!/usr/bin/env bash
# git-dev.sh - Git development assistant using local Qwen3:32b
set -euo pipefail

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
RESET='\033[0m'

TOOLING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TOOLING_DIR/../.." && pwd)"
OWNER="${OWNER:-TV7-Clip-Studio}"
SYNC_BASE="${SYNC_BASE:-origin/main}"
REPOS=("tv7-core" "tv7-conductor" "tv7-engine" "tv7-backend" "tv7-studio" "tv7-site")

# Print headers
echo -e "${CYAN}=== TV7 Git Developer Assistant ===${RESET}"

check_and_resolve_conflicts() {
  if git diff --name-only --diff-filter=U | grep -q .; then
    echo -e "${RED}\nMerge conflicts detected in the following files:${RESET}"
    git diff --name-only --diff-filter=U
    echo -ne "\nWould you like to invoke Conductor CLI to automatically resolve these conflicts? [Y/n]: "
    read -r resolve_choice
    resolve_choice="${resolve_choice:-y}"
    if [[ "$resolve_choice" =~ ^[Yy]$ ]]; then
      echo -e "${CYAN}Launching Conductor conflict resolver...${RESET}"
      python3 "$REPO_ROOT/tv7-conductor/tooling/conductor.py" resolve-conflicts --repo "$SELECTED_REPO"
    else
      echo -e "${YELLOW}Skipping automatic resolution. Please resolve conflicts manually.${RESET}"
    fi
  fi
}

select_repo() {
  echo -e "\nScanning repositories for status..."
  local count=1
  for r in "${REPOS[@]}"; do
    local path="$REPO_ROOT/$r"
    if [ ! -d "$path/.git" ]; then
      echo -e "${RED}[X] $r - missing${RESET}"
      continue
    fi
    local branch
    branch="$(git -C "$path" rev-parse --abbrev-ref HEAD)"
    local changes
    changes="$(git -C "$path" status --porcelain | wc -l | tr -d ' ')"
    local pr_note
    pr_note="$(OWNER="$OWNER" bash "$TOOLING_DIR/pr-info.sh" "$r" "$branch" 2>/dev/null || true)"
    
    local status_line=""
    if [ "$changes" -gt 0 ]; then
      status_line="${YELLOW}$changes pending${RESET}"
    else
      status_line="clean"
    fi
    
    if [ -n "$pr_note" ]; then
      status_line="$status_line, $pr_note"
    fi
    
    echo -e "  ${GREEN}$count)${RESET} ${CYAN}$r${RESET} ($branch) [$status_line]"
    count=$((count+1))
  done
  
  echo -ne "\nSelect repository to manage (1-$((count-1))) or press Enter to exit: "
  read -r choice
  if [ -z "$choice" ] || ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -ge "$count" ]; then
    echo "Exiting."
    exit 0
  fi
  
  SELECTED_REPO="${REPOS[$((choice-1))]}"
  SELECTED_PATH="$REPO_ROOT/$SELECTED_REPO"
}

select_repo

echo -e "\nManaging ${CYAN}$SELECTED_REPO${RESET}..."
cd "$SELECTED_PATH"
check_and_resolve_conflicts

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
# Check PR info
PR_INFO="$(OWNER="$OWNER" bash "$TOOLING_DIR/pr-info.sh" "$SELECTED_REPO" "$CURRENT_BRANCH" 2>/dev/null || true)"

# Check if merged
IS_MERGED=0
if [[ "$PR_INFO" == *"MERGED"* ]]; then
  IS_MERGED=1
fi

if [ "$IS_MERGED" -eq 1 ]; then
  echo -e "${YELLOW}Warning: The PR for your current branch ($CURRENT_BRANCH) has already been merged!${RESET}"
  echo -ne "Sync with origin/main and start a new branch? [Y/n]: "
  read -r sync_choice
  sync_choice="${sync_choice:-y}"
  if [[ "$sync_choice" =~ ^[Yy]$ ]]; then
    # Check for uncommitted changes
    changes="$(git status --porcelain | wc -l | tr -d ' ')"
    stashed=0
    if [ "$changes" -gt 0 ]; then
      echo -e "${YELLOW}Autostashing $changes uncommitted changes...${RESET}"
      git stash
      stashed=1
    fi
    
    echo "Switching to main and pulling..."
    git checkout main
    git pull origin main
    
    # Try to scan active ticket from roadmap
    ROADMAP_PATH="$REPO_ROOT/tv7-core/docs/roadmaps/roadmap.md"
    ROADMAP_CONTEXT="No active ticket context found"
    if [ -f "$ROADMAP_PATH" ]; then
      ROADMAP_CONTEXT="$(grep -B 1 -A 2 -i "IN-PROGRESS" "$ROADMAP_PATH" | head -n 10 || true)"
    fi
    
    echo -e "\nQuerying Gemini via Conductor for branch name suggestions..."
    LLM_SUGGESTIONS="$(python3 "$REPO_ROOT/tv7-conductor/tooling/conductor.py" suggest-branch --repo "$SELECTED_REPO" --context "$ROADMAP_CONTEXT" 2>/dev/null || true)"
    
    if [ -z "$LLM_SUGGESTIONS" ]; then
      echo -e "${RED}Failed to get LLM suggestions. Please verify your Gemini CLI setup.${RESET}"
      LLM_SUGGESTIONS=""
    fi
    
    echo -e "\nSuggested branch names:"
    declare -a SUGGESTED_BRANCHES
    idx=1
    if [ -n "$LLM_SUGGESTIONS" ]; then
      while IFS= read -r line; do
        if [ -n "$line" ]; then
          SUGGESTED_BRANCHES+=("$line")
          echo -e "  ${GREEN}$idx)${RESET} $line"
          idx=$((idx+1))
        fi
      done <<< "$LLM_SUGGESTIONS"
    fi
    echo -e "  ${GREEN}$idx)${RESET} Enter custom branch name"
    
    echo -ne "\nSelect branch option (1-$idx): "
    read -r branch_option
    branch_option="${branch_option:-$idx}"
    
    NEW_BRANCH=""
    if [ "$branch_option" -ge 1 ] && [ "$branch_option" -lt "$idx" ]; then
      NEW_BRANCH="${SUGGESTED_BRANCHES[$((branch_option-1))]}"
    else
      echo -ne "Enter custom branch name: "
      read -r NEW_BRANCH
    fi
    
    if [ -n "$NEW_BRANCH" ]; then
      echo "Creating and checking out branch $NEW_BRANCH..."
      git checkout -b "$NEW_BRANCH"
      CURRENT_BRANCH="$NEW_BRANCH"
    else
      echo "No branch name provided; staying on main."
    fi
    
    if [ "$stashed" -eq 1 ]; then
      echo "Popping stashed changes..."
      git stash pop || true
      check_and_resolve_conflicts
    fi
  fi
fi

# Now check for uncommitted changes and prompt for commit
changes="$(git status --porcelain | wc -l | tr -d ' ')"
if [ "$changes" -gt 0 ]; then
  echo -e "\nYou have ${YELLOW}$changes pending changes${RESET} in this branch ($CURRENT_BRANCH)."
  
  echo "Generating summary of changes from Gemini via Conductor..."
  python3 "$REPO_ROOT/tv7-conductor/tooling/conductor.py" describe-changes --repo "$SELECTED_REPO" 2>/dev/null || echo -e "${RED}Failed to generate change summary.${RESET}"
  echo ""
  
  echo -ne "Would you like to create a new branch? [y/N]: "
  read -r branch_choice
  branch_choice="${branch_choice:-n}"
  if [[ "$branch_choice" =~ ^[Yy]$ ]]; then
    # Try to scan active ticket from roadmap
    ROADMAP_PATH="$REPO_ROOT/tv7-core/docs/roadmaps/roadmap.md"
    ROADMAP_CONTEXT="No active ticket context found"
    if [ -f "$ROADMAP_PATH" ]; then
      ROADMAP_CONTEXT="$(grep -B 1 -A 2 -i "IN-PROGRESS" "$ROADMAP_PATH" | head -n 10 || true)"
    fi
    
    echo -e "\nQuerying Gemini via Conductor for branch name suggestions..."
    LLM_SUGGESTIONS="$(python3 "$REPO_ROOT/tv7-conductor/tooling/conductor.py" suggest-branch --repo "$SELECTED_REPO" --context "$ROADMAP_CONTEXT" 2>/dev/null || true)"
    
    if [ -z "$LLM_SUGGESTIONS" ]; then
      echo -e "${RED}Failed to get LLM suggestions. Please verify your Gemini CLI setup.${RESET}"
      LLM_SUGGESTIONS=""
    fi
    
    echo -e "\nSuggested branch names:"
    declare -a SUGGESTED_BRANCHES
    idx=1
    if [ -n "$LLM_SUGGESTIONS" ]; then
      while IFS= read -r line; do
        if [ -n "$line" ]; then
          SUGGESTED_BRANCHES+=("$line")
          echo -e "  ${GREEN}$idx)${RESET} $line"
          idx=$((idx+1))
        fi
      done <<< "$LLM_SUGGESTIONS"
    fi
    echo -e "  ${GREEN}$idx)${RESET} Enter custom branch name"
    
    echo -ne "\nSelect branch option (1-$idx): "
    read -r branch_option
    branch_option="${branch_option:-$idx}"
    
    NEW_BRANCH=""
    if [ "$branch_option" -ge 1 ] && [ "$branch_option" -lt "$idx" ]; then
      NEW_BRANCH="${SUGGESTED_BRANCHES[$((branch_option-1))]}"
    else
      echo -ne "Enter custom branch name: "
      read -r NEW_BRANCH
    fi
    
    if [ -n "$NEW_BRANCH" ]; then
      echo "Creating and checking out branch $NEW_BRANCH..."
      git checkout -b "$NEW_BRANCH"
      CURRENT_BRANCH="$NEW_BRANCH"
    fi
  fi

  echo -ne "Would you like to commit and push? [Y/n]: "
  read -r commit_choice
  commit_choice="${commit_choice:-y}"
  if [[ "$commit_choice" =~ ^[Yy]$ ]]; then
    # Generate diff
    DIFF_CONTENT="$(git diff HEAD)"
    if [ -z "$DIFF_CONTENT" ]; then
      # If nothing tracked/changed in diff, check untracked
      DIFF_CONTENT="$(git status)"
    fi
    
    echo "Generating commit message suggestion from Gemini via Conductor..."
    SUGGESTED_MSG="$(python3 "$REPO_ROOT/tv7-conductor/tooling/conductor.py" suggest-commit --repo "$SELECTED_REPO" 2>/dev/null || true)"
    
    if [ -z "$SUGGESTED_MSG" ]; then
      echo -e "${RED}Failed to generate commit message suggestions. Please verify your Gemini CLI setup.${RESET}"
      SUGGESTED_MSG="update"
    fi
    
    FULL_COMMIT_MSG="$CURRENT_BRANCH: $SUGGESTED_MSG"
    
    echo -e "\nSuggested commit message:"
    echo -e "  ${CYAN}$FULL_COMMIT_MSG${RESET}"
    echo -ne "\nAccept this message, Edit it, or Cancel? [Y/e/c]: "
    read -r msg_action
    msg_action="${msg_action:-y}"
    
    if [[ "$msg_action" =~ ^[Yy]$ ]]; then
      git add -A
      git commit -m "$FULL_COMMIT_MSG"
      echo -ne "Commit created. Push changes to remote? [Y/n]: "
      read -r push_choice
      push_choice="${push_choice:-y}"
      if [[ "$push_choice" =~ ^[Yy]$ ]]; then
        echo "Pushing changes..."
        TV7_ALLOW_PUSH=1 git push -u origin "$CURRENT_BRANCH"
      fi
    elif [[ "$msg_action" =~ ^[Ee]$ ]]; then
      echo -ne "Enter custom commit message body (branch name prefix will be added): "
      read -r custom_msg
      FULL_COMMIT_MSG="$CURRENT_BRANCH: $custom_msg"
      git add -A
      git commit -m "$FULL_COMMIT_MSG"
      echo -ne "Commit created. Push changes to remote? [Y/n]: "
      read -r push_choice
      push_choice="${push_choice:-y}"
      if [[ "$push_choice" =~ ^[Yy]$ ]]; then
        echo "Pushing changes..."
        TV7_ALLOW_PUSH=1 git push -u origin "$CURRENT_BRANCH"
      fi
    else
      echo "Commit cancelled."
    fi
  fi
else
  # Check for unpushed commits
  ahead="$(git rev-list --count "@{u}..HEAD" 2>/dev/null || echo 0)"
  if [ "$ahead" -gt 0 ]; then
    echo -e "\nYou have ${CYAN}$ahead ahead commits${RESET} not pushed to remote."
    echo -ne "Would you like to push these commits? [Y/n]: "
    read -r push_choice
    push_choice="${push_choice:-y}"
    if [[ "$push_choice" =~ ^[Yy]$ ]]; then
      echo "Pushing changes..."
      TV7_ALLOW_PUSH=1 git push
    fi
  else
    echo -e "\n${GREEN}Repository is clean and up-to-date.${RESET}"
  fi
fi
