"""FastAPI service for the TV7 workspace cockpit."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

CORE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_DIR / "tooling"))

from ai_agent import review_root, worktree_context
from cockpit_jobs import JobStore
from sync import load_queue, update_queue_entry
from cockpit_common import MockRepoState, action_command, allowed_repos, focus_display, normalize_action

STATE_PATH = CORE_DIR / "docs" / ".tmp" / "sync-roadmap-focus.json"
UI_DIST = CORE_DIR / "tooling" / "cockpit-ui" / "dist"
JOBS = JobStore(CORE_DIR / "docs" / ".tmp" / "cockpit" / "jobs")
AI_PROVIDERS = {"gemini", "codex", "deepseek"}

app = FastAPI(title="TV7 Cockpit", docs_url="/api/docs")


class ActionRequest(BaseModel):
    repo: str
    action_type: str
    command: str = ""


class AiRequest(BaseModel):
    repo: str
    model: str
    run_id: str | None = None


class ValidationRequest(BaseModel):
    repo: str
    status: str
    note: str = ""


def workspace_state() -> list[dict]:
    if not STATE_PATH.is_file():
        return []
    rows = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    for row in rows if isinstance(rows, list) else []:
        row["resolved_focus_display"] = focus_display(row.get("resolved_focus"))
    return rows if isinstance(rows, list) else []


def refresh_workspace() -> None:
    env = os.environ.copy()
    env.update(SYNC_INTERACTIVE="0", SYNC_GEMINI="0", QUIET="1")
    subprocess.run(
        [sys.executable, str(CORE_DIR / "tooling" / "sync.py")],
        cwd=str(CORE_DIR), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False, timeout=180,
    )


def patch_snapshot_queue(repo: str, status: str) -> None:
    rows = workspace_state()
    row = next((item for item in rows if item.get("repo") == repo), None)
    if not row:
        return
    row["queue_status"] = status
    profiles = {
        "ready": {
            "state": "awaiting-human-validation", "label": "Run human validation",
            "why": "Machine checks passed; complete the generated human test contract before commit.",
            "command": "record pass or fail in the cockpit", "priority": 75,
        },
        "passed": {
            "state": "validated-needs-commit", "label": "Commit validated slice",
            "why": "Machine and human validation passed. Commit locally before starting review.",
            "command": "commit validated slice", "priority": 70,
        },
        "failed": {
            "state": "validation-failed", "label": "Return failure to agent",
            "why": "Human validation failed; address the recorded failure before another ready check.",
            "command": "return failure to agent", "priority": 80,
        },
    }
    if status in profiles:
        row["action"] = profiles[status]
    STATE_PATH.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def mark_machine_ready(repo: str) -> None:
    refresh_workspace()
    state_data = next((row for row in workspace_state() if row.get("repo") == repo), None)
    if not state_data:
        return
    update_queue_entry(CORE_DIR, load_queue(CORE_DIR), MockRepoState(state_data), status="ready", note="Machine validation passed.")
    patch_snapshot_queue(repo, "ready")


def validate_repo(repo: str) -> None:
    if repo not in allowed_repos():
        raise HTTPException(400, "Unknown repository")


@app.get("/api/workspace")
def get_workspace() -> dict:
    return {"repositories": workspace_state(), "jobs": JOBS.active()}


@app.post("/api/workspace/refresh", status_code=202)
def refresh() -> dict:
    return JOBS.create(
        repo="workspace", kind="refresh",
        command=["env", "SYNC_INTERACTIVE=0", "SYNC_GEMINI=0", "QUIET=1", sys.executable, "tooling/sync.py"], cwd=CORE_DIR,
    )


@app.post("/api/actions", status_code=202)
def start_action(request: ActionRequest) -> dict:
    validate_repo(request.repo)
    if request.action_type == "merge-pr":
        state = next((row for row in workspace_state() if row.get("repo") == request.repo), {})
        if int(state.get("dirty_file_count") or 0) > 0 or int(state.get("ahead") or 0) > 0:
            raise HTTPException(409, "Local changes must be committed, pushed, and reviewed before merge")
        pr = state.get("pr") or {}
        number = pr.get("number")
        if not number:
            raise HTTPException(400, "No open pull request is available to merge")
        reviews = pr.get("reviews") or []
        reviewed_heads = [
            str((review.get("commit") or {}).get("oid") or "")
            for review in reviews
            if "DeepSeek review" in str(review.get("body") or "")
        ]
        if not reviewed_heads or reviewed_heads[-1] != str(state.get("head_sha") or ""):
            raise HTTPException(409, "The latest DeepSeek review does not match the current HEAD")
        owner = os.environ.get("OWNER", "TV7-Clip-Studio")
        return JOBS.create(
            repo=request.repo,
            kind="merge-pr",
            command=["gh", "pr", "merge", str(number), "--repo", f"{owner}/{request.repo}", "--merge", "--delete-branch"],
            cwd=CORE_DIR.parent / request.repo,
            after=refresh_workspace,
        )
    try:
        operation = normalize_action(request.action_type)
        command, cwd = action_command(request.repo, operation, request.command)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return JOBS.create(
        repo=request.repo, kind=request.action_type, command=command, cwd=cwd,
        after=(lambda: mark_machine_ready(request.repo)) if operation == "ready" else refresh_workspace,
    )


@app.post("/api/ai/review", status_code=202)
def start_review(request: AiRequest) -> dict:
    validate_repo(request.repo)
    if request.model not in AI_PROVIDERS:
        raise HTTPException(400, "Unknown AI provider")
    return JOBS.create(
        repo=request.repo, kind=f"review:{request.model}",
        command=[sys.executable, "tooling/ai_agent.py", "review", "--repo", request.repo, "--model", request.model],
        cwd=CORE_DIR,
    )


@app.post("/api/ai/resolve", status_code=202)
def start_resolve(request: AiRequest) -> dict:
    validate_repo(request.repo)
    if request.model not in AI_PROVIDERS:
        raise HTTPException(400, "Unknown AI provider")
    if request.run_id and not re.fullmatch(r"[A-Za-z0-9_.-]+", request.run_id):
        raise HTTPException(400, "Invalid review run id")
    command = [sys.executable, "tooling/ai_agent.py", "resolve", "--repo", request.repo, "--model", request.model]
    if request.run_id:
        command.extend(["--run-id", request.run_id])
    return JOBS.create(
        repo=request.repo, kind=f"resolve:{request.model}", command=command, cwd=CORE_DIR,
        after=refresh_workspace,
    )


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    if not JOBS.get(job_id):
        raise HTTPException(404, "Job not found")

    async def stream():
        offset = 0
        while True:
            text, offset = JOBS.log(job_id, offset)
            if text:
                yield f"event: log\ndata: {json.dumps(text)}\n\n"
            job = JOBS.get(job_id) or {}
            if job.get("status") in {"succeeded", "failed"}:
                yield f"event: done\ndata: {json.dumps(job)}\n\n"
                break
            yield ": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/reviews/{repo}")
def get_review(repo: str) -> dict:
    validate_repo(repo)
    _, _, fingerprint, _ = worktree_context(CORE_DIR.parent / repo)
    path = review_root(repo, fingerprint) / "index.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    runs = payload.get("runs") or []
    active = next((row for row in runs if row.get("id") == payload.get("active_run_id")), runs[-1] if runs else {})
    return {**payload, **active}


@app.post("/api/validation")
def validation(request: ValidationRequest) -> dict:
    validate_repo(request.repo)
    if request.status not in {"passed", "failed"}:
        raise HTTPException(400, "Invalid validation status")
    state_data = next((row for row in workspace_state() if row.get("repo") == request.repo), None)
    if not state_data:
        raise HTTPException(404, "Repository absent from workspace snapshot")
    update_queue_entry(CORE_DIR, load_queue(CORE_DIR), MockRepoState(state_data), status=request.status, note=request.note)
    patch_snapshot_queue(request.repo, request.status)
    return {"status": "success", "queue_status": request.status}


if UI_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def ui(path: str):
    index = UI_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(503, "Cockpit UI is not built. Run make cockpit-deps.")
    return FileResponse(index)
