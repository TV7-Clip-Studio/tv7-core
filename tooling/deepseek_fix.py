#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

MIN_PYTHON = (3, 11)


def _require_python() -> None:
    if sys.version_info < MIN_PYTHON:
        need = ".".join(str(p) for p in MIN_PYTHON)
        cur = ".".join(str(p) for p in sys.version_info[:3])
        raise SystemExit(f"Python {need}+ is required (found {cur}).")


def _read_repo_checks(config_file: Path) -> dict[str, str]:
    checks: dict[str, str] = {}
    for raw in config_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        repo = (parts[0] if len(parts) > 0 else "").strip()
        check = (parts[2] if len(parts) > 2 else "").strip()
        if repo:
            checks[repo] = check
    return checks


def _run_followup(
    followup_script: Path,
    base_env: dict[str, str],
    only_actionable: bool,
    out_json: Path,
    out_md: Path,
) -> None:
    env = os.environ.copy()
    env.update(base_env)
    env["ONLY_ACTIONABLE"] = "1" if only_actionable else "0"
    env["FAIL_ON_ACTIONABLE"] = "0"
    env["OUT_JSON"] = str(out_json)
    env["OUT_MD"] = str(out_md)

    result = subprocess.run(
        [sys.executable, str(followup_script)],
        text=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"deepseek_followup.py failed with exit code {result.returncode}")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc


