#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OWNER = os.environ.get("OWNER", "TV7-Clip-Studio")
PR_STATE = os.environ.get("STATE", "open")
LIMIT = int(os.environ.get("LIMIT", "100"))
REPO_FILTER = os.environ.get("REPO", "").strip()
REPOS_ENV = os.environ.get("REPOS", "").strip()
OUT_DIR = Path(os.environ.get("OUT_DIR", "docs/code-reviews")).resolve()
CONFIG_FILE = Path(
    os.environ.get("CONFIG_FILE", Path(__file__).resolve().parent / "repos-checks.conf")
).resolve()


def gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh error"
        raise RuntimeError(f"gh {' '.join(args)} failed: {stderr}")
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from gh {' '.join(args)}: {exc}") from exc


def gh_check(args: list[str]) -> None:
    result = subprocess.run(["gh", *args], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh error"
        raise RuntimeError(f"gh {' '.join(args)} failed: {stderr}")


def read_repos() -> list[str]:
    if REPOS_ENV:
        repos = [repo.strip() for repo in REPOS_ENV.split() if repo.strip()]
    elif not CONFIG_FILE.exists():
        raise SystemExit(f"Missing config file: {CONFIG_FILE}")
    else:
        repos = []
        for raw in CONFIG_FILE.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            repo = line.split("|", 1)[0].strip()
            if repo:
                repos.append(repo)

    if REPO_FILTER:
        wanted = {item.strip() for item in REPO_FILTER.split(",") if item.strip()}
        repos = [repo for repo in repos if repo in wanted]

    return repos


def api(path: str) -> Any:
    return gh_json(["api", path])


def check_gh_version() -> None:
    try:
        result = subprocess.run(["gh", "--version"], text=True, capture_output=True, check=False)
        if result.returncode == 0:
            first_line = result.stdout.splitlines()[0]
            parts = first_line.split()
            for part in parts:
                if part and part[0].isdigit():
                    major_ver = int(part.split(".")[0])
                    if major_ver < 2:
                        print(f"Warning: gh version {part} detected. GitHub CLI v2.0.0+ is required for --json support.", file=sys.stderr)
                    break
    except Exception as exc:
        print(f"Warning: Could not check gh version: {exc}", file=sys.stderr)


def api_paginated(path: str) -> list[Any]:
    sep = "&" if "?" in path else "?"
    results = []
    page = 1
    while True:
        page_path = f"{path}{sep}page={page}&per_page=100"
        page_data = gh_json(["api", page_path])
        if not isinstance(page_data, list) or not page_data:
            break
        results.extend(page_data)
        if len(page_data) < 100 or page >= 10:
            break
        page += 1
    return results


def collect_pr(repo: str, pr: dict[str, Any]) -> dict[str, Any] | None:
    try:
        number = int(pr["number"])
        full_name = f"{OWNER}/{repo}"
        base_api = f"repos/{full_name}/pulls/{number}"

        detail = gh_json(
            [
                "pr",
                "view",
                str(number),
                "--repo",
                full_name,
                "--json",
                "number,title,url,state,isDraft,author,headRefName,baseRefName,reviewDecision,mergeable,labels,assignees,createdAt,updatedAt,body,commits,statusCheckRollup",
            ]
        )
        if not isinstance(detail, dict) or "number" not in detail:
            print(f"Skipping PR #{number} in repo {repo}: pr view returned invalid JSON", file=sys.stderr)
            return None

        return {
            "repo": repo,
            "repository": full_name,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "pr": detail,
            "issue_comments": api_paginated(f"repos/{full_name}/issues/{number}/comments"),
            "reviews": api_paginated(f"{base_api}/reviews"),
            "review_comments": api_paginated(f"{base_api}/comments"),
            "files": api_paginated(f"{base_api}/files"),
        }
    except Exception as exc:
        print(f"Error collecting PR #{pr.get('number')} in repo {repo}: {exc}", file=sys.stderr)
        return None


def write_repo_outputs(repo: str, entries: list[dict[str, Any]]) -> None:
    repo_dir = OUT_DIR / repo
    repo_dir.mkdir(parents=True, exist_ok=True)

    index: list[dict[str, Any]] = []
    for entry in entries:
        pr = entry.get("pr")
        if not isinstance(pr, dict):
            continue
        number = pr.get("number")
        if number is None:
            continue
        path = repo_dir / f"pr-{number}.json"
        path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")
        index.append(
            {
                "number": number,
                "title": pr.get("title", ""),
                "url": pr.get("url", ""),
                "state": pr.get("state", ""),
                "isDraft": pr.get("isDraft", False),
                "headRefName": pr.get("headRefName", ""),
                "baseRefName": pr.get("baseRefName", ""),
                "reviewDecision": pr.get("reviewDecision"),
                "file": str(path.relative_to(OUT_DIR.parent)),
            }
        )

    (repo_dir / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")


def print_summary(summary: list[dict[str, Any]]) -> None:
    print(f"{'REPO':<24} {'PR':<7} {'STATE':<8} {'REVIEW':<18} URL")
    print(f"{'-' * 24:<24} {'-' * 7:<7} {'-' * 8:<8} {'-' * 18:<18} {'-' * 30}")
    for row in summary:
        print(
            f"{row['repo']:<24} #{row['number']:<6} {row['state']:<8} "
            f"{str(row.get('reviewDecision') or '-'):<18} {row['url']}"
        )
    print()
    print(f"Review data written to {OUT_DIR}")


def main() -> int:
    if shutil.which("gh") is None:
        raise SystemExit("Missing required command: gh")
    check_gh_version()
    gh_check(["auth", "status"])

    repos = read_repos()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_summary: list[dict[str, Any]] = []
    all_index: dict[str, list[dict[str, Any]]] = {}

    for repo in repos:
        full_name = f"{OWNER}/{repo}"
        try:
            prs = gh_json(
                [
                    "pr",
                    "list",
                    "--repo",
                    full_name,
                    "--state",
                    PR_STATE,
                    "--limit",
                    str(LIMIT),
                    "--json",
                    "number,title,url,state,headRefName,baseRefName,reviewDecision,isDraft,updatedAt",
                ]
            )
        except Exception as exc:
            print(f"Skipping repo {repo} due to API/access error: {exc}", file=sys.stderr)
            continue

        if not isinstance(prs, list):
            print(f"Skipping repo {repo}: list response is not a JSON array", file=sys.stderr)
            continue

        valid_prs = []
        for pr in prs:
            if isinstance(pr, dict) and "number" in pr:
                valid_prs.append(pr)
            else:
                print(f"Skipping malformed PR description in repo {repo}: {pr}", file=sys.stderr)

        entries = []
        for pr in valid_prs:
            entry = collect_pr(repo, pr)
            if entry is not None:
                entries.append(entry)

        write_repo_outputs(repo, entries)

        repo_summary: list[dict[str, Any]] = []
        for entry in entries:
            pr = entry["pr"]
            row = {
                "repo": repo,
                "number": pr.get("number"),
                "title": pr.get("title", ""),
                "url": pr.get("url", ""),
                "state": pr.get("state", ""),
                "reviewDecision": pr.get("reviewDecision"),
                "headRefName": pr.get("headRefName", ""),
                "baseRefName": pr.get("baseRefName", ""),
            }
            repo_summary.append(row)
            all_summary.append(row)
        all_index[repo] = repo_summary

    (OUT_DIR / "index.json").write_text(json.dumps(all_index, indent=2, sort_keys=True) + "\n")
    print_summary(all_summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc))
