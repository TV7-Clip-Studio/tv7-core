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

from test_plans import build_test_plan, terminal_test_plan


GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
RESET = "\033[0m"
REFRESH_COCKPIT = 20


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
    latest_activity: list[str] = field(default_factory=list)
    next_action: str = ""
    test_plan: dict[str, Any] = field(default_factory=dict)
    queue_status: str = ""
    head_sha: str = ""
    dirty_status_hash: str = ""


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
    pr = parsed[0] if parsed else None
    if pr and pr.get("state") == "OPEN":
        # Fetch detailed comments and reviews for the open PR
        detail_cmd = [
            "gh",
            "pr",
            "view",
            str(pr["number"]),
            "--repo",
            f"{owner}/{repo}",
            "--json",
            "comments,reviews,reviewDecision",
        ]
        detail_res = run(detail_cmd)
        if detail_res.returncode == 0:
            try:
                detailed = json.loads(detail_res.stdout)
                pr.update(detailed)
            except Exception:
                pass
    return pr


def get_latest_deepseek_review(pr: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pr:
        return None
    items = []
    for r in pr.get("reviews", []):
        items.append(r)
    for c in pr.get("comments", []):
        items.append(c)

    def get_timestamp(item):
        for key in ["submittedAt", "createdAt", "submitted_at", "created_at"]:
            val = item.get(key)
            if val:
                return str(val)
        return ""

    try:
        items.sort(key=get_timestamp)
    except Exception:
        pass

    latest_review = None
    for item in reversed(items):
        body = str(item.get("body") or "")
        if "DeepSeek review" in body or "Final verdict:" in body or "FINAL_VERDICT:" in body:
            latest_review = item
            break

    if not latest_review:
        return None

    body = str(latest_review.get("body") or "")
    # Parse verdict
    verdict = "UNKNOWN"
    verdict_match = re.search(r"(?:FINAL_VERDICT|Final verdict):\s*(?:[✅❌]\s*)?(APPROVED|REJECTED)", body, re.IGNORECASE)
    if verdict_match:
        verdict = verdict_match.group(1).upper()

    # Parse confidence
    confidence = None
    conf_match = re.search(r"Confidence:\s*(\d{1,3})%", body, re.IGNORECASE)
    if conf_match:
        confidence = int(conf_match.group(1))

    return {
        "verdict": verdict,
        "confidence": confidence,
        "body": body,
        "author": (latest_review.get("author") or {}).get("login") or (latest_review.get("user") or {}).get("login") or "DeepSeek",
    }


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
    fetched = git(path, "fetch", "--quiet", "--prune")

    base_branch = "main"
    if "/" in sync_base:
        base_branch = sync_base.split("/")[-1]

    if state.branch != base_branch and state.branch not in {"", "-", "HEAD"}:
        pr = get_pr(owner, repo, state.branch)
        if pr and pr.get("state") in {"MERGED", "CLOSED"}:
            changes = count_changes(path)
            if changes == 0:
                print(f"  [sync info: PR #{pr.get('number')} is {pr.get('state').lower()}; cleaning up branch {state.branch}...]", file=sys.stderr)
                git(path, "checkout", base_branch)
                if pr.get("state") == "MERGED":
                    git(path, "reset", "--hard", f"origin/{base_branch}")
                else:
                    git(path, "pull")
                git(path, "branch", "-D", state.branch)
                state.branch = base_branch
            else:
                print(f"  [sync info: PR #{pr.get('number')} is {pr.get('state').lower()}, but local branch {state.branch} has uncommitted changes; skipping cleanup]", file=sys.stderr)

    upstream = git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout.strip()
    if not upstream and git(path, "ls-remote", "--exit-code", "--heads", "origin", state.branch).returncode == 0:
        if git(path, "branch", "--set-upstream-to", f"origin/{state.branch}", state.branch).returncode == 0:
            upstream = f"origin/{state.branch}"
    state.upstream = upstream

    if fetched.returncode != 0:
        state.status_ok = False
        state.changes = count_changes(path)
        if upstream:
            state.ahead = int_or_zero(git(path, "rev-list", "--count", f"{upstream}..HEAD").stdout)
        detail = status_note(state.changes, state.ahead)
        state.note = f"remote fetch unavailable; local state: {detail}"
        state.dirty_files = git(path, "status", "--porcelain").stdout.splitlines()
        state.commits = git(path, "log", "--oneline", "-n", "5").stdout.splitlines()
        state.signals = detect_repo_signals(repo, path, state.dirty_files)
        state.pr = get_pr(owner, repo, state.branch)
        return state

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
    state.commits = git(path, "log", "--oneline", "-n", "5").stdout.splitlines()
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


def worktree_fingerprint(state: RepoState) -> str:
    payload = ["\n".join(state.dirty_files)]
    payload.append(git(state.path, "diff", "--binary", "HEAD").stdout)
    for line in state.dirty_files:
        if not line.strip().startswith("??"):
            continue
        path = state.path / clean_status_path(line)
        if path.is_file():
            try:
                payload.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                payload.append(str(path.stat().st_size))
    return hashlib.sha256("\n".join(payload).encode("utf-8")).hexdigest()


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
                "head_sha": state.head_sha,
                "git_note": strip_ansi(state.note),
                "status_ok": state.status_ok,
                "dirty_files": state.dirty_files,
                "dirty_file_count": len(state.dirty_files),
                "dirty_status_hash": state.dirty_status_hash,
                "recent_commits": state.commits,
                "latest_activity": state.latest_activity,
                "next_action": state.next_action,
                "test_plan": state.test_plan,
                "queue_status": state.queue_status,
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


def is_cli_authenticated(cli_cmd: str, core_dir: Path) -> bool:
    if cli_cmd != "agy":
        return True

    cache_path = core_dir / "docs" / ".tmp" / "agy_auth_cache.json"
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            ts = cache.get("timestamp", 0)
            status = cache.get("authenticated", False)
            if time.time() - ts < 300:
                return status
        except Exception:
            pass

    status = False
    try:
        res = subprocess.run(
            ["agy", "models"],
            cwd="/tmp",
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=4.0,
        )
        if res.returncode == 0:
            status = True
        else:
            print(f"  [sync debug: agy models returned exit code {res.returncode}]", file=sys.stderr)
            if res.stderr:
                print(f"  [sync debug: stderr: {res.stderr.strip()}]", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("  [sync debug: agy models check timed out (4s)]", file=sys.stderr)
    except Exception as e:
        print(f"  [sync debug: agy models check failed: {type(e).__name__}: {e}]", file=sys.stderr)

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "timestamp": time.time(),
            "authenticated": status
        }), encoding="utf-8")
    except Exception:
        pass

    return status


def call_gemini_api_direct(prompt: str, model: str, api_key: str) -> str:
    import urllib.request
    import urllib.error
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except urllib.error.HTTPError as he:
        try:
            error_body = he.read().decode("utf-8")
            error_json = json.loads(error_body)
            error_msg = error_json.get("error", {}).get("message", str(he))
            raise RuntimeError(f"HTTP {he.code}: {error_msg}")
        except Exception:
            raise RuntimeError(f"HTTPError {he.code}: {he.reason}")
    except Exception as e:
        raise RuntimeError(f"{type(e).__name__}: {e}")
    return ""


