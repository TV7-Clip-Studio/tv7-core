#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify tv7-core Conductor shim routing.")
    parser.add_argument(
        "--core-dir",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to tv7-core repo.",
    )
    parser.add_argument(
        "--workspace-dir",
        default="",
        help="Path to workspace root. Defaults to the parent of --core-dir.",
    )
    args = parser.parse_args()

    core_dir = Path(args.core_dir).expanduser().resolve()
    workspace_dir = Path(args.workspace_dir).expanduser().resolve() if args.workspace_dir else core_dir.parent
    conductor_dir = workspace_dir / "tv7-conductor"
    core_shim = core_dir / "tooling" / "conductor.py"
    run_shim = core_dir / "tooling" / "conductor_run.py"
    conductor_runtime = conductor_dir / "tooling" / "conductor.py"
    conductor_run_runtime = conductor_dir / "tooling" / "conductor_run.py"

    failures: list[str] = []
    for label, path in (
        ("core conductor shim", core_shim),
        ("core conductor_run shim", run_shim),
        ("conductor runtime", conductor_runtime),
        ("conductor_run runtime", conductor_run_runtime),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 2

    stage_targets = [
        ("conductor-init", "tooling/conductor.py"),
        ("conductor-plan", "tooling/conductor.py"),
        ("conductor-tickets", "tooling/conductor.py"),
        ("conductor-expand", "tooling/conductor.py"),
        ("conductor-execute", "tooling/conductor.py"),
        ("conductor-review", "tooling/conductor.py"),
        ("conductor-status", "tooling/conductor.py"),
        ("conductor-events", "tooling/conductor.py"),
        ("conductor-run", "tooling/conductor_run.py"),
    ]
    for target_name, expected_script in stage_targets:
        result = _run(["make", "-n", target_name], cwd=core_dir)
        if result.returncode != 0:
            print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
            return result.returncode
        dry_run = result.stdout
        if expected_script not in dry_run:
            print(
                f"FAIL: `{target_name}` dry-run does not route through {expected_script}",
                file=sys.stderr,
            )
            return 2
        if "tooling/orchestrator.py" in dry_run:
            print(
                f"FAIL: `{target_name}` dry-run still routes through deprecated tooling/orchestrator.py",
                file=sys.stderr,
            )
            return 2

    help_result = _run([sys.executable, str(core_shim), "--help"], cwd=core_dir)
    if help_result.returncode != 0:
        print(help_result.stderr.strip() or help_result.stdout.strip(), file=sys.stderr)
        return help_result.returncode
    if "Project Conductor CLI" not in help_result.stdout:
        print("FAIL: core conductor shim did not reach standalone conductor CLI", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="tv7-conductor-shim-") as td:
        state_dir = Path(td) / ".conductor"
        init_result = _run(
            [
                sys.executable,
                str(core_shim),
                "--state-dir",
                str(state_dir),
                "init",
            ],
            cwd=core_dir,
        )
        if init_result.returncode != 0:
            print(init_result.stderr.strip() or init_result.stdout.strip(), file=sys.stderr)
            return init_result.returncode

        state_path = state_dir / "state.json"
        events_path = state_dir / "events.jsonl"
        if not state_path.is_file() or not events_path.is_file():
            print(f"FAIL: shim init did not create expected state files under {state_dir}", file=sys.stderr)
            return 2

        state = json.loads(state_path.read_text())
        schema = state.get("schema", {})
        if schema.get("name") != "project-conductor-state":
            print(f"FAIL: unexpected state schema in {state_path}: {schema}", file=sys.stderr)
            return 2

    print("Conductor shim check passed:")
    print(f"- core_dir: {core_dir}")
    print(f"- conductor_dir: {conductor_dir}")
    print(f"- make targets checked: {len(stage_targets)}")
    print("- standalone CLI reached through tv7-core/tooling/conductor.py")
    print("- temporary state override honored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
