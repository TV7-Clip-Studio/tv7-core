#!/usr/bin/env python3
"""Validate and summarize one repo before the human commits it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
RESET = "\033[0m"


def init_colors() -> None:
    global GREEN, RED, YELLOW, CYAN, RESET
    disable_color = False
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        disable_color = True
    elif not sys.stdout.isatty():
        disable_color = True

    if disable_color:
        GREEN = ""
        RED = ""
        YELLOW = ""
        CYAN = ""
        RESET = ""


@dataclass(frozen=True)
class RepoConfig:
    repo: str
    base: str
    check_command: str
    docs_only_allowed: bool


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=path)


def fail(message: str) -> None:
    raise SystemExit(f"{RED}[error]{RESET} {message}")


def print_ok(message: str) -> None:
    print(f"{GREEN}[ok]{RESET} {message}")


def print_warn(message: str) -> None:
    print(f"{YELLOW}[warn]{RESET} {message}")


def print_step(message: str) -> None:
    print(f"{CYAN}[..]{RESET} {message}")


def load_repo_config(config_file: Path, repo: str) -> RepoConfig:
    if not config_file.exists():
        fail(f"missing config file: {config_file}")
    for raw in config_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 4:
            continue
        if parts[0] == repo:
            return RepoConfig(
                repo=parts[0],
                base=parts[1] or "main",
                check_command=parts[2],
                docs_only_allowed=parts[3] == "1",
            )
    fail(f"unknown repo: {repo}. Set REPO to one of the repos in {config_file}")


def dirty_files(repo_path: Path) -> list[str]:
    return [line for line in git(repo_path, "status", "--porcelain").stdout.splitlines() if line.strip()]


def clean_path(line: str) -> str:
    return line[3:] if len(line) > 3 else line.strip()


def group_files(files: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for line in files:
        path = clean_path(line)
        if "/" in path:
            key = path.split("/", 1)[0]
        elif path in {"Makefile", "README.md", "Cargo.toml", "Cargo.lock", "pyproject.toml", "package.json"}:
            key = "root"
        else:
            key = "misc"
        groups.setdefault(key, []).append(line)
    return groups


def file_contains(path: Path, text: str) -> bool:
    if not path.exists():
        return False
    try:
        return text in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def infer_slice(repo: str, repo_path: Path, files: list[str], commits: list[str]) -> str:
    haystack = "\n".join([*files, *commits]).lower()
    if repo == "tv7-engine" and any(
        file_contains(repo_path / clean_path(line), marker)
        for line in files
        for marker in ("transcript_generate", "/v1/transcripts/generate", "TRANSCRIPTION_SETUP_REQUIRED")
    ):
        return "Engine transcript generation contract"
    if repo == "tv7-studio" and (
        "quick_clip" in haystack
        or "dashboard" in haystack
        or "diagnostics" in haystack
        or "engine_client" in haystack
    ):
        return "Studio Quick Clip and diagnostics integration"
    if repo == "tv7-backend" and ("cloud_ai" in haystack or "cloud-ai" in haystack):
        return "Backend cloud AI control plane"
    if "review.py" in haystack or "ready.py" in haystack or "sync.py" in haystack or "handoff" in haystack:
        return "Core cockpit and handoff tooling"
    if "site" in haystack or "astro" in haystack or "component" in haystack:
        return "Site component and content polish"
    return "Repository implementation slice"


def infer_commit_title(repo: str, slice_name: str) -> str:
    slug = slice_name[:1].lower() + slice_name[1:]
    return f"{repo}: {slug}"


def recent_commits(repo_path: Path) -> list[str]:
    return git(repo_path, "log", "--oneline", "-n", "5").stdout.splitlines()


def run_diff_check(repo_path: Path) -> bool:
    print_step("running git diff --check")
    result = git(repo_path, "diff", "--check")
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        return False
    print_ok("diff whitespace check passed")
    return True


def run_validation(repo_path: Path, cfg: RepoConfig) -> bool:
    if os.environ.get("READY_SKIP_VALIDATION", "0") == "1":
        print_warn("repo validation skipped by READY_SKIP_VALIDATION=1")
        return True
    if not cfg.check_command:
        print_warn("no repo validation command configured")
        return True
    print_step(f"running validation: {cfg.check_command}")
    result = run(["bash", "-lc", cfg.check_command], cwd=repo_path)
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout[-5000:])
        if result.stderr.strip():
            print(result.stderr[-5000:], file=sys.stderr)
        return False
    print_ok("repo validation passed")
    return True


def handoff_check(core_dir: Path, repo: str) -> bool:
    if repo != "tv7-core":
        return True
    print_step("running Core handoff freshness check")
    result = run(["make", "handoff-check"], cwd=core_dir)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        return False
    return True


def refresh_core_handoffs(core_dir: Path, repo: str) -> bool:
    if repo != "tv7-core":
        return True
    print_step("refreshing generated agent handoffs from the latest sync state")
    result = run(["make", "handoff"], cwd=core_dir)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        print_warn("handoff regeneration failed")
        return False
    print_ok("generated handoffs refreshed")
    return True


def list_configured_repos(config_file: Path) -> list[str]:
    if not config_file.exists():
        return ["tv7-core", "tv7-conductor", "tv7-engine", "tv7-backend", "tv7-studio", "tv7-site"]
    repos = []
    for raw in config_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if parts:
            repos.append(parts[0])
    return repos


def main() -> int:
    init_colors()
    repo = os.environ.get("REPO", "").strip()
    repo_root = Path(os.environ.get("REPO_ROOT", "..")).resolve()
    core_dir = Path(__file__).resolve().parents[1]
    config_file = Path(os.environ.get("CONFIG_FILE", core_dir / "tooling" / "repos-checks.conf")).resolve()

    if not repo:
        if not sys.stdin.isatty():
            fail("REPO is required, for example: make ready REPO=tv7-engine")

        configured_repos = list_configured_repos(config_file)
        print("\nSelect a repository to run ready check:")
        for idx, r in enumerate(configured_repos, 1):
            r_path = repo_root / r
            status = "missing"
            if (r_path / ".git").is_dir():
                changes = len([line for line in git(r_path, "status", "--porcelain").stdout.splitlines() if line.strip()])
                status = f"{YELLOW}{changes} pending{RESET}" if changes else f"{GREEN}clean{RESET}"
            print(f"  {idx}) {r:<15} [{status}]")
        print(f"  {len(configured_repos) + 1}) Exit")

        try:
            choice = input(f"Select option [1-{len(configured_repos) + 1}]: ").strip()
            if not choice or choice == str(len(configured_repos) + 1):
                return 0
            if not choice.isdigit() or not 1 <= int(choice) <= len(configured_repos):
                fail("invalid selection")
            repo = configured_repos[int(choice) - 1]
        except (KeyboardInterrupt, EOFError):
            print()
            return 0
    cfg = load_repo_config(config_file, repo)
    repo_path = repo_root / repo
    if not (repo_path / ".git").is_dir():
        fail(f"repo not found: {repo_path}")

    if not refresh_core_handoffs(core_dir, repo):
        return 1
    files = dirty_files(repo_path)
    commits = recent_commits(repo_path)
    slice_name = infer_slice(repo, repo_path, files, commits)

    print(f"{CYAN}=== TV7 Ready Check ==={RESET}")
    print(f"Repo: {repo}")
    print(f"Branch: {git(repo_path, 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()}")
    print(f"Slice: {slice_name}")
    print(f"Timestamp: {datetime.now().isoformat(timespec='seconds')}")

    if not files:
        print_ok("working tree is clean")
        print(f"Next: make review REPO={repo}")
        return 0

    print("\nChanged files:")
    groups = group_files(files)
    for group, lines in sorted(groups.items()):
        print(f"  {group}: {len(lines)}")
        for line in lines[:8]:
            print(f"    {line}")
        if len(lines) > 8:
            print(f"    ... {len(lines) - 8} more")

    ok = True
    ok = run_diff_check(repo_path) and ok
    ok = run_validation(repo_path, cfg) and ok

    print("\nRecent commits:")
    for commit in commits[:5]:
        print(f"  - {commit}")

    print("\nSuggested commit title:")
    print(f"  {infer_commit_title(repo, slice_name)}")

    if ok:
        print_ok("ready to commit after human review")
        print(f"Next: commit in {repo}, then run make review REPO={repo}")
        return 0

    print_warn("not ready to commit; fix validation issues first")
    return 1


if __name__ == "__main__":
    if sys.version_info < (3, 11):
        fail("Python 3.11+ is required")
    if shutil.which("git") is None:
        fail("missing required command: git")
    raise SystemExit(main())
