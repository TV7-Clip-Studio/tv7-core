"""Framework-neutral contracts shared by the TV7 cockpit API and tests."""

from __future__ import annotations

from pathlib import Path
import re


CORE_DIR = Path(__file__).resolve().parents[1]


def allowed_repos() -> set[str]:
    config = CORE_DIR / "tooling" / "repos-checks.conf"
    repos = set()
    for raw in config.read_text(encoding="utf-8").splitlines() if config.exists() else []:
        line = raw.strip()
        if line and not line.startswith("#"):
            repos.add(line.split("|", 1)[0].strip())
    return repos


def focus_display(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("slice", "title", "next_action"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    return "General / Clean Slice"


def normalize_action(action_type: str) -> str:
    mapping = {
        "dirty-needs-ready": "ready",
        "dirty-pr-needs-ready": "ready",
        "ahead-needs-review": "review",
        "pr-updates-need-review": "review",
        "pr-changes-requested": "review",
        "pr-awaiting-review": "review",
        "pr-ready": "review",
        "clean-needs-agent-work": "start",
        "validated-needs-commit": "commit",
    }
    return mapping.get(action_type, action_type)


def action_command(repo: str, action_type: str, requested: str) -> tuple[list[str], Path]:
    if repo not in allowed_repos():
        raise ValueError("Unknown repository.")
    repo_dir = CORE_DIR.parent / repo
    if action_type == "ready":
        return ["make", "ready", f"REPO={repo}"], CORE_DIR
    if action_type == "review":
        return ["make", "review", f"REPO={repo}"], CORE_DIR
    if action_type == "commit":
        return ["python3", "tooling/cockpit_commit.py", "--repo", repo], CORE_DIR
    if action_type == "start":
        match = re.fullmatch(r"start\s+([A-Z]+-[A-Z0-9-]+)", requested.strip())
        if not match:
            raise ValueError("Invalid roadmap start action.")
        return ["make", "conductor-tickets-apply", f"CONDUCTOR_TICKET_ITEM_PREFIX={match.group(1)}"], CORE_DIR
    if action_type == "skip":
        return ["git", "rebase", "--skip"], repo_dir
    if action_type == "reset":
        return ["bash", "-lc", "git rebase --abort && git reset --hard @{u}"], repo_dir
    if action_type.startswith("conductor-"):
        target = action_type.removeprefix("conductor-")
        if target not in {"status", "run-once", "events"}:
            raise ValueError("Invalid Conductor action.")
        return ["make", f"conductor-{target}"], CORE_DIR
    raise ValueError(f"Unsupported cockpit action: {action_type}")


class MockRepoState:
    """Minimal RepoState adapter for sync queue updates."""

    def __init__(self, data: dict) -> None:
        self.repo = data["repo"]
        self.branch = data.get("branch", "main")
        self.path = CORE_DIR.parent / self.repo
        self.test_plan = data.get("test_plan") or {}
        self.dirty_files = data.get("dirty_files") or []
        self.queue_status = data.get("queue_status")
        self.commits = data.get("recent_commits") or []
        focus_data = data.get("focus")
        if focus_data:
            self.focus = type("MockFocus", (), {
                "item_id": focus_data.get("item_id", ""),
                "title": focus_data.get("title", ""),
            })()
        else:
            self.focus = None
        self.dirty_status_hash = f"{len(self.dirty_files)}-{self.branch}"
