#!/usr/bin/env python3
"""Run the loopback-only TV7 browser test stack without Docker."""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
STATE = Path(__file__).resolve().parents[1] / "docs/.tmp/dev-browser-stack"
BACKEND = ROOT / "tv7-backend"
ENGINE = ROOT / "tv7-engine"
STUDIO = ROOT / "tv7-studio"
DEV_YT_DLP = STATE / "yt-dlp-venv/bin/yt-dlp"
LEGACY_DATABASE = STATE / "tv7-test.sqlite"
DATABASE = STATE / "tv7-test-v2.sqlite"
DATABASE_URL = f"sqlite+aiosqlite:////{str(DATABASE).lstrip('/')}"
MIGRATION_DATABASE_URL = f"sqlite+pysqlite:////{str(DATABASE).lstrip('/')}"
PORTS = {"backend": 8000, "engine": 7070, "studio": 8080}
HEALTH = {
    "backend": "http://127.0.0.1:8000/readyz",
    "engine": "http://127.0.0.1:7070/health",
    "studio": "http://127.0.0.1:8080/",
}


def healthy(name: str) -> bool:
    try:
        with urlopen(HEALTH[name], timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def pid_file(name: str) -> Path:
    return STATE / f"{name}.pid"


def running_pid(name: str) -> int | None:
    try:
        pid = int(pid_file(name).read_text().strip())
        os.kill(pid, 0)
        return pid
    except (FileNotFoundError, ValueError, ProcessLookupError):
        return None


def run_checked(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def start(name: str, command: list[str], cwd: Path, env: dict[str, str]) -> None:
    if healthy(name):
        if running_pid(name):
            print(f"[ok] {name} already running")
            return
        raise RuntimeError(f"Port {PORTS[name]} is already served by an unmanaged process")
    if running_pid(name):
        raise RuntimeError(f"{name} process exists but its health check failed; stop it first")
    log = (STATE / f"{name}.log").open("ab")
    process = subprocess.Popen(  # noqa: S603 - fixed local commands
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    pid_file(name).write_text(f"{process.pid}\n")
    for _ in range(40):
        if healthy(name):
            print(f"[ok] {name}: {HEALTH[name]}")
            return
        if process.poll() is not None:
            break
        time.sleep(0.25)
    raise RuntimeError(f"{name} failed; see {STATE / (name + '.log')}")


def up() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    backend_env = {**os.environ, "DATABASE_URL": DATABASE_URL, "PYTHONPATH": str(BACKEND / "src")}
    if not DATABASE.exists() and LEGACY_DATABASE.exists():
        with sqlite3.connect(LEGACY_DATABASE) as source, sqlite3.connect(DATABASE) as target:
            source.backup(target)
        print(f"[ok] copied disposable database to {DATABASE}; original preserved")
    migration_env = {**backend_env, "DATABASE_URL": MIGRATION_DATABASE_URL}
    with sqlite3.connect(DATABASE) as database:
        has_version = database.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchone()
        has_legacy_schema = database.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
    if has_legacy_schema and not has_version:
        run_checked(
            [str(BACKEND / ".venv/bin/alembic"), "stamp", "4f9d0c6b8a21"],
            BACKEND,
            migration_env,
        )
    run_checked(
        [str(BACKEND / ".venv/bin/alembic"), "upgrade", "head"],
        BACKEND,
        migration_env,
    )
    password = os.environ.get("TV7_TEST_PASSWORD")
    if password:
        run_checked(
            [str(BACKEND / "scripts/create_admin_user.sh"), "--email", os.environ.get("TV7_TEST_EMAIL", "tv7-automation@example.com"), "--full-name", "TV7 Automation"],
            BACKEND,
            {**backend_env, "PASSWORD": password},
        )
    elif not healthy("backend"):
        print("[!] Set TV7_TEST_PASSWORD to create or reset the disposable login")

    run_checked(
        ["npm", "run", "build"],
        STUDIO,
        {**os.environ, "VITE_ENGINE_URL": "http://127.0.0.1:7070"},
    )
    start("backend", [str(BACKEND / ".venv/bin/uvicorn"), "app.main:app", "--host", "127.0.0.1", "--port", "8000"], BACKEND, backend_env)
    engine_env = os.environ.copy()
    if DEV_YT_DLP.is_file():
        engine_env.setdefault("TV7_ENGINE_YT_DLP_BIN", str(DEV_YT_DLP))
        engine_env.setdefault("TV7_ENGINE_YT_DLP_JS_RUNTIME", "node")
    engine_binary = ENGINE / "target/debug/engine-service"
    if not engine_binary.is_file():
        engine_binary = ENGINE / "target/release/engine-service"
    if not engine_binary.is_file():
        raise RuntimeError("Build Engine first: cargo build -p engine-service")
    start("engine", [str(engine_binary)], ENGINE, engine_env)
    start("studio", [sys.executable, "-m", "http.server", "8080", "--bind", "127.0.0.1"], STUDIO / "dist", os.environ.copy())


def status() -> None:
    for name in PORTS:
        print(f"{'[ok]' if healthy(name) else '[X]'} {name}: {HEALTH[name]}")


def stop() -> None:
    for name in reversed(tuple(PORTS)):
        pid = running_pid(name)
        if pid is None:
            pid_file(name).unlink(missing_ok=True)
            continue
        os.killpg(pid, signal.SIGTERM)
        pid_file(name).unlink(missing_ok=True)
        print(f"[ok] stopped {name} ({pid})")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"up", "status", "stop"}:
        raise SystemExit("Usage: dev-browser-stack.py {up|status|stop}")
    {"up": up, "status": status, "stop": stop}[sys.argv[1]]()
