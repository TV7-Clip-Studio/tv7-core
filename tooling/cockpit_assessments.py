"""Normalize local and GitHub reviews into one cockpit assessment history."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from ai_agent import load_repo_runs, review_context, worktree_context


def _section(body: str, heading: str) -> str:
    match = re.search(
        rf"(?ims)^###?\s+{re.escape(heading)}\s*$\n(.*?)(?=^###?\s+|^##\s+FINAL_VERDICT|\Z)",
        body,
    )
    return match.group(1).strip() if match else ""


def parse_github_deepseek(repo: str, branch: str, pr: dict[str, Any], review: dict[str, Any]) -> dict[str, Any] | None:
    body = str(review.get("body") or "")
    if "DeepSeek review" not in body:
        return None
    commit = str((review.get("commit") or {}).get("oid") or "")
    confidence_match = re.search(r"Confidence:\s*(\d+)%", body, re.I)
    verdict_match = re.search(r"(?:Final verdict|FINAL_VERDICT):[^A-Z]*(APPROVED|REJECTED)", body, re.I)
    recommendation_match = re.search(r"MERGE_RECOMMENDATION:\s*([A-Z_]+)", body)
    confidence = int(confidence_match.group(1)) if confidence_match else None
    verdict = verdict_match.group(1).upper() if verdict_match else "UNKNOWN"
    findings_text = _section(body, "Valid Findings")
    no_findings = not findings_text or "no critical issues found" in findings_text.lower()
    issues = [] if no_findings else [
        re.sub(r"^[-*]\s*", "", line).strip()
        for line in findings_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    submitted = str(review.get("submittedAt") or pr.get("updatedAt") or "")
    review_id = str(review.get("id") or hashlib.sha256(body.encode()).hexdigest()[:12])
    return {
        "id": f"github-pr-{pr.get('number')}-{review_id}",
        "provider": "deepseek",
        "model": "github-actions",
        "source": "github_deepseek",
        "scope": "pull_request",
        "timestamp": submitted,
        "repo": repo,
        "branch": branch,
        "head_sha": commit,
        "pr_number": pr.get("number"),
        "summary": _section(body, "Summary") or findings_text or "GitHub DeepSeek review",
        "ready_to_commit": verdict == "APPROVED",
        "verdict": verdict,
        "confidence": confidence,
        "merge_recommendation": recommendation_match.group(1) if recommendation_match else None,
        "issues": issues,
        "raw_output": body,
        "parent_run_ids": [],
    }


def assessment_history(repo: str, state: dict[str, Any]) -> dict[str, Any]:
    path = Path(state.get("path") or "")
    if not path.is_dir():
        path = Path(__file__).resolve().parents[2] / repo
    branch, head, fingerprint, _ = worktree_context(path)
    fingerprints = {
        scope: review_context(path, scope)[2]
        for scope in ("worktree", "pull_request", "roadmap")
        if scope != "pull_request" or state.get("pr")
    }
    runs = []
    for row in load_repo_runs(repo):
        normalized = {**row}
        normalized.setdefault("source", "local_agent")
        normalized.setdefault("scope", "worktree")
        scope = str(normalized.get("scope") or "worktree")
        normalized["stale"] = (
            str(normalized.get("head_sha") or "") != head
            or str(normalized.get("fingerprint") or "") != fingerprints.get(scope)
        )
        runs.append(normalized)
    pr = state.get("pr") or {}
    for review in pr.get("reviews") or []:
        normalized = parse_github_deepseek(repo, branch, pr, review)
        if normalized:
            normalized["fingerprint"] = fingerprint
            normalized["stale"] = normalized["head_sha"] != head
            runs.append(normalized)
    unique = {str(row.get("id")): row for row in runs if row.get("id")}
    ordered = sorted(unique.values(), key=lambda row: str(row.get("timestamp") or ""))
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=str(path), capture_output=True, text=True, check=False
    ).stdout.strip())
    scope = "worktree" if dirty else "pull_request" if pr else "roadmap"
    current = [row for row in ordered if not row.get("stale") and row.get("scope", "worktree") == scope]
    active = current[-1] if current else None
    pr_runs = [row for row in ordered if not row.get("stale") and row.get("scope") == "pull_request"]
    return {
        "repo": repo,
        "head_sha": head,
        "scope": scope,
        "recommended_scope": scope,
        "available_scopes": ["worktree", *( ["pull_request"] if pr else []), "roadmap"],
        "active_run_id": active.get("id") if active else None,
        "active": active,
        "latest_pr": pr_runs[-1] if pr_runs else None,
        "runs": ordered,
    }


def suggested_commit_message(repo: str, repo_path: Path, state: dict[str, Any]) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=str(repo_path), capture_output=True, text=True, check=False
    ).stdout.lower()
    if "cockpit" in status or "review.py" in status or "sync.py" in status:
        subject = "refine cockpit review workflow" if state.get("pr") else "add cockpit review workflow"
    else:
        title = str((state.get("test_plan") or {}).get("title") or "validated implementation slice")
        subject = title[:1].lower() + title[1:]
    return f"{repo}: {subject}"
