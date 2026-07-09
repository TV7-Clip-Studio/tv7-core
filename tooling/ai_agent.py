#!/usr/bin/env python3
"""Run independent local AI reviews and scoped resolution agents for the cockpit."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


CORE_DIR = Path(__file__).resolve().parents[1]
WORKSPACE = CORE_DIR.parent
PROVIDERS = {"gemini", "codex", "deepseek"}
MAX_DIFF_CHARS = 240_000
PROVIDER_TIMEOUT = int(os.environ.get("TV7_AI_PROVIDER_TIMEOUT", "300"))


def run(cmd: list[str], *, cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, check=False)


def configured_repos() -> set[str]:
    config = CORE_DIR / "tooling" / "repos-checks.conf"
    repos = set()
    for raw in config.read_text(encoding="utf-8").splitlines() if config.exists() else []:
        line = raw.strip()
        if line and not line.startswith("#"):
            repos.add(line.split("|", 1)[0].strip())
    return repos


def repo_path(repo: str) -> Path:
    if repo not in configured_repos():
        raise ValueError(f"unknown repository: {repo}")
    path = (WORKSPACE / repo).resolve()
    if not (path / ".git").exists() or path.parent != WORKSPACE.resolve():
        raise ValueError(f"repository checkout unavailable: {repo}")
    return path


def git(path: Path, *args: str) -> str:
    result = run(["git", *args], cwd=path, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def worktree_context(path: Path) -> tuple[str, str, str, str]:
    branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").strip()
    head = git(path, "rev-parse", "HEAD").strip()
    status = git(path, "status", "--porcelain=v1")
    diff = git(path, "diff", "--no-ext-diff", "--unified=3", "HEAD")
    untracked_blocks = []
    for line in status.splitlines():
        if not line.startswith("?? "):
            continue
        rel = line[3:].strip()
        candidate = (path / rel).resolve()
        if candidate.is_file() and str(candidate).startswith(str(path)) and candidate.stat().st_size <= 256_000:
            data = candidate.read_bytes()
            if b"\0" not in data[:1024]:
                untracked_blocks.append(f"=== Untracked: {rel} ===\n{data.decode('utf-8', errors='replace')}")
    context = (diff + "\n\n" + "\n\n".join(untracked_blocks)).strip()[:MAX_DIFF_CHARS]
    fingerprint = hashlib.sha256(f"{head}\n{status}\n{context}".encode()).hexdigest()
    return branch, head, fingerprint, context


def review_context(path: Path, scope: str) -> tuple[str, str, str, str]:
    if scope == "roadmap":
        branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").strip()
        head = git(path, "rev-parse", "HEAD").strip()
        snapshot_path = CORE_DIR / "docs" / ".tmp" / "sync-roadmap-focus.json"
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8")) if snapshot_path.exists() else []
        row = next((item for item in snapshot if item.get("repo") == path.name), {})
        context = json.dumps({
            "repo": path.name,
            "active_slice": row.get("resolved_focus_display"),
            "roadmap_focus": row.get("focus"),
            "next_action": row.get("next_action"),
            "signals": row.get("signals"),
        }, indent=2, default=str)
        fingerprint = hashlib.sha256(f"roadmap\n{head}\n{context}".encode()).hexdigest()
        return branch, head, fingerprint, context
    if scope != "pull_request":
        return worktree_context(path)
    branch = git(path, "rev-parse", "--abbrev-ref", "HEAD").strip()
    head = git(path, "rev-parse", "HEAD").strip()
    base = "origin/main"
    context = git(path, "diff", "--no-ext-diff", "--unified=3", f"{base}...HEAD").strip()[:MAX_DIFF_CHARS]
    fingerprint = hashlib.sha256(f"pull_request\n{head}\n{context}".encode()).hexdigest()
    return branch, head, fingerprint, context


def review_root(repo: str, fingerprint: str) -> Path:
    return CORE_DIR / "docs" / ".tmp" / "reviews" / repo / fingerprint


def load_runs(root: Path) -> list[dict[str, Any]]:
    index = root / "index.json"
    if not index.exists():
        return []
    try:
        payload = json.loads(index.read_text(encoding="utf-8"))
        return payload.get("runs", []) if isinstance(payload.get("runs"), list) else []
    except (OSError, json.JSONDecodeError):
        return []


def load_repo_runs(repo: str) -> list[dict[str, Any]]:
    base = CORE_DIR / "docs" / ".tmp" / "reviews" / repo
    rows: dict[str, dict[str, Any]] = {}
    for index in base.glob("*/index.json") if base.exists() else []:
        for row in load_runs(index.parent):
            if row.get("id"):
                rows[str(row["id"])] = row
    return sorted(rows.values(), key=lambda row: str(row.get("timestamp") or ""))


def extract_json(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S | re.I)
    candidate = fenced.group(1) if fenced else text
    try:
        value = json.loads(candidate.strip())
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    return {"summary": text.strip() or "Model returned no review.", "ready_to_commit": False, "issues": ["Review output was not valid JSON."]}


def deepseek_ready() -> None:
    launcher = Path.home() / ".local" / "bin" / "moonbridge-deepseek"
    if not launcher.exists():
        raise RuntimeError("moonbridge-deepseek launcher is not installed")
    result = run([str(launcher), "check"], cwd=CORE_DIR, timeout=15)
    if result.returncode != 0:
        raise RuntimeError("DeepSeek bridge is unavailable. Run: moonbridge-deepseek start")


def provider_ready(provider: str, path: Path) -> None:
    executable = "gemini" if provider == "gemini" else "codex"
    if not shutil.which(executable):
        raise RuntimeError(f"{executable} CLI is not installed or not available on PATH")
    print(f"[ai-agent] provider={provider} phase=preflight", flush=True)
    result = run([executable, "--version"], cwd=path, timeout=15)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or f"{executable} preflight failed").strip())
    if provider == "deepseek":
        deepseek_ready()


def codex_command(provider: str, path: Path, prompt: str, *, write: bool) -> tuple[list[str], Path]:
    output = Path(tempfile.mkstemp(prefix=f"tv7-{provider}-", suffix=".txt")[1])
    command = [
        "codex", "exec", "--ephemeral", "--color", "never",
        "--sandbox", "danger-full-access" if provider == "deepseek" else ("workspace-write" if write else "read-only"),
        "-C", str(path),
        "-c", 'plugins."github@openai-curated".enabled=false',
        "-o", str(output),
    ]
    if provider == "deepseek":
        command.extend(["--profile", "deepseek"])
    command.append(prompt)
    return command, output


def call_provider(provider: str, path: Path, prompt: str, *, write: bool) -> tuple[str, str]:
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider: {provider}")
    provider_ready(provider, path)
    if provider == "gemini":
        print(f"[ai-agent] provider=gemini phase=running timeout={PROVIDER_TIMEOUT}s", flush=True)
        command = ["gemini", "--skip-trust", "--approval-mode", "auto_edit" if write else "plan", "-p", prompt, "-o", "text"]
        result = run(command, cwd=path, timeout=PROVIDER_TIMEOUT)
        output = result.stdout.strip()
        model = "gemini-cli"
    else:
        print(f"[ai-agent] provider={provider} phase=running timeout={PROVIDER_TIMEOUT}s", flush=True)
        command, output_path = codex_command(provider, path, prompt, write=write)
        try:
            result = run(command, cwd=path, timeout=PROVIDER_TIMEOUT)
            output = output_path.read_text(encoding="utf-8", errors="replace").strip() if output_path.exists() else result.stdout.strip()
        finally:
            output_path.unlink(missing_ok=True)
        model = "moonbridge" if provider == "deepseek" else "codex-default"
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or f"{provider} exited {result.returncode}").strip()[-4000:])
    return output, model


def history_context(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return "No previous reviews exist for this exact worktree fingerprint."
    parts = []
    for item in runs[-8:]:
        parts.append(
            f"Run {item.get('id')} by {item.get('provider')}: {item.get('summary')}\n"
            f"Findings: {json.dumps(item.get('issues', []))}"
        )
    return "\n\n".join(parts)


def rebuild_ledger(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ledger: dict[str, dict[str, Any]] = {}
    for review in runs:
        for issue in review.get("issues", []):
            text = str(issue).strip()
            key = hashlib.sha256(re.sub(r"\s+", " ", text.lower()).encode()).hexdigest()[:12]
            row = ledger.setdefault(key, {"id": key, "text": text, "providers": [], "run_ids": [], "status": "open"})
            if review.get("provider") not in row["providers"]:
                row["providers"].append(review.get("provider"))
            row["run_ids"].append(review.get("id"))
    return list(ledger.values())


def save_review(repo: str, branch: str, head: str, fingerprint: str, provider: str, model: str, report: dict[str, Any], raw: str, parents: list[str], scope: str) -> dict[str, Any]:
    root = review_root(repo, fingerprint)
    runs_dir = root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    run_id = f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}-{provider}"
    issues = [str(item) for item in report.get("issues", []) if str(item).strip()]
    run_row = {
        "id": run_id, "provider": provider, "model": model, "timestamp": timestamp.isoformat(),
        "repo": repo, "branch": branch, "head_sha": head, "fingerprint": fingerprint, "scope": scope,
        "source": "local_agent",
        "summary": str(report.get("summary") or ""), "ready_to_commit": bool(report.get("ready_to_commit")),
        "issues": issues, "parent_run_ids": parents,
    }
    artifact = runs_dir / f"{run_id}.json"
    artifact.write_text(json.dumps({**run_row, "raw_output": raw}, indent=2) + "\n", encoding="utf-8")
    runs = load_runs(root) + [run_row]
    payload = {"repo": repo, "fingerprint": fingerprint, "head_sha": head, "active_run_id": run_id, "runs": runs, "issue_ledger": rebuild_ledger(runs), "updated_at": timestamp.isoformat()}
    (root / "index.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    latest = CORE_DIR / "docs" / ".tmp" / "reviews" / f"{repo}_review_report.json"
    latest.write_text(json.dumps({**payload, **run_row}, indent=2) + "\n", encoding="utf-8")
    return {**payload, **run_row}


def review_prompt(repo: str, branch: str, context: str, runs: list[dict[str, Any]], scope: str) -> str:
    if scope == "roadmap":
        return f"""You are the TV7 technical planner for repository {repo} on branch {branch}.
