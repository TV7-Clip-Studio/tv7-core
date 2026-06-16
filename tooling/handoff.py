#!/usr/bin/env python3
"""Generate tracked TV7 agent handoffs from the latest sync cockpit data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


HANDOFFS: dict[str, dict[str, Any]] = {
    "tv7-backend": {
        "agent": "Backend Agent",
        "file": "backend.md",
        "mission": "Finish the Backend cloud AI control plane for Engine delegation.",
        "roadmap_items": [
            "BE-A01-02-01",
            "BE-A01-02-02",
            "BE-A01-02-04",
            "BE-A01-02-05",
            "BE-A01-02-06",
            "BE-A01-02-07",
        ],
        "contracts": [
            "docs/contracts/tv7-engine/ai-provider-handoff.md",
            "docs/contracts/openapi/tv7-backend/openapi.json",
            "docs/roadmaps/tv7-backend-roadmap.md",
        ],
        "tasks": [],
        "constraints": [
            "Do not add local media probing, transcription, rendering, or transcript scoring to Backend.",
            "Do not expose provider secrets in API payloads, logs, diagnostics, tests, or admin pages.",
            "Do not make Studio call Backend cloud AI execution or debug endpoints directly.",
        ],
        "validation": ["make deps", "make lint", "make type", "make test", "make testcov"],
        "deliverables": [
            "Backend endpoints and schemas are stable for Studio -> Backend token minting and Engine -> Backend execution.",
            "Credit and usage accounting are covered by tests and visible to admins.",
            "OpenAPI contract is updated in tv7-core.",
        ],
    },
    "tv7-engine": {
        "agent": "Engine Agent",
        "file": "engine.md",
        "mission": "Finish the unified Engine AI runtime boundary.",
        "roadmap_items": [
            "EN-A05-01-02",
            "EN-A05-01-03",
            "EN-A06-01-04",
            "EN-A04-01-02",
        ],
        "contracts": [
            "docs/contracts/tv7-engine/ai-provider-handoff.md",
            "docs/contracts/tv7-engine/runtime-setup.md",
            "docs/contracts/openapi/tv7-engine/openapi.json",
            "docs/roadmaps/tv7-engine-roadmap.md",
        ],
        "tasks": [
            "Own provider dispatch for one Studio-facing AI surface.",
            "Keep Backend-issued cloud delegation tokens in memory only and clear them on request.",
            "Call Backend cloud AI execution only through the Engine-scoped delegated token.",
            "Normalize auth, license, quota, network, provider, and context-size failures for Studio.",
            "Expose setup/status and diagnostics readiness for ai and offline_creation without conflating them.",
            "Keep transcript intelligence provider-agnostic for Studio.",
        ],
        "constraints": [
            "Do not persist delegated cloud tokens.",
            "Do not own Backend credentials, billing, quota policy, or user auth storage.",
            "Do not make cloud AI readiness imply offline_creation readiness.",
        ],
        "validation": ["make fmt-check", "make check", "make test", "make clippy"],
        "deliverables": [
            "Engine provides one AI execution/debug integration point for Studio.",
            "Capability readiness clearly separates local/offline capability from cloud-only availability.",
            "Engine OpenAPI and core contracts are updated in tv7-core.",
        ],
    },
    "tv7-studio": {
        "agent": "Studio Agent",
        "file": "studio.md",
        "mission": "Finish user-facing AI setup, diagnostics, and Engine-only AI calls.",
        "roadmap_items": [
            "ST-A04-01-02",
            "ST-A04-01-04",
            "ST-A04-01-05",
            "ST-A01-02-01",
        ],
        "contracts": [
            "docs/contracts/tv7-engine/ai-provider-handoff.md",
            "docs/contracts/tv7-engine/runtime-setup.md",
            "docs/contracts/openapi/tv7-backend/openapi.json",
            "docs/contracts/openapi/tv7-engine/openapi.json",
            "docs/roadmaps/tv7-studio-roadmap.md",
        ],
        "tasks": [
            "Use normal Backend auth/session flow to request an Engine cloud AI delegation token.",
            "Pass the delegated token to Engine over loopback and clear it on logout, revocation, or account changes.",
            "Call Engine for AI execution and AI diagnostics, including cloud debug.",
            "Display AI setup, quota, license, delegated-token, provider, and offline readiness states clearly.",
            "Regenerate/adopt API clients when Backend or Engine contracts change.",
        ],
        "constraints": [
            "Do not collect DeepSeek/OpenAI/provider keys from users.",
            "Do not call Backend cloud AI execution/debug endpoints directly from feature flows.",
            "Do not treat missing cloud delegation as an Engine startup failure.",
        ],
        "validation": ["make format", "make analyze", "make test", "make check"],
        "deliverables": [
            "Studio has one AI feature integration surface: Engine.",
            "Diagnostics and first-run setup show actionable readiness states.",
            "Quick Clip and AI feature flows use Engine contracts only.",
        ],
    },
}


GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
RESET = "\033[0m"


@dataclass
class SyncRow:
    repo: str
    branch: str = "-"
    git_note: str = "unknown"
    dirty_files: list[str] | None = None
    recent_commits: list[str] | None = None
    pr: dict[str, Any] | None = None
    focus: dict[str, Any] | None = None
    matched_item: dict[str, Any] | None = None
    open_required_count: int = 0
    open_other_count: int = 0
    completed_count: int = 0
    resolved_focus: str = ""
    signals: dict[str, Any] | None = None
    head_sha: str = ""
    dirty_file_count: int = 0
    dirty_status_hash: str = ""
    sync_generated_at: str = ""


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


def load_sync_rows(core_dir: Path) -> dict[str, SyncRow]:
    sync_path = core_dir / "docs" / ".tmp" / "sync-roadmap-focus.json"
    if not sync_path.exists():
        return {}
    try:
        raw = json.loads(sync_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    rows: dict[str, SyncRow] = {}
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or "repo" not in item:
            continue
        rows[str(item["repo"])] = SyncRow(
            repo=str(item["repo"]),
            branch=str(item.get("branch", "-")),
            git_note=str(item.get("git_note", "unknown")),
            dirty_files=[str(v) for v in item.get("dirty_files", [])],
            recent_commits=[str(v) for v in item.get("recent_commits", [])],
            pr=item.get("pr") if isinstance(item.get("pr"), dict) else None,
            focus=item.get("focus") if isinstance(item.get("focus"), dict) else None,
            matched_item=item.get("matched_item") if isinstance(item.get("matched_item"), dict) else None,
            open_required_count=int(item.get("open_required_count", 0) or 0),
            open_other_count=int(item.get("open_other_count", 0) or 0),
            completed_count=int(item.get("completed_count", 0) or 0),
            resolved_focus=str(item.get("resolved_focus", "")),
            signals=item.get("signals") if isinstance(item.get("signals"), dict) else None,
            head_sha=str(item.get("head_sha", "")),
            dirty_file_count=int(item.get("dirty_file_count", 0) or 0),
            dirty_status_hash=str(item.get("dirty_status_hash", "")),
            sync_generated_at=str(item.get("sync_generated_at", "")),
        )
    return rows


def fallback_row(repo: str, workspace: Path) -> SyncRow:
    path = workspace / repo
    if not (path / ".git").exists():
        return SyncRow(repo=repo, git_note=f"missing at {path}", resolved_focus="Repository missing locally.")
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path).stdout.strip() or "-"
    dirty_files = run(["git", "status", "--porcelain"], path).stdout.splitlines()[:12]
    commits = run(["git", "log", "--oneline", "-n", "3"], path).stdout.splitlines()
    
    # Calculate simple changes count
    changes = len([line for line in dirty_files if line.strip()])
    untracked = sum(1 for f in dirty_files if f.strip().startswith("??"))
    pending = []
    if changes:
        pending.append(f"{changes} pending changes")
    if untracked:
        pending.append(f"including {untracked} untracked files")
    
    pending_str = " ".join(pending)
    resolved_focus = "no open roadmap items found"
    if pending_str:
        resolved_focus += f"; {pending_str}"
        
    return SyncRow(
        repo=repo,
        branch=branch,
        git_note=f"{changes} pending" if changes else "clean",
        dirty_files=dirty_files,
        recent_commits=commits,
        resolved_focus=resolved_focus
    )


def status_hash(dirty_files: list[str]) -> str:
    payload = "\n".join(dirty_files).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stale_reasons(row: SyncRow, workspace: Path) -> list[str]:
    path = workspace / row.repo
    if not (path / ".git").exists() or not row.head_sha:
        return []
    current_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path).stdout.strip()
    current_head = run(["git", "rev-parse", "HEAD"], path).stdout.strip()
    current_dirty = run(["git", "status", "--porcelain"], path).stdout.splitlines()
    reasons: list[str] = []
    if row.branch and current_branch and row.branch != current_branch:
        reasons.append(f"branch changed from {row.branch} to {current_branch}")
    if current_head and row.head_sha != current_head:
        reasons.append("HEAD changed")
    if row.dirty_file_count != len(current_dirty):
        reasons.append(f"dirty count changed from {row.dirty_file_count} to {len(current_dirty)}")
    if row.dirty_status_hash and row.dirty_status_hash != status_hash(current_dirty):
        reasons.append("dirty file set changed")
    return reasons


def bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- None."


def maybe_list(values: list[str] | None) -> str:
    return bullet_list(values or [])


def detected_state(row: SyncRow) -> str:
    signals = row.signals or {}
    summary = signals.get("summary")
    if isinstance(summary, list) and summary:
        return bullet_list([str(item) for item in summary])
    return "- No semantic detector output for this repo."


def dirty_files_section(row: SyncRow) -> str:
    files = row.dirty_files or []
    if not files:
        return "- None."
    limit = int(os.environ.get("HANDOFF_DIRTY_FILE_LIMIT", "40"))
    shown = files[:limit]
    lines = [f"- {value}" for value in shown]
    if len(files) > limit:
        lines.append(f"- ... {len(files) - limit} more dirty files omitted; see git status.")
    return "\n".join(lines)


def completion_notes(repo: str, row: SyncRow) -> str:
    signals = row.signals or {}
    today = os.environ.get("HANDOFF_DATE", date.today().isoformat())
    notes: list[str] = []
    if repo == "tv7-backend":
        if signals.get("auth_license_endpoint_exists"):
            notes.append(
                f"{today}: `GET /api/v1/auth/license` is detected as the Studio account/license/cloud-AI readiness endpoint."
            )
        if signals.get("engine_token_endpoint_exists"):
            notes.append(f"{today}: `/api/v1/cloud-ai/engine-token` is detected for Backend-issued Engine delegation.")
        if signals.get("engine_execute_endpoint_exists"):
            notes.append(f"{today}: `/api/v1/cloud-ai/engine/execute` is detected as the Engine-only cloud AI execution endpoint.")
        if signals.get("cloud_ai_tests_exist"):
            notes.append(f"{today}: Cloud AI API tests are detected in `tests/test_cloud_ai_api.py`.")
        if signals.get("cloud_ai_migration_exists"):
            notes.append(f"{today}: Cloud AI credit/metering migration is detected.")
        if signals.get("auth_license_endpoint_exists"):
            notes.append(
                "Follow-up: Studio should call `/api/v1/auth/license` for readiness and request `/api/v1/cloud-ai/engine-token` only when it needs a delegated token for Engine."
            )
            notes.append("Follow-up: Engine remains the only caller of `/api/v1/cloud-ai/engine/execute`.")
    if not notes:
        notes = [
            "Generated handoff has no completion signals yet.",
            "Run `SYNC_INTERACTIVE=0 make sync` and `make handoff` after the agent reports completion.",
        ]
    return bullet_list(notes)


def task_list(repo: str, row: SyncRow, config: dict[str, Any]) -> list[str]:
    if repo != "tv7-backend":
        return [str(item) for item in config["tasks"]]

    signals = row.signals or {}
    readiness_task = (
        "Verify `GET /api/v1/auth/license` remains aligned with `/api/v1/cloud-ai/engine-token` account, license, cloud-AI, and credit readiness rules."
        if signals.get("auth_license_endpoint_exists")
        else "Add or finalize the Studio account/license/cloud-AI readiness endpoint (`GET /api/v1/auth/license`) unless a documented replacement is chosen."
    )
    return [
        "Preserve the pending cloud AI implementation; do not duplicate or rebuild it from scratch.",
        readiness_task,
        "Harden the existing Backend-issued short-lived Engine delegation tokens scoped to engine:cloud_ai.",
        "Harden the existing Engine-only cloud AI execution and provider error normalization.",
        "Keep DeepSeek/provider credentials, billing, quota, and cloud metering inside Backend.",
        "Expose admin visibility for cloud AI credit balance, usage, provider latency, and failures.",
        "Regenerate/update Backend OpenAPI after endpoint or schema changes.",
    ]


def pr_line(pr: dict[str, Any] | None) -> str:
    if not pr:
        return "none"
    if "note" in pr:
        return str(pr["note"])
    return f"#{pr.get('number')} {str(pr.get('state', '')).upper()} {pr.get('url', '')}".strip()


def focus_line(row: SyncRow, config: dict[str, Any]) -> str:
    focus = row.focus or {}
    if not focus:
        return f"Milestone route: {', '.join(config['roadmap_items'])}. No focused roadmap item found in latest sync artifact."
    source = "matched" if row.matched_item else "next"
    sync_line = f"{focus.get('id', '-')}: {focus.get('title', '-')} ({source}, {focus.get('path', '-')})"
    if focus.get("id") in config["roadmap_items"]:
        return sync_line
    return f"Milestone route: {', '.join(config['roadmap_items'])}. Latest sync focus outside this handoff: {sync_line}"


def render_handoff(repo: str, row: SyncRow, config: dict[str, Any]) -> str:
    agent = config["agent"]
    prompt = (
        f"You are the {agent}. Work in {repo}. Use docs/handoffs/active/{config['file']} "
        "as your operating contract. Do not push. Implement only the assigned roadmap scope, "
        "keep contracts updated, and run the listed validation commands."
    )
    return f"""# {agent} Handoff