def gemini_analysis(summary: list[dict[str, Any]], core_dir: Path) -> dict[str, dict[str, Any]]:
    if os.environ.get("SYNC_GEMINI", "1") == "0":
        return {}

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    use_direct_api = bool(api_key)

    cli_cmd = None
    if not use_direct_api:
        cli_cmd = "agy" if shutil_which("agy") else "gemini" if shutil_which("gemini") else None
        if not cli_cmd or not is_cli_authenticated(cli_cmd, core_dir):
            print(f"  [sync info: no GEMINI_API_KEY and CLI is unauthenticated; skipping API analysis]")
            return {}

    prompt = (
        "You are the TV7 architect planner. Analyze each repository from the provided JSON sync state.\n"
        "Return a JSON object keyed by repository. Each value must contain `summary` (an object) and `test_plan` (an object).\n"
        "The `summary` object must contain:\n"
        "  - `slice`: a short description of the active implementation slice currently in progress.\n"
        "  - `next_roadmap`: the title and ID of the next upcoming roadmap item for this repository.\n"
        "  - `pending_changes`: what changes are currently pending/uncommitted.\n"
        "  - `signals`: semantic indicators of what is done or needs hardening (e.g. existing endpoints, contracts).\n"
        "  - `next_action`: the precise next technical step.\n"
        "The `test_plan` object must contain: title, roadmap_items (array), where (screen/command), preconditions (array), "
        "steps (array), expected (array), and known_limitations (array). Test observable behavior from the actual changed code; "
        "include both the happy path and the nearest expected setup/failure path. "
        "When semantic signals show an implementation already exists, say to preserve/harden/validate it instead of rebuilding it. "
        "Keep the descriptions tight and professional. Avoid any markdown code block wrappers (like ```json) in your raw response, "
        "or if you do, ensure the response is still valid JSON after stripping them. "
        "Use ONLY the JSON structure provided. Do not invent any repositories.\n\n"
        + json.dumps(summary, indent=2)
    )

    env_model = os.environ.get("TV7_GEMINI_MODEL", "").strip()
    models = [env_model] if env_model else ["gemini-3.5-flash", "gemini-3.1-pro", "gemini-2.5-pro", "gemini-2.5-flash"]
    last_reason = "No models attempted"

    for model in models:
        try:
            start_time = time.time()
            if use_direct_api:
                content = call_gemini_api_direct(prompt, model, api_key)
                model_info = f"model: {model} (direct API)"
            else:
                if cli_cmd == "agy":
                    res = subprocess.run(
                        ["agy", "--model", model, "--print", prompt],
                        cwd="/tmp",
                        stdin=subprocess.DEVNULL,
                        capture_output=True,
                        text=True,
                        timeout=int(os.environ.get("SYNC_GEMINI_TIMEOUT", "25")),
                        check=False,
                    )
                else:
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
                    output = (res.stderr or res.stdout or "").lower()
                    if "subscription_required" in output or "valid license" in output:
                        last_reason = f"{model} license required (403)"
                    elif "permission_denied" in output or "forbidden" in output or "403" in output:
                        last_reason = f"{model} permission denied (403)"
                    elif any(marker in output for marker in ("capacity", "quota", "429", "rate limit")):
                        last_reason = f"{model} capacity/quota limit"
                    else:
                        last_reason = f"{model} CLI failed with exit code {res.returncode}"
                    continue

                if cli_cmd == "agy":
                    content = res.stdout.strip()
                    model_info = f"model: {model}"
                else:
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
                    content = envelope.get("response", "").strip()

            elapsed = time.time() - start_time
            print(f"  [gemini metrics: {model_info}, time: {elapsed:.1f}s]")

            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            parsed_dict = json.loads(content)
            if isinstance(parsed_dict, dict):
                analysis: dict[str, dict[str, Any]] = {}
                for key, value in parsed_dict.items():
                    if isinstance(value, dict):
                        analysis[str(key)] = value
                    else:
                        analysis[str(key)] = {"summary": str(value)}
                return analysis
        except Exception as exc:
            last_reason = f"{model} analysis failed ({type(exc).__name__}: {exc})"
            continue

    print(f"  [warn] Gemini analysis unavailable: {last_reason}; using local sync analysis", file=sys.stderr)
    return {}


def valid_test_plan(value: Any) -> bool:
    if not isinstance(value, dict) or not str(value.get("where", "")).strip():
        return False
    return all(isinstance(value.get(key), list) for key in ("preconditions", "steps", "expected", "known_limitations"))


def get_fallback_focus(state: RepoState) -> str:
    open_items = [item for item in state.roadmap_items if not item.done]
    next_item = open_items[0] if open_items else None

    lines = []
    if state.matched_item:
        lines.append(f"Slice   : {state.matched_item.title} ({state.matched_item.item_id})")
    elif state.changes:
        inferred = infer_slice(state)
        lines.append(f"Slice   : {inferred} (dirty)")
    else:
        lines.append("Slice   : Clean/Idle")

    if next_item:
        lines.append(f"Roadmap : {next_item.title} ({next_item.item_id})")
    else:
        lines.append("Roadmap : none")

    pending = []
    if state.changes:
        pending.append(f"{state.changes} pending changes")
    if state.dirty_files:
        untracked = sum(1 for f in state.dirty_files if f.strip().startswith("??"))
        if untracked:
            pending.append(f"including {untracked} untracked files")
    if pending:
        lines.append(f"Changes : {'; '.join(pending)}")

    return "\n    ".join(lines)


def clean_status_path(line: str) -> str:
    return line[3:] if len(line) > 3 else line.strip()


def check_mixed_dirty_slice(state: RepoState) -> str | None:
    if state.repo != "tv7-core" or not state.dirty_files:
        return None

    categories = set()
    for raw in state.dirty_files:
        path = clean_status_path(raw)
        if path.startswith("tooling/") or path in {"Makefile", "Makefile.core"}:
            categories.add("tooling")
        elif path.startswith("docs/contracts/"):
            categories.add("contracts")
        elif path.startswith("docs/handoffs/") or path.startswith("docs/code-reviews/"):
            categories.add("generated-docs")
        elif path.startswith("docs/roadmaps/") or path in {"README.md", "IDEA.md"}:
            categories.add("roadmaps")
        else:
            categories.add("other")

    if len(categories) > 1:
        return f"Warning: Mixed dirty slice! Found changes in multiple categories: {', '.join(sorted(categories))}."
    return None


