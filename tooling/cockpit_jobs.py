"""Persistent background jobs for the TV7 cockpit."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import threading
import uuid
from typing import Callable


class JobStore:
    ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def create(
        self,
        *,
        repo: str,
        kind: str,
        command: list[str],
        cwd: Path,
        after: Callable[[], None] | None = None,
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
        }
        self._write(job)
        threading.Thread(
            target=self._run,
            args=(job_id, command, cwd, after),
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

    def _run(
        self,
        job_id: str,
        command: list[str],
        cwd: Path,
        after: Callable[[], None] | None,
    ) -> None:
        job = self.get(job_id) or {}
        job.update(status="running", started_at=self._now())
        self._write(job)
        log_path = self.root / f"{job_id}.log"
        try:
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"$ {' '.join(command)}\n\n")
                log.flush()
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                exit_code = process.wait()
                log.write(f"\nCommand exited with status {exit_code}.\n")
                if exit_code == 0 and after:
                    log.write("Refreshing workspace snapshot...\n")
                    log.flush()
                    after()
            job.update(
                status="succeeded" if exit_code == 0 else "failed",
                exit_code=exit_code,
                finished_at=self._now(),
            )
        except Exception as exc:  # pragma: no cover - defensive process boundary
            log_path.write_text(f"Job failed before completion: {exc}\n", encoding="utf-8")
            job.update(status="failed", exit_code=-1, error=str(exc), finished_at=self._now())
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
