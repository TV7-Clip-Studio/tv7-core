#!/usr/bin/env python3
"""Commit one human-validated TV7 repository slice without pushing it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from cockpit_common import CORE_DIR, allowed_repos


def run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=str(cwd), text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def commit_title(repo: str) -> str:
    state_path = CORE_DIR / "docs" / ".tmp" / "sync-roadmap-focus.json"
    if state_path.is_file():
        rows = json.loads(state_path.read_text(encoding="utf-8"))
        row = next((item for item in rows if item.get("repo") == repo), {})
        title = str((row.get("test_plan") or {}).get("title") or "validated implementation slice")
    else:
        title = "validated implementation slice"
    return f"{repo}: {title[:1].lower()}{title[1:]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--message")
    args = parser.parse_args()
    if args.repo not in allowed_repos():
        raise SystemExit(f"Unknown repository: {args.repo}")
    repo_path = CORE_DIR.parent / args.repo
    run(["git", "add", "-A"], repo_path)
    message = (args.message or commit_title(args.repo)).strip()
    if not message or "\n" in message or len(message) > 120:
        raise SystemExit("Commit message must be one non-empty line of at most 120 characters.")
    run(["git", "commit", "-m", message], repo_path)
    print("Committed validated slice. No push was performed.")


if __name__ == "__main__":
    main()
