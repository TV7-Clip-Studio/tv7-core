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

json="$(
  gh pr list \
    --repo "$OWNER/$REPO" \
    --head "$BRANCH" \
    --state open \
    --limit 1 \
    --json number,url,state \
    2>/dev/null || true
)"

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
    print(f"PR: #{number} {state} {url}", end="")
' <<<"$json"
else:
  # Fallback: simple grep/cut/tr parser for basic JSON fields when Python is missing
  number="$(echo "$json" | grep -o '"number":[0-9]*' | head -n1 | cut -d: -f2)"
  state="$(echo "$json" | grep -o '"state":"[^"]*"' | head -n1 | cut -d: -f2 | tr -d '"' | tr '[:lower:]' '[:upper:]')"
  url="$(echo "$json" | grep -o '"url":"[^"]*"' | head -n1 | cut -d: -f2- | tr -d '"')"
  if [[ -n "$number" ]]; then
    printf "PR: #%s %s %s" "$number" "$state" "$url"
  else
    printf "PR: none"
  fi
fi
