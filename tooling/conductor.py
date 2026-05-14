#!/usr/bin/env python3
from __future__ import annotations

import os
import sys


def _target(script_name: str) -> str:
    workspace = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(workspace, "tv7-conductor", "tooling", script_name)


def main() -> int:
    core_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workspace = os.path.abspath(os.path.join(core_dir, ".."))
    conductor_dir = os.path.join(workspace, "tv7-conductor")
    state_dir = os.path.join(conductor_dir, "docs", ".conductor")
    target = _target("conductor.py")
    if not os.path.exists(target):
        print(f"error: missing conductor runtime at {target}", file=sys.stderr)
        return 2
    os.execv(
        sys.executable,
        [
            sys.executable,
            target,
            "--core-dir",
            core_dir,
            "--workspace-dir",
            workspace,
            "--conductor-dir",
            conductor_dir,
            "--state-dir",
            state_dir,
            *sys.argv[1:],
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