Milestone: Unified Engine AI + Cloud Delegation
Repo: `{repo}`
Generated from: `make handoff`

## Mission
{config["mission"]}

## Current State
- Branch: `{row.branch}`
- Git status: {row.git_note}
- Pull request: {pr_line(row.pr)}
- Focus: {focus_line(row, config)}
- Resolved Focus: {row.resolved_focus}
- Roadmap counts: {row.completed_count} completed, {row.open_required_count} required open, {row.open_other_count} other open.

## Roadmap Items
{bullet_list(config["roadmap_items"])}

## Contract References
{bullet_list(config["contracts"])}

## Current Code Signals
Detected state:
{detected_state(row)}

Dirty files:
{dirty_files_section(row)}

Recent commits:
{maybe_list(row.recent_commits)}

## Tasks
{bullet_list(task_list(repo, row, config))}

## Constraints
{bullet_list(config["constraints"])}

## Validation
{bullet_list(config["validation"])}

## Deliverables
{bullet_list(config["deliverables"])}

## Completion Notes
{completion_notes(repo, row)}

## Copy/Paste Prompt
{prompt}
"""


def target_repos() -> list[str]:
    requested = os.environ.get("HANDOFF_REPO", "").strip()
    if requested:
        if requested not in HANDOFFS:
            raise SystemExit(f"Unknown HANDOFF_REPO={requested}. Expected one of: {', '.join(HANDOFFS)}")
        return [requested]
    return list(HANDOFFS)


def main() -> int:
    core_dir = Path(__file__).resolve().parents[1]
    workspace = Path(os.environ.get("REPO_ROOT", str(core_dir.parent))).resolve()
    rows = load_sync_rows(core_dir)
    out_dir = core_dir / "docs" / "handoffs" / "active"
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts_only = os.environ.get("HANDOFF_PROMPTS_ONLY", "0") == "1"
    verbose = os.environ.get("HANDOFF_VERBOSE", "0") == "1"
    check_only = os.environ.get("HANDOFF_CHECK_ONLY", "0") == "1"

    if check_only:
        print("TV7 agent handoff freshness check")
    else:
        print("TV7 agent handoffs" if not prompts_only else "TV7 agent prompts")
    print("Source: docs/.tmp/sync-roadmap-focus.json" if rows else "Source: git fallback; run make sync for richer context")
    print()

    for repo in target_repos():
        config = HANDOFFS[repo]
        row = rows.get(repo) or fallback_row(repo, workspace)
        stale = stale_reasons(row, workspace)
        path = out_dir / config["file"]
        content = render_handoff(repo, row, config)
        prompt = f"You are the {config['agent']}. Work in {repo}. Use {path.relative_to(core_dir)} as your operating contract. Do not push."
        if check_only:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != content:
                print(f"[warn] {path.relative_to(core_dir)} is stale; run `make handoff HANDOFF_REPO={repo}`.")
            elif stale:
                print(f"[warn] sync artifact for {repo} is stale ({'; '.join(stale)}); run `SYNC_INTERACTIVE=0 make sync`.")
            else:
                print(f"[ok] {path.relative_to(core_dir)} is up to date.")
            continue
        if prompts_only:
            print(f"- {GREEN}{config['agent']}{RESET}: {prompt}")
            print(f"  Focus: {row.resolved_focus}")
            print()
            continue
        path.write_text(content, encoding="utf-8")
        
        total = row.completed_count + row.open_required_count + row.open_other_count
        done = row.completed_count
        pct = (done / total * 100.0) if total > 0 else 0.0
        metric_str = f"[Roadmap: {done}/{total} done ({pct:.1f}%)]"
        
        print(f"[ok] {GREEN}{config['agent']}{RESET}: {path.relative_to(core_dir)}")
        print(f"     Status: {CYAN}{row.branch}{RESET} - {row.git_note} - PR: {pr_line(row.pr)} {YELLOW}{metric_str}{RESET}")
        print(f"     Doing:  {row.resolved_focus}")
        if stale:
            print(f"     {YELLOW}Warning: sync artifact may be stale ({'; '.join(stale)}). Run `SYNC_INTERACTIVE=0 make sync` before assigning this handoff.{RESET}")
        if verbose and row.signals:
            for key, value in row.signals.items():
                print(f"     Signal {key}: {value}")
        print(f"     Prompt: {prompt}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