Assess the active roadmap slice below. Do not edit files. Produce a focused implementation plan grounded in current repository state and prior assessments.

ACTIVE ROADMAP SLICE:
{context}

PRIOR REPOSITORY ASSESSMENTS (use only as historical context):
{history_context(runs)}

Return only JSON:
{{"summary":"2-3 sentence implementation approach","ready_to_commit":false,"issues":["ordered implementation action with affected paths and validation"]}}
"""
    return f"""You are an independent TV7 code reviewer. Review repository {repo} on branch {branch}.
Use previous reviews only as hypotheses. Produce your own assessment and classify earlier findings as corroborated, resolved, contradicted, or unverifiable. Do not edit files.

CURRENT {scope.upper().replace('_', ' ')} CHANGES:
{context or '[clean worktree]'}

PRIOR REPOSITORY ASSESSMENTS (treat stale or different-scope findings only as hypotheses):
{history_context(runs)}

Return only JSON:
{{"summary":"2-3 sentence independent assessment","ready_to_commit":true,"issues":["current unresolved finding with path and evidence"]}}
"""


def run_review(repo: str, provider: str, scope: str) -> None:
    path = repo_path(repo)
    branch, head, fingerprint, context = review_context(path, scope)
    prior = load_repo_runs(repo)
    raw, model = call_provider(provider, path, review_prompt(repo, branch, context, prior, scope), write=False)
    report = extract_json(raw)
    saved = save_review(repo, branch, head, fingerprint, provider, model, report, raw, [row["id"] for row in prior[-8:]], scope)
    print(json.dumps(saved))


def resolve_prompt(repo: str, run_row: dict[str, Any]) -> str:
    issues = "\n".join(f"- {item}" for item in run_row.get("issues", []))
    if run_row.get("scope") == "roadmap":
        return f"""You are the TV7 implementation agent working in {repo}.
