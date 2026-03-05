#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MIN_PYTHON = (3, 11)

RE_BOT_AUTHOR = re.compile(
    r"github-actions\[bot\]|chatgpt-codex-connector\[bot\]|chatgpt-codex-connector|deepseek",
    re.IGNORECASE,
)
RE_BOT_BODY = re.compile(r"DeepSeek review|FINAL_VERDICT|AI Summary", re.IGNORECASE)
RE_REJECTED = re.compile(r"FINAL_VERDICT:\s*❌\s*REJECTED|FINAL_VERDICT:\s*REJECTED", re.IGNORECASE)
RE_APPROVED = re.compile(r"FINAL_VERDICT:\s*✅\s*APPROVED|FINAL_VERDICT:\s*APPROVED", re.IGNORECASE)
RE_HARD_ACTION = re.compile(r"request changes|blocking|must fix|before merge", re.IGNORECASE)
RE_RECOMMENDATION = re.compile(
    r"recommendation|recommendations|consider adding|consider|should|could|missing|gap|testing gap|risk",
    re.IGNORECASE,
)
RE_MD_HEADER = re.compile(r"^#{1,6}\s+")
RE_SECTION_LABEL = re.compile(r"^(key changes|risks and considerations|recommendations)\s*:\s*$", re.IGNORECASE)
RE_LEADING_LIST_MARKER = re.compile(r"^\d+\.\s+|^[-*]\s+")


def _require_python() -> None:
    if sys.version_info < MIN_PYTHON:
        need = ".".join(str(p) for p in MIN_PYTHON)
        cur = ".".join(str(p) for p in sys.version_info[:3])
        raise SystemExit(f"Python {need}+ is required (found {cur}).")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_limit(raw: str | None, default: int = 20) -> int:
    try:
        value = int(str(raw or "").strip())
        if value <= 0:
            raise ValueError
        return value
    except Exception:
        print(f"[deepseek-followup] invalid LIMIT `{raw}`; defaulting to {default}.", file=sys.stderr)
        return default


def _gh_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh error"
        raise RuntimeError(f"gh {' '.join(args)} failed: {stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from gh {' '.join(args)}: {exc}") from exc


def _gh_check(args: list[str]) -> None:
    result = subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh error"
        raise RuntimeError(f"gh {' '.join(args)} failed: {stderr}")


def _read_repo_order(config_file: Path) -> list[str]:
    repos: list[str] = []
    for raw in config_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        repo = (parts[0] if parts else "").strip()
        if repo:
            repos.append(repo)
    return repos


def _verdict(body: str) -> str:
    if RE_REJECTED.search(body):
        return "REJECTED"
    if RE_APPROVED.search(body):
        return "APPROVED"
    return "UNKNOWN"


def _actionable(state: str, verdict: str, body: str, include_recommendations: bool) -> bool:
    if state == "CHANGES_REQUESTED":
        return True
    if verdict == "REJECTED":
        return True
    if RE_HARD_ACTION.search(body):
        return True
    if include_recommendations and RE_RECOMMENDATION.search(body):
        return True
    return False


def _summarize(body: str) -> str:
    if not body:
        return ""

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return ""

    for raw in lines:
        line = raw
        lower = line.lower()

        # Skip generic review title and section headings.
        if lower == "deepseek review":
            continue
        if RE_MD_HEADER.match(line) and "deepseek review" in lower:
            continue
        if RE_SECTION_LABEL.match(line):
            continue

        # Normalize markdown list markers and inline formatting.
        line = RE_LEADING_LIST_MARKER.sub("", line)
        line = line.replace("**", "").replace("`", "")
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            return line[:220]

    # Fallback to first non-empty line if every line was filtered.
    fallback = re.sub(r"\s+", " ", lines[0]).strip()
    return fallback[:220]


def _collect_findings(
    owner: str,
    repo: str,
    pr_number: int,
    include_recommendations: bool,
) -> list[dict[str, Any]]:
    reviews = _gh_json([f"api", f"repos/{owner}/{repo}/pulls/{pr_number}/reviews?per_page=100"])
    comments = _gh_json([f"api", f"repos/{owner}/{repo}/issues/{pr_number}/comments?per_page=100"])
    review_comments = _gh_json([f"api", f"repos/{owner}/{repo}/pulls/{pr_number}/comments?per_page=100"])

    findings: list[dict[str, Any]] = []

    def _append(items: list[dict[str, Any]], item_type: str, has_state: bool) -> None:
        for item in items:
            author = ((item.get("user") or {}).get("login") or "").strip()
            body = (item.get("body") or "").strip()
            state = (item.get("state") or "").strip() if has_state else ""
            if not (RE_BOT_AUTHOR.search(author) or RE_BOT_BODY.search(body)):
                continue
            verdict = _verdict(body)
            findings.append(
                {
                    "type": item_type,
                    "id": str(item.get("id", "")),
                    "author": author,
                    "state": state,
                    "body": body,
                    "url": (item.get("html_url") or "").strip(),
                    "verdict": verdict,
                    "action_required": _actionable(state, verdict, body, include_recommendations),
                    "summary": _summarize(body),
                }
            )

    _append(reviews if isinstance(reviews, list) else [], "review", has_state=True)
    _append(comments if isinstance(comments, list) else [], "comment", has_state=False)
    _append(review_comments if isinstance(review_comments, list) else [], "review_comment", has_state=False)
    return findings


