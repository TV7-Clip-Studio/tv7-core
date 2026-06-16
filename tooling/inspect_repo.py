#!/usr/bin/env python3
"""Inspect one TV7 repo after an agent round without syncing or mutating git state."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import sync as sync_tool


REPO_HINTS: dict[str, dict[str, Any]] = {
    "tv7-backend": {
        "validation": ["make lint", "make type", "make test", "make testcov"],
        "core_files": [
            "docs/contracts/openapi/tv7-backend/openapi.json",
            "docs/roadmaps/tv7-backend-roadmap.md",
            "docs/handoffs/active/backend.md",
        ],
    },
    "tv7-engine": {
        "validation": ["make fmt-check", "make check", "make test", "make clippy"],
        "core_files": [
            "docs/contracts/openapi/tv7-engine/openapi.json",
            "docs/contracts/tv7-engine/runtime-setup.md",
            "docs/contracts/tv7-engine/ai-provider-handoff.md",
            "docs/roadmaps/tv7-engine-roadmap.md",
            "docs/handoffs/active/engine.md",
        ],
    },
    "tv7-studio": {
        "validation": ["make format", "make analyze", "make test", "make check"],
        "core_files": [
            "docs/contracts/openapi/tv7-backend/openapi.json",
            "docs/contracts/openapi/tv7-engine/openapi.json",
            "docs/roadmaps/tv7-studio-roadmap.md",
            "docs/handoffs/active/studio.md",
        ],
    },
}


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


def git(path: Path, *args: str) -> str:
    return run(["git", *args], path).stdout.strip()


def print_lines(title: str, lines: list[str]) -> None:
    print(f"\n{title}:")
    if not lines:
        print("  none")
        return
    for line in lines:
        print(f"  {line}")


def dirty_for_paths(core_dir: Path, paths: list[str]) -> list[str]:
    if not paths:
        return []
    status = git(core_dir, "status", "--porcelain", "--", *paths)
    return status.splitlines() if status else []


def main() -> int:
    repo = os.environ.get("REPO", "").strip()
    if not repo:
        print("Usage: make inspect REPO=tv7-backend", file=sys.stderr)
        return 2

    core_dir = Path(__file__).resolve().parents[1]
    workspace = Path(os.environ.get("REPO_ROOT", str(core_dir.parent))).resolve()
    repo_dir = workspace / repo
    if not (repo_dir / ".git").is_dir():
        print(f"Error: {repo} not found at {repo_dir}", file=sys.stderr)
        return 1

    branch = git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD") or "-"
    head = git(repo_dir, "rev-parse", "--short", "HEAD") or "-"
    dirty = git(repo_dir, "status", "--porcelain").splitlines()
    staged = git(repo_dir, "diff", "--cached", "--stat").splitlines()
    unstaged = git(repo_dir, "diff", "--stat").splitlines()
    untracked = [line for line in dirty if line.strip().startswith("??")]
    diff_stat = git(repo_dir, "diff", "--stat").splitlines()
    cached_stat = git(repo_dir, "diff", "--cached", "--stat").splitlines()
    signals = sync_tool.detect_repo_signals(repo, repo_dir, dirty)

    hints = REPO_HINTS.get(repo, {})
    core_dirty = dirty_for_paths(core_dir, hints.get("core_files", []))

    print(f"TV7 inspect: {repo}")
    print(f"Path: {repo_dir}")
    print(f"Branch: {branch}")
    print(f"HEAD: {head}")
    print(f"Dirty files: {len(dirty)}")

    print_lines("Semantic signals", [str(item) for item in signals.get("summary", [])] if signals else [])
    if signals:
        details = [f"{key}: {value}" for key, value in signals.items() if key != "summary"]
        print_lines("Signal details", details)

    print_lines("Dirty files", dirty)
    print_lines("Staged diff stat", cached_stat or staged)
    print_lines("Unstaged diff stat", diff_stat or unstaged)
    print_lines("Untracked files", untracked)
    print_lines("Relevant Core artifacts", core_dirty)
    print_lines("Suggested validation", hints.get("validation", []))

    print("\nNext architect actions:")
    print(f"  1. Review the {repo} diff and validation output from the agent.")
    print(f"  2. Run targeted tests if the agent did not provide fresh validation.")
    print(f"  3. Run `SYNC_INTERACTIVE=0 make sync` from {core_dir} before generating the next handoff.")
    print(f"  4. Run `make handoff HANDOFF_REPO={repo}` if this repo's active handoff should be refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