def infer_slice(state: RepoState) -> str:
    dirty_text = "\n".join(state.dirty_files).lower()
    commit_text = "\n".join(state.commits).lower()
    haystack = "\n".join([state.repo, state.branch, dirty_text, commit_text]).lower()
    if state.repo == "tv7-engine" and any(
        file_contains(state.path / clean_status_path(line), marker)
        for line in state.dirty_files
        for marker in ("transcript_generate", "/v1/transcripts/generate", "TRANSCRIPTION_SETUP_REQUIRED")
    ):
        return "Engine transcript generation contract"
    if state.repo == "tv7-studio" and (
        "quick_clip" in haystack
        or "dashboard" in dirty_text
        or "diagnostics" in dirty_text
        or "engine_client" in dirty_text
    ):
        return "Studio Quick Clip and diagnostics integration"
    if state.repo == "tv7-backend" and ("cloud_ai" in haystack or "cloud-ai" in haystack):
        return "Backend cloud AI control plane"
    if "review.py" in haystack or "ready.py" in haystack or "sync.py" in haystack or "handoff" in haystack:
        return "Core cockpit and handoff tooling"
    if "site" in haystack or "astro" in haystack or "component" in haystack:
        return "Site component and content polish"
    if state.focus:
        return state.focus.title
    return "Repository implementation slice"


def dirty_groups(state: RepoState) -> list[str]:
    counts: dict[str, int] = {}
    for line in state.dirty_files:
        path = clean_status_path(line)
        if "/" in path:
            group = path.split("/", 1)[0]
        elif path in {"Makefile", "README.md", "Cargo.toml", "Cargo.lock", "pyproject.toml", "package.json"}:
            group = "root"
        else:
            group = "misc"
        counts[group] = counts.get(group, 0) + 1
    return [f"{name}({count})" for name, count in sorted(counts.items())]


def build_latest_activity(state: RepoState) -> list[str]:
    items: list[str] = []
    if state.changes:
        groups = ", ".join(dirty_groups(state))
        detail = f"Dirty slice: {infer_slice(state)} ({state.changes} files"
        if groups:
            detail += f"; {groups}"
        detail += ")"
        items.append(detail)
    if state.ahead:
        items.append(f"Local branch has {state.ahead} unpushed commit(s)")
    if state.pr and "note" not in state.pr:
        review = state.pr.get("reviewDecision") or "review pending"
        items.append(f"PR #{state.pr.get('number')} is {str(state.pr.get('state', '')).upper()} ({review})")
    for commit in state.commits[:5]:
        items.append(f"Commit: {commit}")
    return items[:5]


def build_next_action(state: RepoState) -> str:
    return action_profile(state)["command"]


def action_profile(state: RepoState) -> dict[str, Any]:
    """Classify the next operational action for the sync cockpit."""
    if not state.exists:
        return {
            "state": "missing",
            "label": "Fix checkout",
            "why": state.note,
            "command": "fix missing checkout",
            "priority": 10,
        }
    if not state.status_ok and not state.note.startswith("remote fetch unavailable"):
        return {
            "state": "sync-blocked",
            "label": "Resolve sync failure",
            "why": state.note,
            "command": "resolve sync/rebase failure",
            "priority": 20,
        }
    if state.pr and "note" not in state.pr:
        decision = str(state.pr.get("reviewDecision") or "").upper()
        ds_review = get_latest_deepseek_review(state.pr)
        if ds_review:
            ds_verdict = ds_review["verdict"]
            if ds_verdict == "APPROVED":
                decision = "APPROVED"
            elif ds_verdict == "REJECTED":
                decision = "CHANGES_REQUESTED"
        number = state.pr.get("number")
        if decision == "CHANGES_REQUESTED":
            return {
                "state": "pr-changes-requested",
                "label": "Resolve PR review",
                "why": f"PR #{number} has requested changes; run one review-resolution round, then inspect DeepSeek.",
                "command": f"make review REPO={state.repo} REVIEW_AUTO_ROUND=1 REVIEW_HUMAN_DECISION=1",
                "priority": 30,
            }
        if decision in {"REVIEW_REQUIRED", ""}:
            return {
                "state": "pr-awaiting-review",
                "label": "Check PR review",
                "why": f"PR #{number} is open and waiting on review/checks.",
                "command": f"make review REPO={state.repo} REVIEW_AUTO_ROUND=1 REVIEW_HUMAN_DECISION=1",
                "priority": 40,
            }
        return {
            "state": "pr-ready",
            "label": "Review merge decision",
            "why": f"PR #{number} is {decision.lower().replace('_', ' ')}; inspect the full review before merge/delete.",
            "command": f"make review REPO={state.repo} REVIEW_HUMAN_DECISION=1",
            "priority": 50,
        }
    if state.ahead:
        return {
            "state": "ahead-needs-review",
            "label": "Create/update PR",
            "why": f"{state.ahead} local commit(s) are ready for review.",
            "command": f"make review REPO={state.repo}",
            "priority": 60,
        }
    if state.changes:
        if state.queue_status == "passed":
            return {
                "state": "validated-needs-commit",
                "label": "Commit validated slice",
                "why": "Human validation already passed for this dirty slice.",
                "command": "commit validated slice from make sync",
                "priority": 70,
            }
        if state.queue_status == "failed":
            return {
                "state": "validation-failed",
                "label": "Return failure to agent",
                "why": "Human validation failed; repo agent needs the failure context before another ready check.",
                "command": "send failure context to the active agent, then rerun make sync",
                "priority": 80,
            }
        return {
            "state": "dirty-needs-ready",
            "label": "Ready dirty slice",
            "why": f"{state.changes} pending file change(s) need validation and handoff refresh before commit.",
            "command": f"make ready REPO={state.repo}",
            "priority": 90,
        }
    if state.focus:
        return {
            "state": "clean-needs-agent-work",
            "label": "Prompt agent work",
            "why": f"Clean repo; next roadmap item is {state.focus.item_id}.",
            "command": f"start {state.focus.item_id}",
            "priority": 120,
        }
    return {
        "state": "idle",
        "label": "No action",
        "why": "No local changes, open PRs, or open roadmap items were detected.",
        "command": "no action",
        "priority": 999,
    }


def queue_path(core_dir: Path) -> Path:
    return core_dir / "docs" / ".tmp" / "sync-review-queue.json"


