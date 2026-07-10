"""Persistent background jobs for the TV7 cockpit."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import time
import uuid
from typing import Callable


class JobStore:
    ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._processes: dict[str, subprocess.Popen] = {}
        self._recover_interrupted_jobs()

    def create(
        self,
        *,
        repo: str,
        kind: str,
        command: list[str],
        cwd: Path,
        after: Callable[[], None] | None = None,
        timeout: int = 600,
    ) -> dict:
        job_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
        job = {
            "id": job_id,
            "repo": repo,
            "kind": kind,
            "command": command,
            "status": "queued",
            "exit_code": None,
            "created_at": self._now(),
            "started_at": None,
            "finished_at": None,
            "phase": "queued",
            "last_activity_at": self._now(),
            "pid": None,
            "timeout_seconds": timeout,
        }
        self._write(job)
        threading.Thread(
            target=self._run,
            args=(job_id, command, cwd, after, timeout),
            daemon=True,
            name=f"cockpit-{job_id}",
        ).start()
        return job

    def get(self, job_id: str) -> dict | None:
        path = self.root / f"{job_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def log(self, job_id: str, offset: int = 0) -> tuple[str, int]:
        path = self.root / f"{job_id}.log"
        if not path.is_file():
            return "", offset
        data = path.read_text(encoding="utf-8", errors="replace")
        cleaned = self.ANSI_ESCAPE.sub("", data)
        return cleaned[offset:], len(cleaned)

    def active(self) -> list[dict]:
        rows = []
        for path in self.root.glob("*.json"):
            try:
                row = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if row.get("status") in {"queued", "running"}:
                rows.append(row)
        return sorted(rows, key=lambda row: row.get("created_at", ""))

    def cancel(self, job_id: str) -> dict | None:
        job = self.get(job_id)
        if not job:
            return None
        process = self._processes.get(job_id)
        if process and process.poll() is None:
            if process.stdin:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            os.killpg(process.pid, signal.SIGTERM)
        job.update(status="cancelled", phase="cancelled", finished_at=self._now(), last_activity_at=self._now())
        self._write(job)
        return job

    def write_input(self, job_id: str, text: str) -> None:
        with self._lock:
            process = self._processes.get(job_id)
            if process and process.poll() is None and process.stdin:
                try:
                    process.stdin.write(text)
                    process.stdin.flush()
                except OSError:
                    pass
                log_path = self.root / f"{job_id}.log"
                try:
                    with log_path.open("a", encoding="utf-8") as log:
                        log.write(text)
                        log.flush()
                except OSError:
                    pass

    def _run(
        self,
        job_id: str,
        command: list[str],
        cwd: Path,
        after: Callable[[], None] | None,
        timeout: int,
    ) -> None:
        job = self.get(job_id) or {}
        job.update(status="running", phase="starting", started_at=self._now(), last_activity_at=self._now())
        self._write(job)
        log_path = self.root / f"{job_id}.log"
        try:
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"$ {' '.join(command)}\n\n")
                log.flush()
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    start_new_session=True,
                )
                self._processes[job_id] = process
                job.update(pid=process.pid, phase="running", last_activity_at=self._now())
                self._write(job)
                deadline = time.monotonic() + timeout
                while process.poll() is None:
                    current = self.get(job_id) or job
                    if current.get("status") == "cancelled":
                        os.killpg(process.pid, signal.SIGTERM)
                        process.wait(timeout=5)
                        return
                    if time.monotonic() >= deadline:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                        log.write(f"\nCommand timed out after {timeout} seconds.\n")
                        log.flush()
                        job.update(status="failed", phase="timed_out", exit_code=-2, error=f"Timed out after {timeout} seconds", finished_at=self._now(), last_activity_at=self._now())
                        self._write(job)
                        return
                    job.update(last_activity_at=self._now())
                    self._write(job)
                    time.sleep(1)
                if (self.get(job_id) or {}).get("status") == "cancelled":
                    return
                if process.stdin:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                exit_code = process.returncode
                log.write(f"\nCommand exited with status {exit_code}.\n")
                if exit_code == 0 and after:
                    job.update(phase="refreshing", last_activity_at=self._now())
                    self._write(job)
                    log.write("Refreshing workspace snapshot...\n")
                    log.flush()
                    after()
            job.update(
                status="succeeded" if exit_code == 0 else "failed",
                phase="complete" if exit_code == 0 else "failed",
                exit_code=exit_code,
                finished_at=self._now(),
                last_activity_at=self._now(),
            )
        except Exception as exc:  # pragma: no cover - defensive process boundary
            log_path.write_text(f"Job failed before completion: {exc}\n", encoding="utf-8")
            job.update(status="failed", phase="failed", exit_code=-1, error=str(exc), finished_at=self._now(), last_activity_at=self._now())
        self._processes.pop(job_id, None)
        self._write(job)

    def _recover_interrupted_jobs(self) -> None:
        for path in self.root.glob("*.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if job.get("status") in {"queued", "running"}:
                job.update(status="interrupted", phase="interrupted", finished_at=self._now(), last_activity_at=self._now(), error="Cockpit restarted while this job was active")
                self._write(job)

    def _write(self, job: dict) -> None:
        path = self.root / f"{job['id']}.json"
        temporary = self.root / f".{job['id']}.json.tmp"
        with self._lock:
            temporary.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
            temporary.replace(path)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