def main() -> int:
    _require_python()

    script_dir = Path(__file__).resolve().parent
    repo_root = Path(os.environ.get("REPO_ROOT", "..")).resolve()
    config_file = Path(os.environ.get("CONFIG_FILE", str(script_dir / "repos-checks.conf"))).resolve()
    followup_script = Path(os.environ.get("FOLLOWUP_SCRIPT", str(script_dir / "deepseek_followup.py"))).resolve()

    owner = os.environ.get("OWNER", "TV7-Clip-Studio")
    pr_state = os.environ.get("PR_STATE", "open")
    limit = os.environ.get("LIMIT", "20")
    branch_prefix = os.environ.get("BRANCH_PREFIX", "codex/batch")
    batch_id = os.environ.get("BATCH_ID", "")
    include_recommendations = os.environ.get("INCLUDE_RECOMMENDATIONS", "1")

    followup_json = Path(os.environ.get("FOLLOWUP_JSON", "/tmp/tv7-deepseek-followup.json")).resolve()
    followup_md = Path(os.environ.get("FOLLOWUP_MD", "/tmp/tv7-deepseek-followup.md")).resolve()
    actionable_json = Path(os.environ.get("ACTIONABLE_JSON", "/tmp/tv7-deepseek-followup-actionable.json")).resolve()
    actionable_md = Path(os.environ.get("ACTIONABLE_MD", "/tmp/tv7-deepseek-followup-actionable.md")).resolve()
    prompt_dir = Path(os.environ.get("PROMPT_DIR", "/tmp/tv7-deepseek-fix-prompts")).resolve()
    plan_md = Path(os.environ.get("PLAN_MD", "/tmp/tv7-deepseek-fix-plan.md")).resolve()

    if not config_file.exists():
        raise SystemExit(f"Missing config file: {config_file}")
    if not followup_script.exists():
        raise SystemExit(f"Missing follow-up script: {followup_script}")

    checks = _read_repo_checks(config_file)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    plan_md.parent.mkdir(parents=True, exist_ok=True)

    base_env = {
        "REPO_ROOT": str(repo_root),
        "CONFIG_FILE": str(config_file),
        "OWNER": owner,
        "PR_STATE": pr_state,
        "LIMIT": str(limit),
        "BRANCH_PREFIX": branch_prefix,
        "BATCH_ID": batch_id,
        "INCLUDE_RECOMMENDATIONS": include_recommendations,
    }

    _run_followup(followup_script, base_env, only_actionable=False, out_json=followup_json, out_md=followup_md)
    if not followup_json.exists():
        raise SystemExit(f"Follow-up output was not generated: {followup_json}")

    _run_followup(followup_script, base_env, only_actionable=True, out_json=actionable_json, out_md=actionable_md)
    if not actionable_json.exists():
        raise SystemExit(f"Actionable follow-up output was not generated: {actionable_json}")

    entries = _load_json(actionable_json)
    if not isinstance(entries, list):
        raise SystemExit(f"Unexpected actionable payload format: {actionable_json}")

    actionable_count = len(entries)
    header_lines = [
        "# DeepSeek Fix Queue",
        "",
        f"Full follow-up: `{followup_json}`",
        f"Actionable follow-up: `{actionable_json}`",
        f"Prompt directory: `{prompt_dir}`",
        "",
    ]
    if actionable_count == 0:
        header_lines.append("No actionable DeepSeek findings detected.")
        plan_md.write_text("\n".join(header_lines) + "\n")
        print(f"No actionable findings. Plan written to: {plan_md}")
        return 0

    header_lines.extend(
        [
            "| Repo | PR | Actionable Findings | Prompt File | Comments JSON |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )

    for entry in entries:
        repo = str(entry.get("repo", "")).strip()
        pr_number = int(entry.get("pr_number", 0))
        pr_title = str(entry.get("pr_title", "")).strip()
        pr_url = str(entry.get("pr_url", "")).strip()
        head_branch = str(entry.get("head_branch", "")).strip()
        base_branch = str(entry.get("base_branch", "")).strip()
        findings_total = int(entry.get("actionable_count", 0))
        repo_path = repo_root / repo
        check_cmd = checks.get(repo, "").strip()

        prompt_file = prompt_dir / f"{repo}-pr-{pr_number}.md"
        comments_json_file = prompt_dir / f"{repo}-pr-{pr_number}.comments.json"
        comments_json_file.write_text(json.dumps(entry, indent=2) + "\n")

        prompt_lines = [
            f"You are the {repo} repository agent.",
            "",
            f"Task: address actionable DeepSeek review findings for PR #{pr_number}.",
            "",
            "Context:",
            f"- Repo path: {repo_path}",
            f"- PR: {pr_url}",
            f"- PR title: {pr_title}",
            f"- Head branch: {head_branch}",
            f"- Base branch: {base_branch}",
            f"- Actionable findings count: {findings_total}",
        ]
        if check_cmd:
            prompt_lines.append(f"- Validation command: {check_cmd}")
        prompt_lines.extend(
            [
                "",
                "Review details source:",
                f"- Prompt bundle folder: {prompt_dir}",
                f"- Comments JSON file: {comments_json_file}",
                "- The JSON includes PR metadata and all matched DeepSeek/GitHub review comments for this PR.",
                "",
                "Execution requirements:",
                "1. Checkout and update the PR branch locally.",
                "2. Read the JSON comments file and identify each actionable item.",
                "3. Apply the minimum safe code changes to address each actionable item.",
                "4. If an item is advisory-only, keep code unchanged and document rationale.",
                "5. Run the repo validation command from config (if defined).",
                "6. Commit and push updates to the same PR branch.",
                "7. Summarize what was fixed and any items intentionally left unchanged.",
                "",
            ]
        )
        prompt_file.write_text("\n".join(prompt_lines))

        header_lines.append(
            f"| {repo} | #{pr_number} | {findings_total} | `{prompt_file}` | `{comments_json_file}` |"
        )

    plan_md.write_text("\n".join(header_lines) + "\n")

    print()
    print("DeepSeek fix queue prepared:")
    print(f"- Follow-up JSON: {followup_json}")
    print(f"- Follow-up Markdown: {followup_md}")
    print(f"- Actionable JSON: {actionable_json}")
    print(f"- Actionable Markdown: {actionable_md}")
    print(f"- Agent prompt files: {prompt_dir}")
    print(f"- Queue summary: {plan_md}")
    print()
    print("Suggested execution:")
    print(f"1. Open each repo listed in {plan_md}.")
    print("2. Run the repo agent with the corresponding prompt file.")
    print("3. Re-run this command after pushing fixes to verify actionable count drops to zero.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc))
