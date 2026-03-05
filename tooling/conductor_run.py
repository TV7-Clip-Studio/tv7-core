#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Project Conductor flow (plan + tickets).")
    parser.add_argument("--core-dir", default=str(Path(__file__).resolve().parents[1]), help="Path to tv7-core repo")
    parser.add_argument("--roadmap-file", default="", help="Optional roadmap file path for single-roadmap plan mode")
    parser.add_argument("--repo", action="append", default=[], help="Optional repo filter(s) for ticket sync")
    parser.add_argument("--item-prefix", action="append", default=[], help="Optional item id prefix filter(s)")
    parser.add_argument("--agent-profile", default="local_auto_medium", help="Agent profile for ticket sync")
    parser.add_argument("--batch-id", default="", help="Optional batch id override")
    parser.add_argument("--dry-run", action="store_true", help="Run tickets in dry-run mode")
    parser.add_argument(
        "--assess",
        action="store_true",
        default=False,
        help="Enable assessment during conductor-run ticket sync (disabled by default).",
    )
    args = parser.parse_args(argv)

    core_dir = Path(args.core_dir).resolve()
    conductor_cli = [sys.executable, str(core_dir / "tooling" / "conductor.py")]

    env = dict(os.environ)
    env.setdefault("TV7_STATE_ROOT_NAME", ".conductor")

    plan_cmd = [*conductor_cli, "plan"]
    if args.roadmap_file:
        plan_cmd.extend(["--single-roadmap", "--roadmap", args.roadmap_file])
    _run(plan_cmd, cwd=core_dir)

    tickets_cmd = [*conductor_cli, "tickets", "--agent-profile", args.agent_profile]
    if not args.dry_run:
        tickets_cmd.append("--apply")
    if args.batch_id:
        tickets_cmd.extend(["--batch-id", args.batch_id])
    for repo in args.repo:
        tickets_cmd.extend(["--repo", repo])
    for prefix in args.item_prefix:
        tickets_cmd.extend(["--item-prefix", prefix])
    if not args.assess:
        tickets_cmd.append("--no-assess")

    result = subprocess.run(tickets_cmd, cwd=str(core_dir), env=env, check=False)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
