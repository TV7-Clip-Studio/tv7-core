#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-..}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-$SCRIPT_DIR/repos-checks.conf}"

declare -a REPOS=()
while IFS='|' read -r repo _rest; do
  [ -z "${repo:-}" ] && continue
  case "$repo" in
    \#*) continue ;;
  esac
  REPOS+=("$repo")
done < "$CONFIG_FILE"

printf "%-24s %-24s %-12s %-10s %-8s %s\n" "REPO" "BRANCH" "UPSTREAM" "CHANGES" "PR" "NOTE"
printf "%-24s %-24s %-12s %-10s %-8s %s\n" "------------------------" "------------------------" "------------" "----------" "--------" "-----------------------------"

for repo in "${REPOS[@]}"; do
  repo_path="$REPO_ROOT/$repo"
  if [ ! -d "$repo_path/.git" ]; then
    printf "%-24s %-24s %-12s %-10s %-8s %s\n" "$repo" "-" "-" "-" "-" "missing repo"
    continue
  fi

  branch="$(git -C "$repo_path" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "-")"
  upstream="$(git -C "$repo_path" rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || echo "none")"
  staged="$(git -C "$repo_path" diff --cached --name-only | wc -l | tr -d ' ')"
  unstaged="$(git -C "$repo_path" diff --name-only | wc -l | tr -d ' ')"
  untracked="$(git -C "$repo_path" ls-files --others --exclude-standard | wc -l | tr -d ' ')"
  changes="+${staged} ~${unstaged} ?${untracked}"

  pr_state="N/A"
  note=""
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh pr view "$branch" --repo "TV7-Clip-Studio/${repo}" >/tmp/tv7-${repo}-pr-status.log 2>&1; then
      pr_state="OPEN"
    else
      pr_state="NONE"
    fi
  else
    note="gh unavailable/auth missing"
  fi

  printf "%-24s %-24s %-12s %-10s %-8s %s\n" "$repo" "$branch" "$upstream" "$changes" "$pr_state" "$note"
done
