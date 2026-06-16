#!/usr/bin/env bash
# git-dev.sh - Git development assistant using local Qwen3:32b
if [ -z "${BASH_VERSION:-}" ]; then
  printf 'git-dev.sh must be run with bash. Try: bash %s\n' "$0" >&2
  exit 2
fi
if shopt -qo posix 2>/dev/null; then
  printf 'git-dev.sh must be run with bash, not POSIX sh mode. Try: bash %s\n' "$0" >&2
  exit 2
fi

set -euo pipefail

NON_INTERACTIVE="${GIT_DEV_NON_INTERACTIVE:-0}"
for arg in "$@"; do
  case "$arg" in
    --non-interactive)
      NON_INTERACTIVE=1
      ;;
    -h|--help)
      printf 'Usage: %s [--non-interactive]\n' "$0"
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\nUsage: %s [--non-interactive]\n' "$arg" "$0" >&2
      exit 2
      ;;
  esac
done

if [ "$NON_INTERACTIVE" = "1" ] || [ "${CI:-}" = "true" ] || [ "${CI:-}" = "1" ] || ! [ -t 0 ]; then
  printf 'git-dev.sh is an interactive assistant; skipping because no interactive terminal is available.\n' >&2
  exit 0
fi

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
RESET='\033[0m'

TOOLING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TOOLING_DIR/../.." && pwd)"
CONDUCTOR_SCRIPT="$REPO_ROOT/tv7-conductor/tooling/conductor.py"
OWNER="${OWNER:-TV7-Clip-Studio}"
SYNC_BASE="${SYNC_BASE:-origin/main}"
REPOS=("tv7-core" "tv7-conductor" "tv7-engine" "tv7-backend" "tv7-studio" "tv7-site")
CONDUCTOR_MISSING_WARNED=0

# Print headers
echo -e "${CYAN}=== TV7 Git Developer Assistant ===${RESET}"

warn_conductor_missing() {
  if [ "$CONDUCTOR_MISSING_WARNED" -eq 0 ]; then
    echo -e "${YELLOW}Conductor CLI not found at $CONDUCTOR_SCRIPT. Skipping Conductor-powered features.${RESET}" >&2
    CONDUCTOR_MISSING_WARNED=1
  fi
}

conductor_available() {
  [ -f "$CONDUCTOR_SCRIPT" ]
}

run_conductor() {
  if ! conductor_available; then
    warn_conductor_missing
    return 127
  fi

  python3 "$CONDUCTOR_SCRIPT" "$@"
}

capture_optional_conductor() {
  if ! conductor_available; then
    warn_conductor_missing
    return 127
  fi

  python3 "$CONDUCTOR_SCRIPT" "$@" 2>/dev/null
}

get_roadmap_context() {
  local repo="$1"
  local paths=()
  case "$repo" in
    "tv7-core")
      paths=(
        "$REPO_ROOT/tv7-core/docs/roadmaps/tv7-core-roadmap.md"
        "$REPO_ROOT/tv7-core/docs/roadmaps/core/agent-orchestration-roadmap.md"
        "$REPO_ROOT/tv7-core/docs/roadmaps/core/project-conductor-roadmap.md"
        "$REPO_ROOT/tv7-core/docs/roadmaps/roadmap.md"
      )
      ;;
    "tv7-conductor")
      paths=("$REPO_ROOT/tv7-conductor/docs/roadmaps/tv7-conductor-roadmap.md")
      ;;
    "tv7-backend")
      paths=(
        "$REPO_ROOT/tv7-core/docs/roadmaps/tv7-backend-roadmap.md"
        "$REPO_ROOT/tv7-core/docs/roadmaps/tv7-backend-off-roadmap.md"
      )
      ;;
    "tv7-studio")
      paths=("$REPO_ROOT/tv7-core/docs/roadmaps/tv7-studio-roadmap.md")
      ;;
    "tv7-site")
      paths=("$REPO_ROOT/tv7-core/docs/roadmaps/tv7-site-roadmap.md")
      ;;
    "tv7-engine")
      paths=("$REPO_ROOT/tv7-core/docs/roadmaps/tv7-engine-roadmap.md")
      ;;
    *)
      paths=("$REPO_ROOT/tv7-core/docs/roadmaps/roadmap.md")
      ;;
  esac

  local context=""
  for p in "${paths[@]}"; do
    if [ -f "$p" ]; then
      local match
      match="$(grep -B 1 -A 2 -i "IN-PROGRESS" "$p" | head -n 10 || true)"
      if [ -n "$match" ]; then
        context="$match"
        break
      fi
    fi
  done

  if [ -z "$context" ]; then
    for p in "${paths[@]}"; do
      if [ -f "$p" ]; then
        local match
        match="$(grep -B 1 -A 2 -E "\-\s+\[[ pP]\]" "$p" | head -n 10 || true)"
        if [ -n "$match" ]; then
          context="$match"
          break
        fi
      fi
    done
  fi

  if [ -z "$context" ]; then
    echo "No active ticket context found"
  else
    echo "$context"
  fi
}