def load_queue(core_dir: Path) -> dict[str, dict[str, Any]]:
    path = queue_path(core_dir)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def save_queue(core_dir: Path, queue: dict[str, dict[str, Any]]) -> None:
    path = queue_path(core_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reconcile_queue(states: list[RepoState], queue: dict[str, dict[str, Any]]) -> None:
    for state in states:
        if not state.exists:
            continue
        entry = queue.get(state.repo, {})
        if not entry:
            continue
        current_head = git(state.path, "rev-parse", "HEAD").stdout.strip()
        current_hash = worktree_fingerprint(state)
        stale = bool(entry) and (
            entry.get("head_sha") != current_head or entry.get("dirty_status_hash") != current_hash
        )
        if stale:
            entry = {
                **entry,
                "status": "pending",
                "head_sha": current_head,
                "dirty_status_hash": current_hash,
                "invalidated_at": datetime.now(timezone.utc).isoformat(),
                "invalidated_reason": "HEAD or dirty file set changed",
                "is_stale": True,
            }
            queue[state.repo] = entry
        else:
            entry["is_stale"] = entry.get("is_stale", False)

        if entry:
            entry["slice"] = infer_slice(state)
            entry["test_plan"] = state.test_plan
            entry["roadmap_items"] = state.test_plan.get("roadmap_items", [])
            queue[state.repo] = entry
        state.queue_status = str(entry.get("status", ""))


def get_check_command(core_dir: Path, repo: str) -> str:
    conf_path = core_dir / "tooling" / "repos-checks.conf"
    if not conf_path.exists():
        return ""
    for line in conf_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if parts and parts[0] == repo and len(parts) >= 3:
            return parts[2]
    return ""


def update_queue_entry(
    core_dir: Path,
    queue: dict[str, dict[str, Any]],
    state: RepoState,
    *,
    status: str,
    note: str = "",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    check_cmd = get_check_command(core_dir, state.repo)
    cmd_str = f"make ready REPO={state.repo}"
    if check_cmd:
        cmd_str += f" (runs: {check_cmd})"

    entry = {
        **queue.get(state.repo, {}),
        "repo": state.repo,
        "slice": infer_slice(state),
        "roadmap_items": state.test_plan.get("roadmap_items", []),
        "head_sha": git(state.path, "rev-parse", "HEAD").stdout.strip(),
        "dirty_status_hash": worktree_fingerprint(state),
        "dirty_files": state.dirty_files,
        "test_plan": state.test_plan,
        "status": status,
        "updated_at": now,
        "last_validation_command": cmd_str,
        "is_stale": False,
    }
    if note:
        entry["note"] = note
    elif status != "failed":
        entry.pop("note", None)
    if status in {"passed", "failed"}:
        entry[f"{status}_at"] = now
    queue[state.repo] = entry
    state.queue_status = status
    save_queue(core_dir, queue)


def print_failure_prompt(state: RepoState, note: str) -> None:
    print("\nCopy/paste prompt for the active agent:")
    print("---")
    print(f"Work in {state.repo}. Do not push.")
    print(f"The human validation for `{infer_slice(state)}` failed.")
    if note:
        print(f"Human note: {note}")
    print("Reproduce the failed workflow using the active handoff Human Validation section, inspect the supplied logs, fix only this slice, run repo validation, and report what changed plus what the human should retest.")
    print("---")


def commit_validated_slice(core_dir: Path, state: RepoState, queue: dict[str, dict[str, Any]]) -> int:
    title = f"{state.repo}: {infer_slice(state)[:1].lower()}{infer_slice(state)[1:]}"
    print("\nCommit scope:")
    for line in state.dirty_files:
        print(f"  {line}")
    print(f"Commit message: {title}")
    choice = input("Commit this validated slice? [y/N]: ").strip().lower()
    if choice not in {"y", "yes"}:
        print("Commit deferred. The passing test result remains in the local queue.")
        return 0
    added = git(state.path, "add", "-A")
    if added.returncode != 0:
        print(added.stderr.strip() or "git add failed", file=sys.stderr)
        return added.returncode
    committed = git(state.path, "commit", "-m", title)
    if committed.returncode != 0:
        print(committed.stderr.strip() or committed.stdout.strip() or "git commit failed", file=sys.stderr)
        return committed.returncode
    state.dirty_files = git(state.path, "status", "--porcelain").stdout.splitlines()
    state.changes = len(state.dirty_files)
    update_queue_entry(core_dir, queue, state, status="committed")
    print(f"Committed {state.repo}.")
    print("\nReview flow:")
    print("  1) Run one automated review round, then show DeepSeek review for human merge/round decision")
    print("  2) Create/update PR and stop after collecting DeepSeek review")
    print("  3) Skip review for now")
    review_choice = input("Select review option [1-3, default: 1]: ").strip() or "1"
    if review_choice == "3":
        print(f"Review skipped. Next: make review REPO={state.repo}")
        return 0
    if review_choice not in {"1", "2"}:
        print("Invalid review option; review skipped.", file=sys.stderr)
        return 2
    print(f"Starting make review for {state.repo}...")
    roadmap_items = state.test_plan.get("roadmap_items", [])
    primary_roadmap_item = str(roadmap_items[0]) if roadmap_items else ""
    command = [
        "make",
        "review",
        f"REPO={state.repo}",
        f"ROADMAP_ITEM={primary_roadmap_item}",
    ]
    if review_choice == "1":
        command.extend([
            "REVIEW_MAX_ROUNDS=1",
            "REVIEW_AUTO_ROUND=1",
            "REVIEW_HUMAN_DECISION=1",
            "REVIEW_AUTOMERGE=0",
            "REVIEW_AUTOMERGE_THRESHOLD=90",
        ])
    else:
        command.extend([
            "REVIEW_RESOLVE=0",
            "REVIEW_AUTOMERGE=0",
        ])
    rc = subprocess.run(command, cwd=str(core_dir), env=os.environ.copy()).returncode
    if rc == 0:
        print("\nReview action complete. Refreshing the sync cockpit.")
        return REFRESH_COCKPIT
    return rc


def execute_repo_action(
    core_dir: Path,
    state: RepoState,
    queue: dict[str, dict[str, Any]],
) -> int:
    action = action_profile(state)
    if action["state"].startswith("pr-") or action["state"] == "ahead-needs-review":
        print(f"Running review flow for {state.repo}: {action['why']}")
        rc = subprocess.run(
            [
                "make",
                "review",
                f"REPO={state.repo}",
                "REVIEW_MAX_ROUNDS=1",
                "REVIEW_AUTO_ROUND=1",
                "REVIEW_HUMAN_DECISION=1",
                "REVIEW_AUTOMERGE=0",
            ],
            cwd=str(core_dir),
            env=os.environ.copy(),
        ).returncode
        return REFRESH_COCKPIT if rc == 0 else rc

    if action["state"] == "sync-blocked":
        print(f"\n{RED}Sync failure detected on {state.repo}: {action['why']}{RESET}")
        print("How would you like to resolve this?")
        print("  1) Run git rebase --abort && git reset --hard @{u} (Resets local branch to match remote upstream)")
        print("  2) Run git rebase --skip")
        print("  3) Return to cockpit (resolve manually in terminal)")
        choice = input("Select option [1-3, default: 3]: ").strip() or "3"
        if choice == "1":
            print("Aborting rebase and resetting branch to upstream...")
            git(state.path, "rebase", "--abort")
            rc = git(state.path, "reset", "--hard", state.upstream or "origin/main").returncode
            input("\nPress Enter to return to cockpit...")
            return REFRESH_COCKPIT if rc == 0 else rc
        if choice == "2":
            print("Skipping conflicting commit(s)...")
            rc = git(state.path, "rebase", "--skip").returncode
            input("\nPress Enter to return to cockpit...")
            return REFRESH_COCKPIT if rc == 0 else rc
        return REFRESH_COCKPIT

    if action["state"] == "missing":
        print(f"Missing checkout: {action['why']}")
        return 0

    if action["state"] == "clean-needs-agent-work":
        print(f"Starting work for {state.repo} on {state.focus.item_id}...")
        rc = subprocess.run(action["command"], shell=True, cwd=str(core_dir)).returncode
        input("\nPress Enter to return to cockpit...")
        return REFRESH_COCKPIT if rc == 0 else rc

    if state.queue_status == "passed":
        print("The current worktree already has a passing human validation result.")
        return commit_validated_slice(core_dir, state, queue)

    ready = subprocess.run(["make", "ready", f"REPO={state.repo}"], cwd=str(core_dir))
    if ready.returncode != 0:
        update_queue_entry(core_dir, queue, state, status="pending", note="make ready failed")
        return ready.returncode

    if state.repo in {"tv7-engine", "tv7-studio", "tv7-backend"}:
        subprocess.run(
            ["make", "handoff", f"HANDOFF_REPO={state.repo}"],
            cwd=str(core_dir),
            check=False,
        )

    update_queue_entry(core_dir, queue, state, status="pending")
    print(f"\nHuman validation: {infer_slice(state)}")
    print(terminal_test_plan(state.test_plan))
    print("\nResult:")
    print("  1) Pass")
    print("  2) Fail")
    print("  3) Exit and resume later")
    result = input("Select result [1-3]: ").strip()
    if result == "2":
        note = input("Optional failure note (Enter to skip): ").strip()
        update_queue_entry(core_dir, queue, state, status="failed", note=note)
        print_failure_prompt(state, note)
        return 0
    if result == "3" or not result:
        print("Human validation remains pending. Run make sync to resume later.")
        return 0
    if result != "1":
        print("Invalid result; validation remains pending.", file=sys.stderr)
        return 2

    update_queue_entry(core_dir, queue, state, status="passed")
    print("Human validation passed.")
    return commit_validated_slice(core_dir, state, queue)


def process_validation_queue(
    core_dir: Path,
    states: list[RepoState],
    queue: dict[str, dict[str, Any]],
) -> int:
    repo_priority = {repo: index for index, repo in enumerate(
        ["tv7-engine", "tv7-studio", "tv7-backend", "tv7-core", "tv7-conductor", "tv7-site"]
    )}
    candidates = sorted(
        [
            state
            for state in states
            if state.exists and action_profile(state)["state"] not in {"idle", "clean-needs-agent-work"}
        ],
        key=lambda state: (action_profile(state)["priority"], repo_priority.get(state.repo, 99)),
    )
    if not candidates:
        print("No repository actions are waiting in the sync queue.")
        return 0
    print("\nWorkspace action queue:")
    for index, state in enumerate(candidates, 1):
        status = state.queue_status or "pending"
        action = action_profile(state)
        print(f"  {index}) {state.repo}: {action['label']} [{status}]")
        print(f"      {action['why']}")
    raw = input(f"Select repository [1-{len(candidates)}] or Enter to exit: ").strip()
    if not raw:
        return 0
    if not raw.isdigit() or not 1 <= int(raw) <= len(candidates):
        print("Invalid selection.", file=sys.stderr)
        return 2
    state = candidates[int(raw) - 1]
    return execute_repo_action(core_dir, state, queue)


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, dict):
        if "title" in val or "id" in val:
            title = val.get("title") or ""
            item_id = val.get("id") or val.get("item_id") or ""
            if title and item_id:
                return f"{title} ({item_id})"
            return str(title or item_id)
        return json.dumps(val)
    return str(val).strip()


def format_focus(focus: Any) -> str:
    if isinstance(focus, dict):
        slice_val = _safe_str(focus.get("slice", ""))
        roadmap_val = _safe_str(focus.get("next_roadmap", ""))
        changes_val = _safe_str(focus.get("pending_changes", ""))
        signals_val = _safe_str(focus.get("signals", ""))
        next_val = _safe_str(focus.get("next_action", ""))

        lines = []
        if slice_val:
            lines.append(f"    {CYAN}Slice{RESET}   : {slice_val}")
        if roadmap_val:
            lines.append(f"    {CYAN}Roadmap{RESET} : {roadmap_val}")
        if changes_val:
            lines.append(f"    {YELLOW}Changes{RESET} : {changes_val}")
        if signals_val:
            lines.append(f"    {GREEN}Signals{RESET} : {signals_val}")
        if next_val:
            lines.append(f"    {GREEN}Next{RESET}    : {next_val}")
        return "\n".join(lines)

    focus_str = str(focus).strip()
    if focus_str.startswith("{"):
        try:
            parsed = json.loads(focus_str)
            if isinstance(parsed, dict):
                return format_focus(parsed)
        except Exception:
            pass

    return "\n".join(f"    {line}" for line in focus_str.splitlines())


def format_focus_markdown(focus: Any) -> str:
    if isinstance(focus, dict):
        slice_val = _safe_str(focus.get("slice", ""))
        roadmap_val = _safe_str(focus.get("next_roadmap", ""))
        changes_val = _safe_str(focus.get("pending_changes", ""))
        signals_val = _safe_str(focus.get("signals", ""))
        next_val = _safe_str(focus.get("next_action", ""))

        lines = []
        if slice_val:
            lines.append(f"  - **Slice**: {slice_val}")
        if roadmap_val:
            lines.append(f"  - **Roadmap**: {roadmap_val}")
        if changes_val:
            lines.append(f"  - **Changes**: {changes_val}")
        if signals_val:
            lines.append(f"  - **Signals**: {signals_val}")
        if next_val:
            lines.append(f"  - **Next**: {next_val}")
        return "\n".join(lines)

    focus_str = str(focus).strip()
    if focus_str.startswith("{"):
        try:
            parsed = json.loads(focus_str)
            if isinstance(parsed, dict):
                return format_focus_markdown(parsed)
        except Exception:
            pass

    return "\n".join(f"  {line}" for line in focus_str.splitlines())


def print_action_plan(states: list[RepoState], focus_map: dict[str, Any]) -> None:
    print(f"{GREEN}📋 Workspace Action Plan:{RESET}")
    has_actions = False
    idx = 1
    for state in sorted(states, key=lambda item: action_profile(item)["priority"]):
        if not state.exists:
            continue
        action = action_profile(state)

        focus = focus_map.get(state.repo)
        action_desc = ""
        if isinstance(focus, dict):
            action_desc = focus.get("next_action", "").strip()
        elif focus:
            focus_str = str(focus).strip()
            if focus_str.startswith("{"):
                try:
                    parsed = json.loads(focus_str)
                    if isinstance(parsed, dict):
                        action_desc = parsed.get("next_action", "").strip()
                except Exception:
                    pass

        if not action_desc:
            action_desc = action["label"]

        cmd_action = action["command"]
        if cmd_action and cmd_action != "no action":
            cmd_str = f" ({YELLOW}{cmd_action}{RESET})"
        else:
            cmd_str = ""

        print(f"  {idx}. {CYAN}{state.repo:<15}{RESET} [{action['label']}] ➜ {action_desc}{cmd_str}")
        print(f"      why: {action['why']}")
        has_actions = True
        idx += 1

    if not has_actions:
        print("  No pending actions across workspace.")
    print()


def print_repo_status(states: list[RepoState], focus_map: dict[str, Any]) -> None:
    core_dir = Path(__file__).resolve().parents[1]
    queue = load_queue(core_dir)
    for state in states:
        if state.status_ok:
            mark = f"{GREEN}[✓]{RESET}"
        elif state.note.startswith("remote fetch unavailable"):
            mark = f"{YELLOW}[!]{RESET}"
        else:
            mark = f"{RED}[X]{RESET}"
        if not state.exists:
            print(f"{mark} {state.repo} - {state.note}")
            continue
        pr_note = "PR: none"
        if state.pr:
            if "note" in state.pr:
                pr_note = f"PR: {state.pr['note']}"
            else:
                ds_review = get_latest_deepseek_review(state.pr)
                ds_str = ""
                if ds_review:
                    conf = f" ({ds_review['confidence']})" if ds_review['confidence'] is not None else ""
                    ds_str = f" [DeepSeek: {ds_review['verdict']}{conf}]"
                pr_note = f"PR: #{state.pr.get('number')} {str(state.pr.get('state', '')).upper()} {state.pr.get('url', '')}{ds_str}"

        total = len(state.roadmap_items)
        done = sum(1 for item in state.roadmap_items if item.done)
        pct = (done / total * 100.0) if total > 0 else 0.0
        metric_str = f" [Roadmap: {done}/{total} done ({pct:.1f}%)]"

        print(f"{mark} {state.repo} ({CYAN}{state.branch}{RESET}) - {state.note} - {pr_note}{metric_str}")

        mixed_warn = check_mixed_dirty_slice(state)
        if mixed_warn:
            print(f"    {YELLOW}⚠️  {mixed_warn}{RESET}")

        focus_desc = focus_map.get(state.repo, "")
        if not focus_desc:
            focus_desc = get_fallback_focus(state)
        print(format_focus(focus_desc))

        if state.latest_activity:
            print("    Last 5:")
            for item in state.latest_activity:
                print(f"      - {item}")

        entry = queue.get(state.repo)
        if entry and entry.get("status") in {"passed", "failed"}:
            cmd = entry.get("last_validation_command", f"make ready REPO={state.repo}")
            res = entry.get("status")
            ts = entry.get("updated_at")
            is_stale = entry.get("is_stale", False)
            stale_str = f" ({RED}stale - HEAD/dirty state changed afterward{RESET})" if is_stale else f" ({GREEN}fresh{RESET})"
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                ts_str = ts
            print(f"    {CYAN}Validation{RESET}: cmd: `{cmd}`, result: {res}, at: {ts_str}{stale_str}")

        if state.next_action:
            action = action_profile(state)
            print(f"    Action: {action['label']} ({action['state']})")
            print(f"    Why: {action['why']}")
            print(f"    Next: {action['command']}")


def write_artifacts(core_dir: Path, states: list[RepoState], focus_map: dict[str, Any], global_metric: str) -> None:
    queue = load_queue(core_dir)
    out_dir = core_dir / "docs" / ".tmp"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = repo_summary_for_gemini(states)
    generated_at = datetime.now(timezone.utc).isoformat()
    state_by_repo = {state.repo: state for state in states}
    for item in summary:
        repo = item["repo"]
        state = state_by_repo.get(repo)
        focus_desc = focus_map.get(repo, "")
        if isinstance(focus_desc, str):
            focus_desc = focus_desc.strip()
        if not focus_desc:
            focus_desc = get_fallback_focus(state)
        item["resolved_focus"] = focus_desc
        if state:
            item["latest_activity"] = state.latest_activity
            item["next_action"] = state.next_action
            item["action"] = action_profile(state)
        item["sync_generated_at"] = generated_at

    (out_dir / "sync-roadmap-focus.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    md_lines = ["# TV7 Sync Cockpit", f"**{global_metric}**\n"]

    md_lines.append("## 📋 Workspace Action Plan")
    idx = 1
    for state in sorted(states, key=lambda item: action_profile(item)["priority"]):
        if not state.exists:
            continue
        action = action_profile(state)
        focus = focus_map.get(state.repo)
        action_desc = ""
        if isinstance(focus, dict):
            action_desc = focus.get("next_action", "").strip()
        elif focus:
            focus_str = str(focus).strip()
            if focus_str.startswith("{"):
                try:
                    parsed = json.loads(focus_str)
                    if isinstance(parsed, dict):
                        action_desc = parsed.get("next_action", "").strip()
                except Exception:
                    pass
        if not action_desc:
            action_desc = action["label"]

        cmd_action = action["command"]
        if cmd_action and cmd_action != "no action":
            cmd_str = f" (`{cmd_action}`)"
        else:
            cmd_str = ""
        md_lines.append(f"{idx}. **{state.repo}** [{action['label']}] ➜ {action_desc}{cmd_str}")
        md_lines.append(f"   - Why: {action['why']}")
        idx += 1
    md_lines.append("")

    md_lines.append("## 📁 Repository Details")
    for state in states:
        mark = "[✓]" if state.status_ok else "[!]" if state.note.startswith("remote fetch unavailable") else "[X]"
        if not state.exists:
            md_lines.append(f"- **{mark} {state.repo}** - {state.note}")
            continue
        pr_note = "PR: none"
        if state.pr:
            if "note" in state.pr:
                pr_note = f"PR: {state.pr['note']}"
            else:
                ds_review = get_latest_deepseek_review(state.pr)
                ds_str = ""
                if ds_review:
                    conf = f" ({ds_review['confidence']})" if ds_review['confidence'] is not None else ""
                    ds_str = f" [DeepSeek: {ds_review['verdict']}{conf}]"
                pr_note = f"PR: #{state.pr.get('number')} {str(state.pr.get('state', '')).upper()} {state.pr.get('url', '')}{ds_str}"

        total = len(state.roadmap_items)
        done = sum(1 for item in state.roadmap_items if item.done)
        pct = (done / total * 100.0) if total > 0 else 0.0
        metric_str = f" [Roadmap: {done}/{total} done ({pct:.1f}%)]"

        md_lines.append(f"- **{mark} {state.repo} ({state.branch})** - {state.note} - {pr_note}{metric_str}")

        mixed_warn = check_mixed_dirty_slice(state)
        if mixed_warn:
            md_lines.append(f"  - **⚠️ {mixed_warn}**")

        focus_desc = focus_map.get(state.repo, "")
        if not focus_desc:
            focus_desc = get_fallback_focus(state)
        md_lines.append(format_focus_markdown(focus_desc))
        if state.latest_activity:
            md_lines.append("  Last 5:")
            for item in state.latest_activity:
                md_lines.append(f"  - {item}")

        entry = queue.get(state.repo)
        if entry and entry.get("status") in {"passed", "failed"}:
            cmd = entry.get("last_validation_command", f"make ready REPO={state.repo}")
            res = entry.get("status")
            ts = entry.get("updated_at")
            is_stale = entry.get("is_stale", False)
            stale_str = " (stale - HEAD/dirty state changed afterward)" if is_stale else " (fresh)"
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ts_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                ts_str = ts
            md_lines.append(f"  - **Validation**: cmd: `{cmd}`, result: {res}, at: {ts_str}{stale_str}")
        if state.next_action:
            action = action_profile(state)
            md_lines.append(f"  - **Action**: {action['label']} (`{action['state']}`)")
            md_lines.append(f"  - **Why**: {action['why']}")
            md_lines.append(f"  - **Next**: `{action['command']}`")

    (out_dir / "sync-roadmap-focus.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def interactive_actions(
    core_dir: Path,
    states: list[RepoState],
    queue: dict[str, dict[str, Any]],
) -> int:
    if os.environ.get("SYNC_INTERACTIVE", "1") == "0" or not sys.stdin.isatty():
        return 0
    candidates = [state for state in states if state.exists and (state.changes or state.ahead or state.branch != "main" or state.pr)]

    priority_candidate = None
    priority_action = None
    repo_priority = {repo: index for index, repo in enumerate(
        ["tv7-engine", "tv7-studio", "tv7-backend", "tv7-core", "tv7-conductor", "tv7-site"]
    )}
    sorted_states = sorted(
        [state for state in states if state.exists],
        key=lambda item: (action_profile(item)["priority"], repo_priority.get(item.repo, 99))
    )
    for state in sorted_states:
        act = action_profile(state)
        if act["state"] != "idle":
            priority_candidate = state
            priority_action = act
            break

    print("\nActions:")
    menu_idx = 1
    execute_idx = None
    if priority_candidate:
        execute_idx = menu_idx
        print(f"  {menu_idx}) Execute priority planned action: {priority_candidate.repo} ({priority_action['label']}) (runs: {priority_action['command']})")
        menu_idx += 1

    queue_idx = menu_idx
    print(f"  {menu_idx}) Process validation/review queue   (runs: make ready / make review)")
    menu_idx += 1

    git_idx = menu_idx
    print(f"  {menu_idx}) Operate a repo branch/PR          (runs: make git-dev)")
    menu_idx += 1

    conductor_idx = menu_idx
    print(f"  {menu_idx}) Conductor status and operations   (runs: make conductor-status / run-once / events)")
    menu_idx += 1

    handoff_idx = menu_idx
    print(f"  {menu_idx}) Generate agent handoffs           (runs: make handoff)")
    menu_idx += 1

    prompts_idx = menu_idx
    print(f"  {menu_idx}) Print agent prompts               (runs: make handoff HANDOFF_PROMPTS_ONLY=1)")
    menu_idx += 1

    exit_idx = menu_idx
    print(f"  {menu_idx}) Exit")

    choice = input(f"Select action [1-{menu_idx}, default: {exit_idx}]: ").strip() or str(exit_idx)

    if execute_idx and choice == str(execute_idx):
        return execute_repo_action(core_dir, priority_candidate, queue)
    if choice == str(queue_idx):
        return process_validation_queue(core_dir, states, queue)
    if choice == str(conductor_idx):
        print(f"\n{CYAN}=== Conductor Control Center ==={RESET}")
        print("  1) Check Conductor status            (runs: make conductor-status)")
        print("  2) Run Conductor loop once           (runs: make conductor-run-once)")
        print("  3) Show Conductor events             (runs: make conductor-events)")
        print("  4) Return to main menu")
        sub_choice = input("Select conductor option [1-4, default: 4]: ").strip() or "4"
        if sub_choice == "1":
            subprocess.run(["make", "conductor-status"], cwd=str(core_dir))
            input("\nPress Enter to return to cockpit...")
            return REFRESH_COCKPIT
        elif sub_choice == "2":
            subprocess.run(["make", "conductor-run-once"], cwd=str(core_dir))
            input("\nPress Enter to return to cockpit...")
            return REFRESH_COCKPIT
        elif sub_choice == "3":
            subprocess.run(["make", "conductor-events"], cwd=str(core_dir))
            input("\nPress Enter to return to cockpit...")
            return REFRESH_COCKPIT
        return REFRESH_COCKPIT
    if choice == str(handoff_idx):
        return print_cmd(["python3", str(core_dir / "tooling" / "handoff.py")], cwd=core_dir)
    if choice == str(prompts_idx):
        env = os.environ.copy()
        env["HANDOFF_PROMPTS_ONLY"] = "1"
        return subprocess.run(["python3", str(core_dir / "tooling" / "handoff.py")], cwd=str(core_dir), env=env).returncode
    if choice == str(git_idx):
        if candidates:
            print("Likely repos needing attention:")
            for state in candidates:
                pr = state.pr.get("url", "") if state.pr else ""
                print(f"  - {state.repo} ({state.branch}) {pr}")
        return print_cmd(["bash", str(core_dir / "tooling" / "git-dev.sh")], cwd=core_dir)
    return 0


def rerun_sync(core_dir: Path) -> int:
    env = os.environ.copy()
    env["SYNC_INTERACTIVE"] = "1"
    return subprocess.run([sys.executable, str(core_dir / "tooling" / "sync.py")], cwd=str(core_dir), env=env).returncode


def load_previous_sync_data(core_dir: Path) -> dict[str, dict[str, Any]]:
    json_path = core_dir / "docs" / ".tmp" / "sync-roadmap-focus.json"
    if not json_path.exists():
        return {}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return {item["repo"]: item for item in data if isinstance(item, dict) and "repo" in item}
    except Exception:
        return {}


def is_repo_unchanged(state: RepoState, prev_item: dict[str, Any] | None) -> bool:
    if not prev_item:
        return False
    # If the previous run failed to generate resolved_focus, we must refresh
    if not prev_item.get("resolved_focus"):
        return False
    # If there are local uncommitted changes or ahead commits, it has changed
    if state.changes > 0 or state.ahead > 0:
        return False
    # If it is on a feature branch (not main), it is actively in development
    if state.branch not in {"main", "HEAD", "-"}:
        return False
    # If the branch name changed
    if state.branch != prev_item.get("branch"):
        return False
    if not state.head_sha or state.head_sha != prev_item.get("head_sha"):
        return False
    if state.dirty_status_hash != prev_item.get("dirty_status_hash"):
        return False
    if not state.status_ok or prev_item.get("status_ok", True) is not True:
        return False
    # If the git status was not clean in the previous run
    prev_git_note = prev_item.get("git_note", "").lower()
    if "pending" in prev_git_note or "ahead" in prev_git_note:
        return False
    # Check PR status match
    prev_pr = prev_item.get("pr")
    if (state.pr is None) != (prev_pr is None):
        return False
    if state.pr and prev_pr:
        if state.pr.get("number") != prev_pr.get("number") or state.pr.get("state") != prev_pr.get("state"):
            return False
    # Check roadmap metrics match
    total = len(state.roadmap_items)
    done = sum(1 for item in state.roadmap_items if item.done)
    if done != prev_item.get("completed_count") or (total - done) != (prev_item.get("open_required_count", 0) + prev_item.get("open_other_count", 0)):
        return False
    # If all these match, the repository state is unchanged and clean
    return True


def deterministic_pending_changes(state: RepoState) -> str:
    if not state.status_ok:
        return strip_ansi(state.note) or "Repository synchronization failed; inspect Git state."
    if state.changes:
        return f"{state.changes} pending file change(s)."
    if state.ahead:
        return f"{state.ahead} local commit(s) ahead of the configured upstream."
    if state.pr:
        return f"No uncommitted changes; work is packaged in open PR #{state.pr.get('number')}."
    return "No pending changes (repository is clean)."


def sanitize_resolved_focus(state: RepoState, focus: Any) -> Any:
    if not isinstance(focus, dict):
        return focus

    sanitized = dict(focus)
    sanitized["pending_changes"] = deterministic_pending_changes(state)
    state_claim_pattern = re.compile(r"\b(conflicts?|rebase failed|unmerged|UU\s|dirty|pending changes?)\b", re.I)

    if state.status_ok and not state.changes:
        for key in ("signals", "next_action"):
            value = str(sanitized.get(key) or "")
            if state_claim_pattern.search(value):
                if key == "signals":
                    sanitized[key] = "Current Git worktree is clean; semantic implementation signals require direct code inspection."
                elif state.focus:
                    sanitized[key] = f"Start {state.focus.item_id}: {state.focus.title}"
                else:
                    sanitized[key] = "Inspect the clean repository and select the next roadmap slice."
    return sanitized


def main() -> int:
    init_colors()
    core_dir = Path(__file__).resolve().parents[1]
    workspace = Path(os.environ.get("REPO_ROOT", str(core_dir.parent))).resolve()
    owner = os.environ.get("OWNER", "TV7-Clip-Studio")
    repos = os.environ.get("REPOS", "tv7-core tv7-conductor tv7-engine tv7-backend tv7-studio tv7-site").split()
    sync_base = os.environ.get("SYNC_BASE", "origin/main")

    states = [sync_repo(repo, workspace / repo, owner, sync_base) for repo in repos]
    for state in states:
        state.head_sha = git(state.path, "rev-parse", "HEAD").stdout.strip() if state.exists else ""
        state.dirty_status_hash = status_hash(state.dirty_files)
        state.roadmap_items = collect_roadmap_items(state.repo, workspace)
        infer_focus(state)
        state.latest_activity = build_latest_activity(state)
        state.test_plan = build_test_plan(state.repo, infer_slice(state), item_to_dict(state.focus))

    # 1. Ask Gemini to refine summaries and human test plans; reuse cached data for unchanged repositories.
    prev_data = load_previous_sync_data(core_dir)
    focus_map: dict[str, Any] = {}
    states_to_analyze: list[RepoState] = []

    print("Checking repository cache status:")
    for state in states:
        prev_item = prev_data.get(state.repo)
        if is_repo_unchanged(state, prev_item):
            print(f"  - {state.repo}: cache hit (unchanged)")
            focus_map[state.repo] = sanitize_resolved_focus(state, prev_item.get("resolved_focus", ""))
            if prev_item and "test_plan" in prev_item:
                state.test_plan = prev_item["test_plan"]
        else:
            reason = "no previous cache"
            if prev_item:
                reasons = []
                if not prev_item.get("resolved_focus"): reasons.append("no cached focus")
                if state.changes > 0: reasons.append(f"{state.changes} changes")
                if state.ahead > 0: reasons.append(f"{state.ahead} ahead commits")
                if state.branch not in {"main", "HEAD", "-"}: reasons.append(f"branch {state.branch}")
                if state.branch != prev_item.get("branch"): reasons.append("branch changed")
                prev_git_note = prev_item.get("git_note", "").lower()
                if "pending" in prev_git_note or "ahead" in prev_git_note: reasons.append(f"previous run was dirty ({prev_git_note})")
                prev_pr = prev_item.get("pr")
                if (state.pr is None) != (prev_pr is None): reasons.append("PR presence changed")
                if state.pr and prev_pr:
                    if state.pr.get("number") != prev_pr.get("number") or state.pr.get("state") != prev_pr.get("state"):
                        reasons.append("PR details changed")
                total = len(state.roadmap_items)
                done = sum(1 for item in state.roadmap_items if item.done)
                if done != prev_item.get("completed_count") or (total - done) != (prev_item.get("open_required_count", 0) + prev_item.get("open_other_count", 0)):
                    reasons.append("roadmap progress changed")
                reason = ", ".join(reasons) if reasons else "state mismatched"
            print(f"  - {state.repo}: cache miss ({reason})")
            states_to_analyze.append(state)

    if states_to_analyze:
        summary_to_analyze = repo_summary_for_gemini(states_to_analyze)
        analysis_map = gemini_analysis(summary_to_analyze, core_dir)
        for state in states_to_analyze:
            analysis = analysis_map.get(state.repo, {})
            focus_map[state.repo] = sanitize_resolved_focus(state, analysis.get("summary", ""))
            candidate_plan = analysis.get("test_plan")
            if valid_test_plan(candidate_plan):
                fallback = state.test_plan
                state.test_plan = {
                    **fallback,
                    **candidate_plan,
                    "title": str(candidate_plan.get("title") or fallback.get("title") or infer_slice(state)),
                    "roadmap_items": candidate_plan.get("roadmap_items") or fallback.get("roadmap_items", []),
                }

    queue = load_queue(core_dir)
    reconcile_queue(states, queue)
    save_queue(core_dir, queue)
    for state in states:
        state.next_action = build_next_action(state)

    # 2. Compute global workspace metrics
    total_items = sum(len(state.roadmap_items) for state in states)
    total_done = sum(sum(1 for item in state.roadmap_items if item.done) for state in states)
    global_pct = (total_done / total_items * 100.0) if total_items > 0 else 0.0
    global_metric = f"Workspace Roadmap: {total_done}/{total_items} done ({global_pct:.1f}%)"

    conductor_state_path = workspace / "tv7-conductor" / "docs" / ".conductor" / "state.json"
    conductor_msg = ""
    if conductor_state_path.exists():
        try:
            cond_data = json.loads(conductor_state_path.read_text(encoding="utf-8"))
            items = cond_data.get("work_items", [])
            stats = {}
            for item in items:
                status = item.get("status", "UNKNOWN").upper()
                stats[status] = stats.get(status, 0) + 1
            if items:
                stats_str = ", ".join(f"{count} {status}" for status, count in sorted(stats.items()))
                conductor_msg = f"Project Conductor: {len(items)} items ({stats_str})"
        except Exception:
            pass

    # 3. Print global header
    print(f"\n{global_metric}")
    if conductor_msg:
        print(conductor_msg)
    print()

    # 3.5 Print Workspace Action Plan
    print_action_plan(states, focus_map)

    # 4. Print unified repo list
    print_repo_status(states, focus_map)

    # 5. Write updated artifacts
    write_artifacts(core_dir, states, focus_map, global_metric)

    if os.environ.get("SYNC_MODE") == "operate":
        return print_cmd(["bash", str(core_dir / "tooling" / "git-dev.sh")], cwd=core_dir)
    rc = interactive_actions(core_dir, states, queue)
    if rc == REFRESH_COCKPIT:
        return rerun_sync(core_dir)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
