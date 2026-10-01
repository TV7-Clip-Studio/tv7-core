"""FastAPI service for the TV7 workspace cockpit."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

CORE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_DIR / "tooling"))

class ServerRequest(BaseModel):
    repo: str
    port: int | None = None

class JobInputRequest(BaseModel):
    text: str


from cockpit_assessments import assessment_history, suggested_commit_message
from cockpit_jobs import JobStore
from sync import load_queue, update_queue_entry
from cockpit_common import MockRepoState, action_command, allowed_repos, focus_display, normalize_action, workflow_from_state

STATE_PATH = CORE_DIR / "docs" / ".tmp" / "sync-roadmap-focus.json"
UI_DIST = CORE_DIR / "tooling" / "cockpit-ui" / "dist"
JOBS = JobStore(CORE_DIR / "docs" / ".tmp" / "cockpit" / "jobs")
AI_PROVIDERS = {"gemini", "codex", "deepseek"}
DEV_STATE_DIR = CORE_DIR / "docs" / ".tmp" / "dev-stack"
PORTS_PATH = DEV_STATE_DIR / "ports.json"
DEFAULT_PORTS = {
    "tv7-core": 7979,
    "tv7-backend": 8000,
    "tv7-engine": 7070,
    "tv7-site": 4321,
    "tv7-studio": 5173,
}

app = FastAPI(title="TV7 Cockpit", docs_url="/api/docs")


class ActionRequest(BaseModel):
    repo: str
    action_type: str
    command: str = ""
    commit_message: str | None = None


class AiRequest(BaseModel):
    repo: str
    model: str
    run_id: str | None = None
    scope: str | None = None


class ValidationRequest(BaseModel):
    repo: str
    status: str
    note: str = ""


def workspace_state() -> list[dict]:
    if not STATE_PATH.is_file():
        return []
    rows = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    for row in rows if isinstance(rows, list) else []:
        repo_path = CORE_DIR.parent / row.get("repo", "")
        live_status = subprocess.run(
            ["git", "status", "--porcelain=v1"], cwd=str(repo_path), capture_output=True, text=True, check=False
        ).stdout.splitlines() if repo_path.is_dir() else []
        row["dirty_files"] = live_status
        row["dirty_file_count"] = len(live_status)
        if live_status and row.get("pr"):
            queue_status = row.get("queue_status")
            row["action"] = {
                "state": "dirty-pr-needs-ready",
                "label": "Validate local changes",
                "why": f"PR #{row['pr'].get('number')} is open, but {len(live_status)} local change(s) are not committed or reviewed.",
                "command": f"make ready REPO={row.get('repo')}",
                "priority": 25,
            }
            if queue_status == "ready":
                row["action"] = {
                    "state": "awaiting-human-validation",
                    "label": "Run human validation",
                    "why": "Machine checks passed for local changes on this open PR branch; complete the generated human test contract before commit.",
                    "command": "record pass or fail in the cockpit",
                    "priority": 25,
                }
            elif queue_status == "passed":
                row["action"] = {
                    "state": "validated-needs-commit",
                    "label": "Commit validated changes",
                    "why": "Human validation passed for local changes on this open PR branch.",
                    "command": "commit validated slice",
                    "priority": 25,
                }
            elif queue_status == "failed":
                row["action"] = {
                    "state": "validation-failed",
                    "label": "Return failure to agent",
                    "why": "Human validation failed for local changes on this open PR branch.",
                    "command": "return failure to agent",
                    "priority": 25,
                }
        row["resolved_focus_display"] = focus_display(row.get("resolved_focus"))
        row["suggested_commit_message"] = suggested_commit_message(
            row.get("repo", ""), repo_path, row
        )
        row["workflow"] = workflow_state(row)
    return rows if isinstance(rows, list) else []


def workflow_state(row: dict) -> dict:
    pr = row.get("pr") or {}
    latest = None
    if pr and "note" not in pr:
        history = assessment_history(row.get("repo", ""), row)
        latest = history.get("latest_pr")
    return workflow_from_state(row, latest)


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


def is_port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex(("127.0.0.1", port)) == 0

def validate_repo(repo: str) -> None:
    if repo not in allowed_repos():
        raise HTTPException(400, "Unknown repository")


def load_ports() -> dict[str, int]:
    ports = DEFAULT_PORTS.copy()
    if PORTS_PATH.is_file():
        try:
            stored = json.loads(PORTS_PATH.read_text(encoding="utf-8"))
            for repo, port in stored.items():
                if repo in ports and isinstance(port, int) and 1 <= port <= 65535:
                    ports[repo] = port
        except json.JSONDecodeError:
            pass
    return ports


def save_port(repo: str, port: int) -> None:
    if repo not in DEFAULT_PORTS:
        return
    if not 1 <= port <= 65535:
        raise HTTPException(400, "Port must be between 1 and 65535")
    DEV_STATE_DIR.mkdir(parents=True, exist_ok=True)
    ports = load_ports()
    ports[repo] = port
    PORTS_PATH.write_text(json.dumps(ports, indent=2) + "\n", encoding="utf-8")


def port_owner(port: int) -> dict:
    try:
        res = subprocess.run(
            ["lsof", "-nP", "-iTCP:%s" % port, "-sTCP:LISTEN"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return {"pid": None, "command": "lsof missing"}
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return {"pid": None, "command": ""}
    columns = lines[1].split()
    pid = columns[1] if len(columns) > 1 else None
    command = " ".join(columns)
    return {"pid": pid, "command": command}


@app.get("/api/workspace")
def get_workspace() -> dict:
    active_jobs = JOBS.active()
    servers_status = []
    port_map = load_ports()

    for repo in ["tv7-core", "tv7-backend", "tv7-engine", "tv7-site", "tv7-studio"]:
        server_job = next((j for j in active_jobs if j.get("repo") == repo and j.get("kind") == f"server:{repo}"), None)
        job_id = server_job["id"] if server_job else None

        active = is_port_listening(port_map[repo])
        owner = port_owner(port_map[repo]) if active else {"pid": None, "command": ""}

        servers_status.append({
            "repo": repo,
            "port": port_map.get(repo),
            "default_port": DEFAULT_PORTS.get(repo),
            "status": "active" if active else "offline",
            "active_job_id": job_id,
            "owner": owner,
            "can_change_port": repo in {"tv7-backend", "tv7-engine", "tv7-site", "tv7-studio"},
        })

    return {
        "repositories": workspace_state(),
        "jobs": active_jobs,
        "servers": servers_status
    }


@app.post("/api/servers/start", status_code=202)
def start_server(request: ServerRequest) -> dict:
    validate_repo(request.repo)
    if request.port is not None:
        save_port(request.repo, request.port)
    port_map = load_ports()
    suffix = request.repo.replace("tv7-", "")
    backend_port = port_map["tv7-backend"]
    engine_port = port_map["tv7-engine"]
    site_port = port_map["tv7-site"]
    diag_cmd = (
        f"echo '=== RUNTIME DIAGNOSTICS ===';"
        f"echo 'PATH: '\"$PATH\";"
        f"echo 'DOCKER_HOST: '\"$DOCKER_HOST\";"
        f"echo 'DOCKER_CONTEXT: '$(docker context show 2>/dev/null || echo 'none');"
        f"echo 'WHOAMI: '$(whoami);"
        f"echo 'DOCKER SOCK EXIST: '$(ls -la /Users/joaquinastelarra/.docker/run/docker.sock 2>/dev/null || echo 'no');"
        f"echo '============================';"
        f"BACKEND_PORT={backend_port} ENGINE_PORT={engine_port} SITE_PORT={site_port} make dev-{suffix}"
    )
    command = ["zsh", "-lic", diag_cmd]
    return JOBS.create(
        repo=request.repo,
        kind=f"server:{request.repo}",
        command=command,
        cwd=CORE_DIR,
        timeout=86400,
    )


@app.post("/api/servers/stop", status_code=200)
def stop_server(request: ServerRequest) -> dict:
    validate_repo(request.repo)
    active_jobs = JOBS.active()
    server_job = next((j for j in active_jobs if j.get("repo") == request.repo and j.get("kind") == f"server:{request.repo}"), None)
    if server_job:
        JOBS.cancel(server_job["id"])

    port_map = load_ports()
    if request.repo in port_map:
        port = port_map[request.repo]
        try:
            res = subprocess.run(["lsof", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"], capture_output=True, text=True, check=False)
            pids = res.stdout.strip().split()
            for pid in pids:
                os.kill(int(pid), signal.SIGKILL)
        except Exception:
            pass

    return {"status": "stopped"}


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
        if operation == "commit":
            message = (request.commit_message or "").strip()
            if not message or "\n" in message or len(message) > 120:
                raise ValueError("Commit message must be one non-empty line of at most 120 characters.")
            command = ["python3", "tooling/cockpit_commit.py", "--repo", request.repo, "--message", message]
            cwd = CORE_DIR
        else:
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
    state = next((row for row in workspace_state() if row.get("repo") == request.repo), {})
    scope = request.scope or ("pull_request" if state.get("pr") and int(state.get("dirty_file_count") or 0) == 0 else "worktree")
    if scope not in {"worktree", "pull_request", "roadmap"}:
        raise HTTPException(400, "Unknown assessment scope")
    if scope == "pull_request" and not state.get("pr"):
        raise HTTPException(409, "This repository has no open pull request")
    return JOBS.create(
        repo=request.repo, kind=f"review:{request.model}",
        command=[sys.executable, "tooling/ai_agent.py", "review", "--repo", request.repo, "--model", request.model, "--scope", scope],
        cwd=CORE_DIR,
        timeout=330,
    )


@app.post("/api/ai/resolve", status_code=202)
def start_resolve(request: AiRequest) -> dict:
    validate_repo(request.repo)
    if request.model not in AI_PROVIDERS:
        raise HTTPException(400, "Unknown AI provider")
    if request.run_id and not re.fullmatch(r"[A-Za-z0-9_.-]+", request.run_id):
        raise HTTPException(400, "Invalid review run id")
    state = next((row for row in workspace_state() if row.get("repo") == request.repo), {})
    history = assessment_history(request.repo, state)
    selected = next((row for row in history.get("runs", []) if row.get("id") == request.run_id), None)
    if not selected:
        raise HTTPException(404, "Selected assessment does not exist")
    if selected.get("stale"):
        raise HTTPException(409, "Selected assessment is stale for the current HEAD")
    selected_dir = CORE_DIR / "docs" / ".tmp" / "cockpit" / "selected-assessments"
    selected_dir.mkdir(parents=True, exist_ok=True)
    selected_path = selected_dir / f"{request.run_id}.json"
    selected_path.write_text(json.dumps(selected, indent=2) + "\n", encoding="utf-8")
    command = [sys.executable, "tooling/ai_agent.py", "resolve", "--repo", request.repo, "--model", request.model, "--run-file", str(selected_path)]
    return JOBS.create(
        repo=request.repo, kind=f"resolve:{request.model}", command=command, cwd=CORE_DIR,
        after=refresh_workspace,
        timeout=330,
    )


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict:
    job = JOBS.cancel(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/api/jobs/{job_id}/input")
def job_input(job_id: str, request: JobInputRequest) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    JOBS.write_input(job_id, request.text)
    return {"status": "success"}


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    if not JOBS.get(job_id):
        raise HTTPException(404, "Job not found")

    async def stream():
        offset = 0
        previous_status = None
        while True:
            text, offset = JOBS.log(job_id, offset)
            if text:
                yield f"event: log\ndata: {json.dumps(text)}\n\n"
            job = JOBS.get(job_id) or {}
            status_signature = (job.get("status"), job.get("phase"), job.get("last_activity_at"))
            if status_signature != previous_status:
                yield f"event: status\ndata: {json.dumps(job)}\n\n"
                previous_status = status_signature
            if job.get("status") in {"succeeded", "failed", "cancelled", "interrupted"}:
                yield f"event: done\ndata: {json.dumps(job)}\n\n"
                break
            yield ": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/assessments/{repo}")
def get_assessments(repo: str) -> dict:
    validate_repo(repo)
    state = next((row for row in workspace_state() if row.get("repo") == repo), {})
    return assessment_history(repo, state)


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