check_and_resolve_conflicts() {
  if git diff --name-only --diff-filter=U | grep -q .; then
    echo -e "${RED}\nMerge conflicts detected in the following files:${RESET}"
    git diff --name-only --diff-filter=U
    echo -ne "\nWould you like to invoke Conductor CLI to automatically resolve these conflicts? [Y/n]: "
    read -r resolve_choice
    resolve_choice="${resolve_choice:-y}"
    if [[ "$resolve_choice" =~ ^[Yy]$ ]]; then
      echo -e "${CYAN}Launching Conductor conflict resolver...${RESET}"
      if ! run_conductor resolve-conflicts --repo "$SELECTED_REPO"; then
        echo -e "${YELLOW}Conductor conflict resolver did not run. Please resolve conflicts manually.${RESET}"
      fi
    else
      echo -e "${YELLOW}Skipping automatic resolution. Please resolve conflicts manually.${RESET}"
    fi
  fi
}

open_pr_review_flow() {
  echo -ne "\nWould you like to open the gated PR review flow? [Y/n]: "
  read -r review_choice
  review_choice="${review_choice:-y}"
  if [[ "$review_choice" =~ ^[Yy]$ ]]; then
    echo -e "${CYAN}Opening gated PR review flow via Conductor...${RESET}"
    if ! run_conductor resolve-pr-review --repo "$SELECTED_REPO"; then
      echo -e "${YELLOW}Conductor PR review flow did not run. Review findings manually or restore Conductor and retry.${RESET}"
      return 1
    fi
  fi
}

post_push_pr_flow() {
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD)"
  local pr_info
  pr_info="$(OWNER="$OWNER" bash "$TOOLING_DIR/pr-info.sh" "$SELECTED_REPO" "$branch" 2>/dev/null || true)"

  if [[ "$pr_info" == *"OPEN"* ]]; then
    echo -e "${GREEN}Pushed branch. Existing PR found:${RESET} $pr_info"
    open_pr_review_flow
    return $?
  fi

  if [[ "$pr_info" == *"MERGED"* ]]; then
    echo -e "${YELLOW}Pushed branch, but its PR is already merged: $pr_info${RESET}"
    echo -e "${YELLOW}Run make git-dev again to start a fresh branch from origin/main.${RESET}"
    return 0
  fi

  echo -ne "\nNo open PR found for this branch. Create one automatically? [Y/n]: "
  read -r pr_choice
  pr_choice="${pr_choice:-y}"
  if ! [[ "$pr_choice" =~ ^[Yy]$ ]]; then
    return 0
  fi

  echo -e "${CYAN}Creating Pull Request via Conductor...${RESET}"
  if ! run_conductor create-pr --repo "$SELECTED_REPO"; then
    echo -e "${YELLOW}Conductor PR creation did not run. Create the PR manually or restore Conductor and retry.${RESET}"
    return 1
  fi

  open_pr_review_flow
}

apply_stashed_changes() {
  local stash_ref="$1"

  echo "Applying stashed changes..."
  if git stash apply "$stash_ref"; then
    git stash drop "$stash_ref" >/dev/null
    check_and_resolve_conflicts
    return 0
  fi

  echo -e "${RED}Stash apply failed. Your working tree may contain conflicts; the stash was kept at $stash_ref.${RESET}"
  if git diff --name-only --diff-filter=U | grep -q .; then
    check_and_resolve_conflicts
  else
    echo -e "${YELLOW}Review 'git status' and 'git stash list' before continuing.${RESET}"
  fi
  return 1
}