def _write_outputs(entries: list[dict[str, Any]], out_json: Path, out_md: Path, branch_prefix: str, pr_state: str, batch_id: str) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    out_json.write_text(json.dumps(entries, indent=2) + "\n")

    md_lines = [
        "# DeepSeek Follow-up",
        "",
        f"Source: branch prefix `{branch_prefix}`, state `{pr_state}`",
    ]
    if batch_id:
        md_lines.append(f"Batch filter: `{batch_id}`")
    md_lines.extend(
        [
            "",
            "| Repo | PR | Action Required | Actionable Findings | URL |",
            "| --- | ---: | :---: | ---: | --- |",
        ]
    )
    for entry in entries:
        md_lines.append(
            f"| {entry['repo']} | #{entry['pr_number']} | {str(entry['action_required']).lower()} | {entry['actionable_count']} | {entry['pr_url']} |"
        )
    out_md.write_text("\n".join(md_lines) + "\n")


def _print_summary(entries: list[dict[str, Any]], out_json: Path, out_md: Path) -> None:
    print("DeepSeek follow-up report written:")
    print(f"- JSON: {out_json}")
    print(f"- Markdown: {out_md}")
    print()
    print(f"{'REPO':<24} {'PR':<6} {'ACTION':<9} {'FINDINGS':<10} URL")
    print(f"{'-' * 24:<24} {'-' * 6:<6} {'-' * 9:<9} {'-' * 10:<10} {'-' * 30}")
    for entry in entries:
        print(
            f"{entry['repo']:<24} #{entry['pr_number']:<5} {str(entry['action_required']).lower():<9} "
            f"{entry['actionable_count']:<10} {entry['pr_url']}"
        )


def main() -> int:
    _require_python()

    script_dir = Path(__file__).resolve().parent
    repo_root = Path(os.environ.get("REPO_ROOT", "..")).resolve()
    config_file = Path(os.environ.get("CONFIG_FILE", str(script_dir / "repos-checks.conf"))).resolve()
    owner = os.environ.get("OWNER", "TV7-Clip-Studio")
    pr_state = os.environ.get("PR_STATE", "open")
    limit = _parse_limit(os.environ.get("LIMIT"), default=20)
    branch_prefix = os.environ.get("BRANCH_PREFIX", "codex/batch")
    batch_id = os.environ.get("BATCH_ID", "")
    only_actionable = _env_bool("ONLY_ACTIONABLE", default=False)
    fail_on_actionable = _env_bool("FAIL_ON_ACTIONABLE", default=False)
    include_recommendations = _env_bool("INCLUDE_RECOMMENDATIONS", default=True)
    out_json = Path(os.environ.get("OUT_JSON", "/tmp/tv7-deepseek-followup.json")).resolve()
    out_md = Path(os.environ.get("OUT_MD", "/tmp/tv7-deepseek-followup.md")).resolve()

    if shutil.which("gh") is None:
        raise SystemExit("Missing required command: gh")
    if not config_file.exists():
        raise SystemExit(f"Missing config file: {config_file}")
    _gh_check(["auth", "status"])

    repo_order = _read_repo_order(config_file)
    entries: list[dict[str, Any]] = []

    for repo in repo_order:
        repo_slug = f"{owner}/{repo}"
        prs = _gh_json(
            [
                "pr",
                "list",
                "--repo",
                repo_slug,
                "--state",
                pr_state,
                "--limit",
                str(limit),
                "--json",
                "number,title,url,headRefName,baseRefName,author",
            ]
        )
        if not isinstance(prs, list):
            continue

        prefix = f"{branch_prefix}-{repo}-"
        filtered_prs = [
            pr
            for pr in prs
            if isinstance(pr, dict)
            and str(pr.get("headRefName", "")).startswith(prefix)
            and (not batch_id or batch_id in str(pr.get("headRefName", "")))
        ]

        for pr in filtered_prs:
            pr_number = int(pr.get("number"))
            findings = _collect_findings(owner, repo, pr_number, include_recommendations)
            actionable_count = sum(1 for f in findings if f.get("action_required"))
            entries.append(
                {
                    "repo": repo,
                    "pr_number": pr_number,
                    "pr_title": pr.get("title", ""),
                    "pr_url": pr.get("url", ""),
                    "head_branch": pr.get("headRefName", ""),
                    "base_branch": pr.get("baseRefName", ""),
                    "findings_count": len(findings),
                    "actionable_count": actionable_count,
                    "action_required": actionable_count > 0,
                    "findings": findings,
                }
            )

    if only_actionable:
        entries = [entry for entry in entries if entry["action_required"]]

    _write_outputs(entries, out_json, out_md, branch_prefix, pr_state, batch_id)
    _print_summary(entries, out_json, out_md)

    actionable_total = sum(1 for entry in entries if entry["action_required"])
    if fail_on_actionable and actionable_total > 0:
        print()
        print(f"Actionable DeepSeek findings detected: {actionable_total}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        raise SystemExit(str(exc))
