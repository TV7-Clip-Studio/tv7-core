#!/usr/bin/env bash
set -euo pipefail

OWNER="${OWNER:-TV7-Clip-Studio}"
REPO="${1:-}"
BRANCH="${2:-}"

if [[ -z "$REPO" || -z "$BRANCH" || "$BRANCH" == "-" || "$BRANCH" == "HEAD" ]]; then
  exit 0
fi

if ! command -v gh >/dev/null 2>&1; then
  printf "PR: gh missing"
  exit 0
fi

if ! gh auth status >/dev/null 2>&1; then
  printf "PR: gh auth missing"
  exit 0
fi

query_prs_for_state() {
  gh pr list \
    --repo "$OWNER/$REPO" \
    --head "$BRANCH" \
    --state "$1" \
    --limit 1 \
    --json number,url,state
}

gh_supports_state_all() {
  gh pr list --help 2>/dev/null | grep -Eq '(^|[^[:alnum:]_])all([^[:alnum:]_]|$)'
}

json=""
if gh_supports_state_all; then
  json="$(query_prs_for_state all 2>/dev/null || true)"
else
  json="$(query_prs_for_state open 2>/dev/null || true)"
  if [[ -z "$json" || "$json" == "[]" ]]; then
    json="$(query_prs_for_state closed 2>/dev/null || true)"
  fi
fi

if [[ -z "$json" || "$json" == "[]" ]]; then
  printf "PR: none"
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  python3 -c '
import json
import sys

try:
    rows = json.loads(sys.stdin.read())
except Exception:
    rows = []

if not rows:
    print("PR: none", end="")
else:
    pr = rows[0]
    number = pr.get("number", "?")
    state = str(pr.get("state", "OPEN")).upper()
    url = pr.get("url", "")
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    PURPLE = "\033[0;35m"
    RESET = "\033[0m"
    state_colored = state
    if state == "OPEN":
        state_colored = f"{GREEN}OPEN{RESET}"
    elif state == "MERGED":
        state_colored = f"{PURPLE}MERGED{RESET}"
    elif state == "CLOSED":
        state_colored = f"{RED}CLOSED{RESET}"
    print(f"PR: #{number} {state_colored} {url}", end="")
' <<<"$json"
else
  if command -v jq >/dev/null 2>&1; then
    number="$(echo "$json" | jq -r '.[0].number // empty')"
    state="$(echo "$json" | jq -r '.[0].state // "OPEN"' | tr '[:lower:]' '[:upper:]')"
    url="$(echo "$json" | jq -r '.[0].url // empty')"
    if [[ -n "$number" ]]; then
      GREEN=$'\033[0;32m'
      RED=$'\033[0;31m'
      PURPLE=$'\033[0;35m'
      RESET=$'\033[0m'
      state_colored="$state"
      if [[ "$state" == "OPEN" ]]; then
        state_colored="${GREEN}OPEN${RESET}"
      elif [[ "$state" == "MERGED" ]]; then
        state_colored="${PURPLE}MERGED${RESET}"
      elif [[ "$state" == "CLOSED" ]]; then
        state_colored="${RED}CLOSED${RESET}"
      fi
      printf "PR: #%s %s %s" "$number" "$state_colored" "$url"
    else
      printf "PR: none"
    fi
  else
    # Fallback: simple grep/cut/tr parser for basic JSON fields when Python and jq are missing
    number="$(echo "$json" | grep -o '"number":[0-9]*' | head -n1 | cut -d: -f2)"
    state="$(echo "$json" | grep -o '"state":"[^"]*"' | head -n1 | cut -d: -f2 | tr -d '"' | tr '[:lower:]' '[:upper:]')"
    url="$(echo "$json" | grep -o '"url":"[^"]*"' | head -n1 | cut -d: -f2- | tr -d '"')"
    if [[ -n "$number" ]]; then
      GREEN=$'\033[0;32m'
      RED=$'\033[0;31m'
      PURPLE=$'\033[0;35m'
      RESET=$'\033[0m'
      state_colored="$state"
      if [[ "$state" == "OPEN" ]]; then
        state_colored="${GREEN}OPEN${RESET}"
      elif [[ "$state" == "MERGED" ]]; then
        state_colored="${PURPLE}MERGED${RESET}"
      elif [[ "$state" == "CLOSED" ]]; then
        state_colored="${RED}CLOSED${RESET}"
      fi
      printf "PR: #%s %s %s" "$number" "$state_colored" "$url"
    else
      printf "PR: none"
    fi
  fi
fi