push_current_branch() {
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD)"
  local upstream_ref=""
  upstream_ref="$(git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || true)"

  if [ "$upstream_ref" != "origin/$branch" ]; then
    if [ -n "$upstream_ref" ]; then
      echo -e "${YELLOW}Current upstream is $upstream_ref; pushing to origin/$branch instead.${RESET}"
    fi
    TV7_ALLOW_PUSH=1 git push -u origin "HEAD:$branch"
    return $?
  fi

  TV7_ALLOW_PUSH=1 git push
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

# Menu selection for flow
echo -e "\nWhat would you like to do?"
echo -e "  ${GREEN}1)${RESET} Continue standard development flow (commit, push, create PR)"
echo -e "  ${GREEN}2)${RESET} Review or merge open PRs"
echo -ne "\nSelect option [1-2, default: 1]: "
read -r flow_choice
flow_choice="${flow_choice:-1}"

if [[ "$flow_choice" == "2" ]]; then
  echo -e "\n${CYAN}Fetching open Pull Requests for $SELECTED_REPO...${RESET}"
  prs_raw="$(gh pr list --json number,title,headRefName --jq '.[] | "\(.number) - \(.title) (\(.headRefName))"' 2>/dev/null || true)"

  if [ -z "$prs_raw" ]; then
    echo -e "${YELLOW}No open Pull Requests found for $SELECTED_REPO.${RESET}"
    exit 0
  fi

  echo -e "\nOpen Pull Requests:"
  PR_BRANCHES=()
  PR_NUMBERS=()
  idx=1
  while IFS= read -r line; do
    if [ -n "$line" ]; then
      branch="$(echo "$line" | sed -E 's/.* \((.*)\)/\1/')"
      num="$(echo "$line" | cut -d' ' -f1)"
      PR_BRANCHES+=("$branch")
      PR_NUMBERS+=("$num")
      echo -e "  ${GREEN}$idx)${RESET} #$line"
      idx=$((idx+1))
    fi
  done <<< "$prs_raw"

  echo -ne "\nSelect a PR to resolve (1-$((idx-1))) or press Enter to cancel: "
  read -r pr_choice
  if [ -z "$pr_choice" ] || ! [[ "$pr_choice" =~ ^[0-9]+$ ]] || [ "$pr_choice" -lt 1 ] || [ "$pr_choice" -ge "$idx" ]; then
    echo "Cancelled."
    exit 0
  fi

  TARGET_BRANCH="${PR_BRANCHES[$((pr_choice-1))]}"
  TARGET_PR_NUM="${PR_NUMBERS[$((pr_choice-1))]}"
  echo -e "\nChecking out branch ${CYAN}$TARGET_BRANCH${RESET} for PR #$TARGET_PR_NUM..."
  git checkout "$TARGET_BRANCH"

  echo -e "${CYAN}Opening gated PR review flow...${RESET}"
  if ! run_conductor resolve-pr-review --repo "$SELECTED_REPO"; then
    echo -e "${YELLOW}Conductor PR review flow did not run. Review findings manually or restore Conductor and retry.${RESET}"
  fi
  exit 0
