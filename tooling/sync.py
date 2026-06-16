#!/usr/bin/env python3
"""TV7 cross-repo sync cockpit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
RESET = "\033[0m"


ROADMAPS: dict[str, list[str]] = {
    "tv7-core": [
        "tv7-core/docs/roadmaps/tv7-core-roadmap.md",
        "tv7-core/docs/roadmaps/core/agent-orchestration-roadmap.md",
        "tv7-core/docs/roadmaps/core/project-conductor-roadmap.md",
        "tv7-core/docs/roadmaps/roadmap.md",
    ],
    "tv7-conductor": ["tv7-conductor/docs/roadmaps/tv7-conductor-roadmap.md"],
    "tv7-backend": [
        "tv7-core/docs/roadmaps/tv7-backend-roadmap.md",
        "tv7-core/docs/roadmaps/tv7-backend-off-roadmap.md",
    ],
    "tv7-studio": ["tv7-core/docs/roadmaps/tv7-studio-roadmap.md"],
    "tv7-site": ["tv7-core/docs/roadmaps/tv7-site-roadmap.md"],
    "tv7-engine": ["tv7-core/docs/roadmaps/tv7-engine-roadmap.md"],
}


@dataclass
class RoadmapItem:
    done: bool
    item_id: str
    title: str
    section: str
    path: str


@dataclass
class RepoState:
    repo: str
    path: Path
    exists: bool = False
    branch: str = "-"
    status_ok: bool = True
    note: str = ""
    changes: int = 0
    ahead: int = 0
    upstream: str = ""
    pr: dict[str, Any] | None = None
    dirty_files: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)
    roadmap_items: list[RoadmapItem] = field(default_factory=list)
    focus: RoadmapItem | None = None
    matched_item: RoadmapItem | None = None


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=check)


def print_cmd(cmd: list[str], *, cwd: Path | None = None) -> int:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None).returncode


def git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(path), *args])


def parse_roadmap(path: Path, display_path: str) -> list[RoadmapItem]:
    if not path.exists():
        return []
    items: list[RoadmapItem] = []
    section = "Unsectioned"
    pattern = re.compile(r"^-\s+\[(?P<done>[ xX])\]\s+\[(?P<id>[A-Z]+-[A-Z0-9-]+)\]\s+(?P<title>.+?)\s*$")
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            section = line.lstrip("#").strip()
            continue
        match = pattern.match(line)
        if not match:
            continue
        items.append(
            RoadmapItem(
                done=match.group("done").lower() == "x",
                item_id=match.group("id"),
                title=match.group("title").strip(),
                section=section,
                path=display_path,
            )
        )
    return items


def collect_roadmap_items(repo: str, workspace: Path) -> list[RoadmapItem]:
    items: list[RoadmapItem] = []
    for rel in ROADMAPS.get(repo, []):
        path = workspace / rel
        items.extend(parse_roadmap(path, rel))
    return items


def get_pr(owner: str, repo: str, branch: str) -> dict[str, Any] | None:
    if branch in {"", "-", "HEAD"}:
        return None
    if not shutil_which("gh"):
        return None
    if run(["gh", "auth", "status"]).returncode != 0:
        return {"note": "gh auth missing"}
    base_cmd = [
        "gh",
        "pr",
        "list",
        "--repo",
        f"{owner}/{repo}",
        "--head",
        branch,
        "--limit",
        "1",
        "--json",
        "number,url,state,title,body,reviewDecision,updatedAt",
    ]
    rows = run([*base_cmd, "--state", "all"])
    if rows.returncode != 0:
        rows = run([*base_cmd, "--state", "open"])
    if rows.returncode != 0 or not rows.stdout.strip():
        return None
    try:
        parsed = json.loads(rows.stdout)
    except json.JSONDecodeError:
        return None
    return parsed[0] if parsed else None


def shutil_which(name: str) -> str | None:
    for part in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(part) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def sync_repo(repo: str, path: Path, owner: str, sync_base: str) -> RepoState:
    state = RepoState(repo=repo, path=path)
    if not (path / ".git").is_dir():
        state.exists = False
        state.status_ok = False
        state.note = f"missing at {path}"
        return state

    state.exists = True
    state.branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "-"
    git(path, "fetch", "--quiet", "--prune")
    upstream = git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout.strip()
    if not upstream and git(path, "ls-remote", "--exit-code", "--heads", "origin", state.branch).returncode == 0:
        if git(path, "branch", "--set-upstream-to", f"origin/{state.branch}", state.branch).returncode == 0:
            upstream = f"origin/{state.branch}"
    state.upstream = upstream

    if upstream:
        pulled = git(path, "pull", "--rebase", "--autostash")
        if pulled.returncode != 0:
            state.status_ok = False
            conflicts = git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
            state.note = f"rebase failed onto {upstream}; conflicts: {' '.join(conflicts) if conflicts else 'see git status'}"
        else:
            state.changes = count_changes(path)
            state.ahead = int_or_zero(git(path, "rev-list", "--count", "@{u}..HEAD").stdout)
            state.note = status_note(state.changes, state.ahead)
    else:
        if git(path, "rev-parse", "--verify", "--quiet", f"{sync_base}^{{commit}}").returncode == 0:
            rebased = git(path, "rebase", "--autostash", sync_base)
            if rebased.returncode != 0:
                state.status_ok = False
                conflicts = git(path, "diff", "--name-only", "--diff-filter=U").stdout.split()
                state.note = f"rebase failed onto {sync_base}; conflicts: {' '.join(conflicts) if conflicts else 'see git status'}"
            else:
                state.changes = count_changes(path)
                state.ahead = int_or_zero(git(path, "rev-list", "--count", f"{sync_base}..HEAD").stdout)
                detail = status_note(state.changes, state.ahead)
                state.note = f"local branch (rebased onto {sync_base}, {detail})"
        else:
            state.changes = count_changes(path)
            state.note = "local branch (no upstream, clean)" if state.changes == 0 else f"local branch (no upstream, {state.changes} pending)"

    state.dirty_files = git(path, "status", "--porcelain").stdout.splitlines()
    state.commits = git(path, "log", "--oneline", "-n", "3").stdout.splitlines()
    state.signals = detect_repo_signals(repo, path, state.dirty_files)
    state.pr = get_pr(owner, repo, state.branch)
    return state


def file_contains(path: Path, text: str) -> bool:
    if not path.exists():
        return False
    try:
        return text in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def detect_repo_signals(repo: str, path: Path, dirty_files: list[str]) -> dict[str, Any]:
    if repo == "tv7-backend":
        return detect_backend_signals(path, dirty_files)
    return {}


def detect_backend_signals(path: Path, dirty_files: list[str]) -> dict[str, Any]:
    cloud_ai_route = path / "src" / "app" / "api" / "v1" / "cloud_ai.py"
    auth_route = path / "src" / "app" / "api" / "v1" / "auth.py"
    tests = path / "tests" / "test_cloud_ai_api.py"
    migration_dir = path / "alembic" / "versions"
    dirty_paths = [line[3:] if len(line) > 3 else line.strip() for line in dirty_files]
    return {
        "summary": [
            "Pending uncommitted cloud AI implementation exists; preserve and harden it."
            if cloud_ai_route.exists()
            else "Cloud AI route file not detected.",
            "Engine token endpoint exists."
            if file_contains(cloud_ai_route, '"/engine-token"')
            else "Engine token endpoint not detected.",
            "Engine execution endpoint exists."
            if file_contains(cloud_ai_route, '"/engine/execute"')
            else "Engine execution endpoint not detected.",
            "Studio license readiness endpoint is missing."
            if not file_contains(auth_route, '"/license"')
            else "Studio license readiness endpoint exists.",
        ],
        "cloud_ai_route_exists": cloud_ai_route.exists(),
        "engine_token_endpoint_exists": file_contains(cloud_ai_route, '"/engine-token"'),
        "engine_execute_endpoint_exists": file_contains(cloud_ai_route, '"/engine/execute"'),
        "auth_license_endpoint_exists": file_contains(auth_route, '"/license"'),
        "cloud_ai_tests_exist": tests.exists(),
        "cloud_ai_migration_exists": any(migration_dir.glob("*cloud_ai*")) if migration_dir.exists() else False,
        "dirty_untracked_files": [line for line in dirty_files if line.strip().startswith("??")],
        "dirty_cloud_ai_files": [item for item in dirty_paths if "cloud_ai" in item or "cloud-ai" in item],
    }


def int_or_zero(raw: str) -> int:
    try:
        return int(raw.strip())
    except ValueError:
        return 0


def count_changes(path: Path) -> int:
    return len([line for line in git(path, "status", "--porcelain").stdout.splitlines() if line.strip()])


def status_hash(dirty_files: list[str]) -> str:
    payload = "\n".join(dirty_files).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def status_note(changes: int, ahead: int) -> str:
    parts = []
    if changes:
        parts.append(f"{YELLOW}{changes} pending{RESET}")
    if ahead:
        parts.append(f"{CYAN}{ahead} ahead{RESET}")
    return ", ".join(parts) if parts else "clean"


def infer_focus(state: RepoState) -> None:
    open_items = [item for item in state.roadmap_items if not item.done]
    haystack = "\n".join(
        [
            state.branch,
            str((state.pr or {}).get("title", "")),
            str((state.pr or {}).get("body", "")),
            "\n".join(state.dirty_files),
            "\n".join(state.commits),
        ]
    )
    for item in open_items:
        if item.item_id in haystack:
            state.matched_item = item
            state.focus = item
            return

    preferred = [
        item
        for item in open_items
        if item.section.lower() in {"needs to be done", "planned off-roadmap work"}
    ]
    state.focus = (preferred or open_items or [None])[0]


def repo_summary_for_gemini(states: list[RepoState]) -> list[dict[str, Any]]:
    rows = []
    for state in states:
        open_items = [item for item in state.roadmap_items if not item.done]
        done_items = [item for item in state.roadmap_items if item.done]
        rows.append(
            {
                "repo": state.repo,
                "branch": state.branch,
                "head_sha": git(state.path, "rev-parse", "HEAD").stdout.strip() if state.exists else "",
                "git_note": strip_ansi(state.note),
                "dirty_files": state.dirty_files,
                "dirty_file_count": len(state.dirty_files),
                "dirty_status_hash": status_hash(state.dirty_files),
                "recent_commits": state.commits,
                "signals": state.signals,
                "pr": state.pr,
                "focus": item_to_dict(state.focus),
                "matched_item": item_to_dict(state.matched_item),
                "open_required_count": len(
                    [item for item in open_items if item.section.lower() in {"needs to be done", "planned off-roadmap work"}]
                ),
                "open_other_count": len(open_items)
                - len([item for item in open_items if item.section.lower() in {"needs to be done", "planned off-roadmap work"}]),
                "completed_count": len(done_items),
                "last_completed": item_to_dict(done_items[-1] if done_items else None),
            }
        )
    return rows


def item_to_dict(item: RoadmapItem | None) -> dict[str, str] | None:
    if item is None:
        return None
    return {
        "id": item.item_id,
        "title": item.title,
        "section": item.section,
        "path": item.path,
    }


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def gemini_summary(summary: list[dict[str, Any]], core_dir: Path) -> dict[str, str]:
    if os.environ.get("SYNC_GEMINI", "1") == "0":
        return {}
    if not shutil_which("gemini"):
        return {}
    prompt = (
        "You are the TV7 planner. Summarize the status of each repository from the provided JSON sync state.\n"
        "Return a JSON object where the keys are the repository names and the values are string summaries.\n"
        "Each summary string must concisely describe what the repository is currently working on (based on the focus/matched roadmap item), "
        "any pending changes or dirty files, semantic signals if present, and the next recommended action. "
        "When semantic signals show an implementation already exists, say to preserve/harden/validate it instead of rebuilding it. "
        "Keep the descriptions tight and professional. Avoid any markdown code block wrappers (like ```json) in your raw response, "
        "or if you do, ensure the response is still valid JSON after stripping them. "
        "Use ONLY the JSON structure provided. Do not invent any repositories.\n\n"
        + json.dumps(summary, indent=2)
    )

    models = ["gemini-2.5-flash", "gemini-2.5-pro"]
    for model in models:
        try:
            start_time = time.time()
            res = subprocess.run(
                ["gemini", "-m", model, "-o", "json", "-p", "-"],
                cwd=str(core_dir),
                input=prompt,
                capture_output=True,
                text=True,
                timeout=int(os.environ.get("SYNC_GEMINI_TIMEOUT", "25")),
                check=False,
            )
            if res.returncode != 0:
                continue

            envelope = json.loads(res.stdout)
            stats = envelope.get("stats", {})
            model_info = ""
            if "models" in stats:
                actual_model = next(iter(stats["models"].keys()), model)
                tokens = stats["models"][actual_model].get("tokens", {})
                inp = tokens.get("input", 0)
                out = tokens.get("candidates", 0)
                cached = tokens.get("cached", 0)
                cached_str = f" ({cached} cached)" if cached else ""
                model_info = f"model: {actual_model}, tokens: {inp + out}{cached_str}"
            else:
                model_info = f"model: {model}"
            
            elapsed = time.time() - start_time
            print(f"  [gemini metrics: {model_info}, time: {elapsed:.1f}s]")

            content = envelope.get("response", "").strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            parsed_dict = json.loads(content)
            if isinstance(parsed_dict, dict):
                return {str(k): str(v) for k, v in parsed_dict.items()}
        except Exception:
            continue
    return {}


def get_fallback_focus(state: RepoState) -> str:
    open_items = [item for item in state.roadmap_items if not item.done]
    if state.focus:
        source = "matched" if state.matched_item else "next"
        desc = f"Working on `{state.focus.title}` ({source} {state.focus.item_id})"
    else:
        desc = "no open roadmap items found"
    
    pending = []
    if state.changes:
        pending.append(f"{state.changes} pending changes")
    if state.dirty_files:
        untracked = sum(1 for f in state.dirty_files if f.strip().startswith("??"))
        if untracked:
            # Match the including format
            pending.append(f"including {untracked} untracked files")
    
    # We combine them nicely
    pending_str = ""
    if len(pending) == 2:
        pending_str = f"{pending[0]} {pending[1]}"
    elif len(pending) == 1:
        pending_str = pending[0]
        
    if pending_str:
        desc += f"; {pending_str}"
    return desc


def print_repo_status(states: list[RepoState], focus_map: dict[str, str]) -> None:
    for state in states:
        mark = f"{GREEN}[✓]{RESET}" if state.status_ok else f"{RED}[X]{RESET}"
        if not state.exists:
            print(f"{mark} {state.repo} - {state.note}")
            continue
        pr_note = "PR: none"
        if state.pr:
            if "note" in state.pr:
                pr_note = f"PR: {state.pr['note']}"
            else:
                pr_note = f"PR: #{state.pr.get('number')} {str(state.pr.get('state', '')).upper()} {state.pr.get('url', '')}"
        
        total = len(state.roadmap_items)
        done = sum(1 for item in state.roadmap_items if item.done)
        pct = (done / total * 100.0) if total > 0 else 0.0
        metric_str = f" [Roadmap: {done}/{total} done ({pct:.1f}%)]"
        
        print(f"{mark} {state.repo} ({CYAN}{state.branch}{RESET}) - {state.note} - {pr_note}{metric_str}")
        
        focus_desc = focus_map.get(state.repo, "").strip()
        if not focus_desc:
            focus_desc = get_fallback_focus(state)
        print(f"    {focus_desc}")


def write_artifacts(core_dir: Path, states: list[RepoState], focus_map: dict[str, str], global_metric: str) -> None:
    out_dir = core_dir / "docs" / ".tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    summary = repo_summary_for_gemini(states)
    generated_at = datetime.now(timezone.utc).isoformat()
    state_by_repo = {state.repo: state for state in states}
    for item in summary:
        repo = item["repo"]
        state = state_by_repo.get(repo)
        focus_desc = focus_map.get(repo, "").strip()
        if state and not focus_desc:
            focus_desc = get_fallback_focus(state)
        item["resolved_focus"] = focus_desc
        item["sync_generated_at"] = generated_at

    (out_dir / "sync-roadmap-focus.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    
    md_lines = ["# TV7 Sync Cockpit", f"**{global_metric}**\n"]
    for state in states:
        mark = "[✓]" if state.status_ok else "[X]"
        if not state.exists:
            md_lines.append(f"- **{mark} {state.repo}** - {state.note}")
            continue
        pr_note = "PR: none"
        if state.pr:
            if "note" in state.pr:
                pr_note = f"PR: {state.pr['note']}"
            else:
                pr_note = f"PR: #{state.pr.get('number')} {str(state.pr.get('state', '')).upper()} {state.pr.get('url', '')}"
        
        total = len(state.roadmap_items)
        done = sum(1 for item in state.roadmap_items if item.done)
        pct = (done / total * 100.0) if total > 0 else 0.0
        metric_str = f" [Roadmap: {done}/{total} done ({pct:.1f}%)]"
        
        md_lines.append(f"- **{mark} {state.repo} ({state.branch})** - {state.note} - {pr_note}{metric_str}")
        
        focus_desc = focus_map.get(state.repo, "").strip()
        if not focus_desc:
            focus_desc = get_fallback_focus(state)
        md_lines.append(f"  {focus_desc}")
        
    (out_dir / "sync-roadmap-focus.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def interactive_actions(core_dir: Path, states: list[RepoState]) -> int:
    if os.environ.get("SYNC_INTERACTIVE", "1") == "0" or not sys.stdin.isatty():
        return 0
    candidates = [state for state in states if state.exists and (state.changes or state.ahead or state.branch != "main" or state.pr)]
    print("\nActions:")
    print("  1) Operate a repo branch/PR")
    print("  2) Generate agent handoffs")
    print("  3) Print agent prompts")
    print("  4) Exit")
    choice = input("Select action [1-4, default: 4]: ").strip() or "4"
    if choice == "2":
        return print_cmd(["python3", str(core_dir / "tooling" / "handoff.py")], cwd=core_dir)
    if choice == "3":
        env = os.environ.copy()
        env["HANDOFF_PROMPTS_ONLY"] = "1"
        return subprocess.run(["python3", str(core_dir / "tooling" / "handoff.py")], cwd=str(core_dir), env=env).returncode
    if choice != "1":
        return 0
    if candidates:
        print("Likely repos needing attention:")
        for state in candidates:
            pr = state.pr.get("url", "") if state.pr else ""
            print(f"  - {state.repo} ({state.branch}) {pr}")
    return print_cmd(["bash", str(core_dir / "tooling" / "git-dev.sh")], cwd=core_dir)


def main() -> int:
    core_dir = Path(__file__).resolve().parents[1]
    workspace = Path(os.environ.get("REPO_ROOT", str(core_dir.parent))).resolve()
    owner = os.environ.get("OWNER", "TV7-Clip-Studio")
    repos = os.environ.get("REPOS", "tv7-core tv7-conductor tv7-engine tv7-backend tv7-studio tv7-site").split()
    sync_base = os.environ.get("SYNC_BASE", "origin/main")

    states = [sync_repo(repo, workspace / repo, owner, sync_base) for repo in repos]
    for state in states:
        state.roadmap_items = collect_roadmap_items(state.repo, workspace)
        infer_focus(state)

    # 1. Fetch Gemini summaries first
    summary = repo_summary_for_gemini(states)
    focus_map = gemini_summary(summary, core_dir)

    # 2. Compute global workspace metrics
    total_items = sum(len(state.roadmap_items) for state in states)
    total_done = sum(sum(1 for item in state.roadmap_items if item.done) for state in states)
    global_pct = (total_done / total_items * 100.0) if total_items > 0 else 0.0
    global_metric = f"Workspace Roadmap: {total_done}/{total_items} done ({global_pct:.1f}%)"

    # 3. Print global header
    print(f"\n{global_metric}\n")

    # 4. Print unified repo list
    print_repo_status(states, focus_map)

    # 5. Write updated artifacts
    write_artifacts(core_dir, states, focus_map, global_metric)

    if os.environ.get("SYNC_MODE") == "operate":
        return print_cmd(["bash", str(core_dir / "tooling" / "git-dev.sh")], cwd=core_dir)
    return interactive_actions(core_dir, states)


if __name__ == "__main__":
    raise SystemExit(main())
