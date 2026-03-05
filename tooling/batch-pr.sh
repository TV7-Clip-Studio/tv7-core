#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-..}"
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
CONFIG_FILE="${CONFIG_FILE:-$SCRIPT_DIR/repos-checks.conf}"
BRANCH_PREFIX="${BRANCH_PREFIX:-codex/batch}"
BATCH_ID="${BATCH_ID:-$(date +%Y%m%d-%H%M%S)}"
DEFAULT_COMMIT_MESSAGE="chore: batch update ${BATCH_ID}"
COMMIT_MESSAGE="${COMMIT_MESSAGE:-$DEFAULT_COMMIT_MESSAGE}"
OPEN_PR="${OPEN_PR:-1}"
PUSH_BRANCH="${PUSH_BRANCH:-1}"
DRY_RUN="${DRY_RUN:-0}"
RUN_CHECKS_IN_ALL_REPOS="${RUN_CHECKS_IN_ALL_REPOS:-1}"
TASK_ID="${TASK_ID:-}"
CHANGE_TITLE="${CHANGE_TITLE:-}"
PR_TITLE="${PR_TITLE:-}"
PR_BODY="${PR_BODY:-}"
PR_BODY_FILE="${PR_BODY_FILE:-}"

declare -a REPO_ORDER=()
declare -A BASE_BRANCH
declare -A CHECK_CMD
declare -A DOCS_ONLY_ALLOWED
declare -A RESULT
declare -A NOTE
declare -A CHECK_STATE
declare -A BRANCH_STATE
declare -A COMMIT_STATE
declare -A PUSH_STATE
declare -A PR_STATE

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Missing config file: $CONFIG_FILE" >&2
  exit 1
fi

while IFS='|' read -r repo base check docs_only; do
  [ -z "${repo:-}" ] && continue
  case "$repo" in
    \#*) continue ;;
  esac
  REPO_ORDER+=("$repo")
  BASE_BRANCH["$repo"]="$base"
  CHECK_CMD["$repo"]="$check"
  DOCS_ONLY_ALLOWED["$repo"]="${docs_only:-0}"
done < "$CONFIG_FILE"

run_cmd() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] $*"
    return 0
  fi
  eval "$@"
}

sanitize_ref() {
  printf "%s" "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//'
}

resolve_pr_title() {
  if [ -n "$PR_TITLE" ]; then
    printf "%s" "$PR_TITLE"
    return 0
  fi
  printf "%s" "$COMMIT_MESSAGE" | head -n1
}

resolve_pr_body_file() {
  local repo="$1"
  local out="/tmp/tv7-batch-${repo}-${BATCH_ID}-pr-body.md"

  if [ -n "$PR_BODY_FILE" ]; then
    printf "%s" "$PR_BODY_FILE"
    return 0
  fi

  if [ -n "$PR_BODY" ]; then
    printf "%s\n" "$PR_BODY" > "$out"
    printf "%s" "$out"
    return 0
  fi

  {
    echo "## Summary"
    if [ -n "$CHANGE_TITLE" ]; then
      echo "- ${CHANGE_TITLE}"
    else
      echo "- Automated batch update."
    fi
    if [ -n "$TASK_ID" ]; then
      echo "- Task ID: ${TASK_ID}"
    fi
    echo "- Batch ID: ${BATCH_ID}"
    echo "- Repo: ${repo}"
    echo
    echo "## Validation"
    if [ -n "${CHECK_CMD[$repo]}" ]; then
      echo "- Check command: \`${CHECK_CMD[$repo]}\`"
    else
      echo "- Check command: (none configured)"
    fi
  } > "$out"

  printf "%s" "$out"
}

if [ -n "$TASK_ID" ] || [ -n "$CHANGE_TITLE" ]; then
  if [ -z "$TASK_ID" ] || [ -z "$CHANGE_TITLE" ]; then
    echo "TASK_ID and CHANGE_TITLE must be provided together." >&2
    exit 1
  fi
  task_subject="[${TASK_ID}] ${CHANGE_TITLE}"
  if [ "$COMMIT_MESSAGE" = "$DEFAULT_COMMIT_MESSAGE" ]; then
    COMMIT_MESSAGE="$task_subject"
  fi
  if [ -z "$PR_TITLE" ]; then
    PR_TITLE="$task_subject"
  fi
fi

if [ -n "$PR_BODY" ] && [ -n "$PR_BODY_FILE" ]; then
  echo "Set either PR_BODY or PR_BODY_FILE, not both." >&2
  exit 1