fi

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
    changes="$(git status --porcelain | wc -l | tr -d ' ')"
    stashed=0
    stash_ref=""
    if [ "$changes" -gt 0 ]; then
      echo -e "${YELLOW}Autostashing $changes uncommitted changes...${RESET}"
      stash_msg="git-dev:$SELECTED_REPO:$CURRENT_BRANCH:$(date +%Y%m%d%H%M%S)"
      git stash push -u -m "$stash_msg"
      stashed=1
      stash_ref="stash@{0}"
    fi

    echo "Fetching latest origin/main..."
    git fetch origin main
    if git show-ref --verify --quiet refs/heads/main; then
      if ! git merge-base --is-ancestor main "$SYNC_BASE" && ! git merge-base --is-ancestor "$SYNC_BASE" main; then
        echo -e "${YELLOW}Local main has diverged from $SYNC_BASE; leaving local main untouched and using $SYNC_BASE as the new branch base.${RESET}"
      fi
    fi

    ROADMAP_CONTEXT="$(get_roadmap_context "$SELECTED_REPO")"

    echo -e "\nQuerying Gemini via Conductor for branch name suggestions..."
    LLM_SUGGESTIONS="$(capture_optional_conductor suggest-branch --repo "$SELECTED_REPO" --context "$ROADMAP_CONTEXT" || true)"

    if [ -z "$LLM_SUGGESTIONS" ]; then
      echo -e "${RED}Failed to get LLM suggestions. Please verify your Gemini CLI setup.${RESET}"
      LLM_SUGGESTIONS=""
    fi

    echo -e "\nSuggested branch names:"
    SUGGESTED_BRANCHES=()
    idx=1
    if [ -n "$LLM_SUGGESTIONS" ]; then
      while IFS= read -r line; do
        if [ -n "$line" ] && [[ "$line" != *"[gemini metrics:"* ]]; then
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

    if [ -n "$NEW_BRANCH" ] && ! git check-ref-format --branch "$NEW_BRANCH" >/dev/null 2>&1; then
      echo -e "${RED}Invalid branch name: $NEW_BRANCH${RESET}"
      NEW_BRANCH=""
    fi

    if [ -n "$NEW_BRANCH" ]; then
      if git show-ref --verify --quiet "refs/heads/$NEW_BRANCH"; then
        echo -e "${RED}Branch already exists: $NEW_BRANCH${RESET}"
        if [ "$stashed" -eq 1 ]; then
          echo -e "${YELLOW}Your changes are still saved at $stash_ref.${RESET}"
        fi
        exit 1
      fi
      echo "Creating and checking out branch $NEW_BRANCH from $SYNC_BASE..."
      git checkout -b "$NEW_BRANCH" "$SYNC_BASE"
      CURRENT_BRANCH="$NEW_BRANCH"
    else
      echo -e "${RED}No branch name provided; aborting branch refresh.${RESET}"
      if [ "$stashed" -eq 1 ]; then
        echo -e "${YELLOW}Your changes are still saved at $stash_ref.${RESET}"
      fi
      exit 1
    fi

    if [ "$stashed" -eq 1 ]; then
      apply_stashed_changes "$stash_ref"
    fi
  fi
fi

# Now check for uncommitted changes and prompt for commit
changes="$(git status --porcelain | wc -l | tr -d ' ')"
if [ "$changes" -gt 0 ]; then
  echo -e "\nYou have ${YELLOW}$changes pending changes${RESET} in this branch ($CURRENT_BRANCH)."

  echo "Generating summary of changes from Gemini via Conductor..."
  run_conductor describe-changes --repo "$SELECTED_REPO" || echo -e "${RED}Failed to generate change summary.${RESET}"
  echo ""

  echo -ne "Would you like to create a new branch? [y/N]: "
  read -r branch_choice
  branch_choice="${branch_choice:-n}"
  if [[ "$branch_choice" =~ ^[Yy]$ ]]; then
    ROADMAP_CONTEXT="$(get_roadmap_context "$SELECTED_REPO")"

    echo -e "\nQuerying Gemini via Conductor for branch name suggestions..."
    LLM_SUGGESTIONS="$(capture_optional_conductor suggest-branch --repo "$SELECTED_REPO" --context "$ROADMAP_CONTEXT" || true)"

    if [ -z "$LLM_SUGGESTIONS" ]; then
      echo -e "${RED}Failed to get LLM suggestions. Please verify your Gemini CLI setup.${RESET}"
      LLM_SUGGESTIONS=""
    fi

    echo -e "\nSuggested branch names:"
    SUGGESTED_BRANCHES=()
    idx=1
    if [ -n "$LLM_SUGGESTIONS" ]; then
      while IFS= read -r line; do
        if [ -n "$line" ] && [[ "$line" != *"[gemini metrics:"* ]]; then
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
    SUGGESTED_MSG="$(capture_optional_conductor suggest-commit --repo "$SELECTED_REPO" || true)"

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
        if push_current_branch; then
          post_push_pr_flow
        else
          echo -e "${RED}Push failed. Skipping PR creation.${RESET}"
        fi
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
        if push_current_branch; then
          post_push_pr_flow
        else
          echo -e "${RED}Push failed. Skipping PR creation.${RESET}"
        fi
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
      if push_current_branch; then
        post_push_pr_flow
      else
        echo -e "${RED}Push failed. Skipping PR creation.${RESET}"
      fi
    fi
  else
    echo -e "\n${GREEN}Repository is clean and up-to-date.${RESET}"
  fi
fi