Implement the selected roadmap plan below. Inspect current code and repository guidance first. Preserve unrelated user changes. Do not commit or push.

ROADMAP PLAN {run_row.get('id')} ({run_row.get('provider')}):
{issues}

After editing, run the repository's appropriate validation. Your final response must summarize the implementation, files changed, validation results, and remaining work.
"""
    return f"""You are the TV7 implementation agent working in {repo}.
Resolve only the selected review findings below. Inspect current files and tests before editing. Preserve unrelated user changes. Do not commit or push.

FINDINGS FROM REVIEW {run_row.get('id')} ({run_row.get('provider')}):
{issues}

After editing, run the repository's appropriate focused validation. Your final response must summarize findings addressed, files changed, validation commands/results, and any remaining issue.
"""


def run_resolve(repo: str, provider: str, run_id: str | None, run_file: str | None) -> None:
    path = repo_path(repo)
    _, _, fingerprint, _ = worktree_context(path)
    root = review_root(repo, fingerprint)
    runs = load_runs(root)
    selected = None
    if run_file:
        selected = json.loads(Path(run_file).read_text(encoding="utf-8"))
        if str(selected.get("head_sha") or "") != git(path, "rev-parse", "HEAD").strip():
            raise RuntimeError("Selected assessment is stale for the current HEAD")
    else:
        selected = next((row for row in runs if row.get("id") == run_id), None) if run_id else (runs[-1] if runs else None)
    if not selected:
        raise RuntimeError("No matching review exists for the current worktree fingerprint")
    if not selected.get("issues"):
        print("Selected review has no unresolved findings.")
        return
    before = git(path, "status", "--porcelain=v1")
    summary, model = call_provider(provider, path, resolve_prompt(repo, selected), write=True)
    after = git(path, "status", "--porcelain=v1")
    result = {
        "provider": provider, "model": model, "source_run_id": selected.get("id"),
        "worktree_changed": before != after, "summary": summary,
        "status": after.splitlines(),
    }
    print(json.dumps(result, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("review", "resolve"))
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model", required=True, choices=sorted(PROVIDERS))
    parser.add_argument("--run-id")
    parser.add_argument("--run-file")
    parser.add_argument("--scope", choices=("worktree", "pull_request", "roadmap"), default="worktree")
    args = parser.parse_args()
    try:
        if args.action == "review":
            run_review(args.repo, args.model, args.scope)
        else:
            run_resolve(args.repo, args.model, args.run_id, args.run_file)
        return 0
    except Exception as exc:
        print(f"[ai-agent error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