fi

if [ -n "$PR_BODY_FILE" ] && [ ! -f "$PR_BODY_FILE" ]; then
  echo "PR_BODY_FILE does not exist: $PR_BODY_FILE" >&2
  exit 1
fi

has_docs_only_changes() {
  local repo_path="$1"
  local changes
  changes="$(git -C "$repo_path" diff --name-only --cached && git -C "$repo_path" diff --name-only)"
  if [ -z "${changes// /}" ]; then
    return 1
  fi
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    case "$p" in
      *.md|docs/*|.agent/*) ;;
      *) return 1 ;;
    esac
  done <<< "$changes"
  return 0
}

ensure_branch() {
  local repo="$1"
  local repo_path="$2"
  local branch
  branch="$(git -C "$repo_path" rev-parse --abbrev-ref HEAD)"
  if [ "$branch" = "HEAD" ]; then
    BRANCH_STATE["$repo"]="FAIL"
    NOTE["$repo"]="detached HEAD"
    return 1
  fi
  case "$branch" in
    main|master)
      local branch_suffix="$BATCH_ID"
      if [ -n "$TASK_ID" ]; then
        branch_suffix="$(sanitize_ref "$TASK_ID")"
      fi
      if [ -z "$branch_suffix" ]; then
        branch_suffix="$BATCH_ID"
      fi
      local next_branch="${BRANCH_PREFIX}-${repo}-${branch_suffix}"
      run_cmd "git -C \"$repo_path\" checkout -b \"$next_branch\""
      BRANCH_STATE["$repo"]="CREATED:${next_branch}"
      ;;
    *)
      BRANCH_STATE["$repo"]="EXISTING:${branch}"
      ;;
  esac
  return 0
}

run_checks() {
  local repo="$1"
  local repo_path="$2"
  local cmd="${CHECK_CMD[$repo]}"

  if [ -z "$cmd" ]; then
    CHECK_STATE["$repo"]="SKIP"
    return 0
  fi

  if [ "$RUN_CHECKS_IN_ALL_REPOS" = "0" ]; then
    if [ -z "$(git -C "$repo_path" status --porcelain)" ]; then
      CHECK_STATE["$repo"]="SKIP"
      return 0
    fi
  fi

  if run_cmd "cd \"$repo_path\" && $cmd >/tmp/tv7-batch-${repo}.log 2>&1"; then
    CHECK_STATE["$repo"]="PASS"
    return 0
  fi

  CHECK_STATE["$repo"]="FAIL"
  NOTE["$repo"]="check failed: ${cmd}"
  return 1
}

commit_repo() {
  local repo="$1"
  local repo_path="$2"
  run_cmd "git -C \"$repo_path\" add -A"

  if git -C "$repo_path" diff --cached --quiet; then
    COMMIT_STATE["$repo"]="SKIP"
    return 0
  fi

  if [ "${DOCS_ONLY_ALLOWED[$repo]}" = "1" ] && has_docs_only_changes "$repo_path"; then
    :
  fi

  run_cmd "git -C \"$repo_path\" commit -m \"$COMMIT_MESSAGE\" >/tmp/tv7-batch-${repo}-commit.log 2>&1"
  COMMIT_STATE["$repo"]="DONE"
  return 0
}

push_and_open_pr() {
  local repo="$1"
  local repo_path="$2"
  local base="${BASE_BRANCH[$repo]}"
  local branch
  branch="$(git -C "$repo_path" rev-parse --abbrev-ref HEAD)"

  if [ "${COMMIT_STATE[$repo]:-SKIP}" != "DONE" ]; then
    PUSH_STATE["$repo"]="SKIP"
    PR_STATE["$repo"]="SKIP"
    return 0
  fi

  if [ "$PUSH_BRANCH" = "1" ]; then
    run_cmd "git -C \"$repo_path\" push -u origin \"$branch\" >/tmp/tv7-batch-${repo}-push.log 2>&1"
    if [ "$DRY_RUN" = "1" ]; then
      PUSH_STATE["$repo"]="DRY-RUN"
    else
      PUSH_STATE["$repo"]="DONE"
    fi
  else
    PUSH_STATE["$repo"]="SKIP"
  fi

  if [ "$OPEN_PR" != "1" ]; then
    PR_STATE["$repo"]="SKIP"
    return 0
  fi

  if [ "$DRY_RUN" = "1" ]; then
    PR_STATE["$repo"]="DRY-RUN"
    return 0
  fi

  if ! command -v gh >/dev/null 2>&1; then
    PR_STATE["$repo"]="FAIL"
    NOTE["$repo"]="gh not found"
    return 1
  fi

  if ! gh auth status >/dev/null 2>&1; then
    PR_STATE["$repo"]="FAIL"
    NOTE["$repo"]="gh auth missing"
    return 1
  fi

  local existing_pr_state existing_pr_url
  existing_pr_state="$(
    gh pr view --repo "TV7-Clip-Studio/${repo}" "$branch" --json state,url --jq '.state' 2>/tmp/tv7-batch-${repo}-pr.log || true
  )"
  existing_pr_url="$(
    gh pr view --repo "TV7-Clip-Studio/${repo}" "$branch" --json state,url --jq '.url' 2>/dev/null || true
  )"
  case "$existing_pr_state" in
    OPEN)
      PR_STATE["$repo"]="EXISTS"
      NOTE["$repo"]="open PR already exists: ${existing_pr_url}"
      return 0
      ;;
    MERGED|CLOSED)
      NOTE["$repo"]="previous ${existing_pr_state,,} PR found for branch; creating a new PR for latest commits"
      ;;
    *)
      : # no existing PR for this branch
      ;;
  esac

  local pr_title pr_body_file
  pr_title="$(resolve_pr_title)"
  pr_body_file="$(resolve_pr_body_file "$repo")"

  if cd "$repo_path" && gh pr create --base "$base" --head "$branch" --title "$pr_title" --body-file "$pr_body_file" >/tmp/tv7-batch-${repo}-pr.log 2>&1; then
    PR_STATE["$repo"]="CREATED"
    return 0
  fi

  PR_STATE["$repo"]="FAIL"
  NOTE["$repo"]="pr create failed"
  return 1
}

print_summary() {
  echo
  printf "%-24s %-8s %-12s %-8s %-8s %-8s %s\n" "REPO" "RESULT" "CHECK" "COMMIT" "PUSH" "PR" "NOTE"
  printf "%-24s %-8s %-12s %-8s %-8s %-8s %s\n" "------------------------" "--------" "------------" "--------" "--------" "--------" "-----------------------------"
  for repo in "${REPO_ORDER[@]}"; do
    printf "%-24s %-8s %-12s %-8s %-8s %-8s %s\n" \
      "$repo" \
      "${RESULT[$repo]:-OK}" \
      "${CHECK_STATE[$repo]:-SKIP}" \
      "${COMMIT_STATE[$repo]:-SKIP}" \
      "${PUSH_STATE[$repo]:-SKIP}" \
      "${PR_STATE[$repo]:-SKIP}" \
      "${NOTE[$repo]:-}"
  done
}

overall=0
for repo in "${REPO_ORDER[@]}"; do
  repo_path="$REPO_ROOT/$repo"
  RESULT["$repo"]="OK"
  NOTE["$repo"]=""

  if [ ! -d "$repo_path/.git" ]; then
    RESULT["$repo"]="FAIL"
    NOTE["$repo"]="missing repo at $repo_path"
    CHECK_STATE["$repo"]="SKIP"
    BRANCH_STATE["$repo"]="SKIP"
    COMMIT_STATE["$repo"]="SKIP"
    PUSH_STATE["$repo"]="SKIP"
    PR_STATE["$repo"]="SKIP"
    overall=1
    continue
  fi

  if ! ensure_branch "$repo" "$repo_path"; then
    RESULT["$repo"]="FAIL"
    overall=1
    continue
  fi

  if ! run_checks "$repo" "$repo_path"; then
    RESULT["$repo"]="FAIL"
    COMMIT_STATE["$repo"]="SKIP"
    PUSH_STATE["$repo"]="SKIP"
    PR_STATE["$repo"]="SKIP"
    overall=1
    continue
  fi

  if ! commit_repo "$repo" "$repo_path"; then
    RESULT["$repo"]="FAIL"
    NOTE["$repo"]="commit failed"
    PUSH_STATE["$repo"]="SKIP"
    PR_STATE["$repo"]="SKIP"
    overall=1
    continue
  fi

  if ! push_and_open_pr "$repo" "$repo_path"; then
    RESULT["$repo"]="FAIL"
    overall=1
    continue
  fi
done

print_summary
exit "$overall"
