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


def workflow_from_state(row: dict, latest_review: dict | None = None) -> dict:
    action = row.get("action") or {}
    pr = row.get("pr") or {}
    dirty = int(row.get("dirty_file_count") or 0)
    ahead = int(row.get("ahead") or 0)
    if action.get("state") == "validated-needs-commit":
        return {
            "mode": "validated-commit",
            "allowed_actions": ["commit"],
            "summary": "Machine and human validation passed; commit this slice locally.",
        }
    if action.get("state") == "awaiting-human-validation":
        return {
            "mode": "human-validation",
            "allowed_actions": ["record-validation"],
            "summary": "Machine checks passed; complete the human validation step before commit.",
        }
    if action.get("state") == "validation-failed":
        return {
            "mode": "validation-failed",
            "allowed_actions": ["return-to-agent"],
            "summary": "Human validation failed; return the failure context before another ready check.",
        }
    if action.get("state") in {"dirty-needs-ready", "dirty-pr-needs-ready"}:
        return {
            "mode": "dirty-validation",
            "allowed_actions": ["ready"],
            "summary": "Local changes need machine validation before human validation, commit, or review.",
        }
    if pr and "note" not in pr:
        if latest_review:
            reviewed_sha = str(latest_review.get("head_sha") or "")
            head_sha = str(row.get("head_sha") or "")
            fresh = reviewed_sha == head_sha
            if fresh and not dirty and not ahead:
                verdict = str(latest_review.get("verdict") or "").upper()
                confidence = latest_review.get("confidence")
                return {
                    "mode": "pr-review-decision",
                    "review": latest_review,
                    "allowed_actions": ["fix-pr-review", "merge-pr", "defer"],
                    "summary": f"DeepSeek reviewed current PR HEAD: {verdict} {confidence or ''}%",
                }
            return {
                "mode": "pr-follow-up",
                "review": latest_review,
                "allowed_actions": ["prepare-pr-follow-up", "defer"],
                "summary": "DeepSeek review covers an older PR state; local changes must be prepared and reviewed before merge.",
            }
        if action.get("state") in {"pr-awaiting-review", "pr-updates-need-review"}:
            return {
                "mode": "pr-awaiting-review",
                "allowed_actions": ["review-pr", "defer"],
                "summary": "PR is open and waiting for a current DeepSeek review.",
            }
    if action.get("state") == "ahead-needs-review":
        return {
            "mode": "ahead-review",
            "allowed_actions": ["review-pr"],
            "summary": "Local commits are ready to push and review.",
        }
    if action.get("state") == "clean-needs-agent-work":
        return {
            "mode": "agent-work",
            "allowed_actions": ["start-roadmap"],
            "summary": "Repo is clean and ready for the next roadmap item.",
        }
    return {
        "mode": "idle",
        "allowed_actions": [],
        "summary": "No immediate cockpit action is required.",
    }


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
