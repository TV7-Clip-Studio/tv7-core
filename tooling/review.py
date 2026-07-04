#!/usr/bin/env python3
"""Push one committed repo branch, ensure a ready PR, and enter the review flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any


GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
RESET = "\033[0m"

REVIEW_DECISION_PAUSE = 0
REVIEW_DECISION_ANOTHER_ROUND = 20


def init_colors() -> None:
    global GREEN, RED, YELLOW, CYAN, RESET
    disable_color = False
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        disable_color = True
    elif not sys.stdout.isatty():
        disable_color = True

    if disable_color:
        GREEN = ""
        RED = ""
        YELLOW = ""
        CYAN = ""
        RESET = ""


@dataclass(frozen=True)
class RepoConfig:
    repo: str
    base: str
    check_command: str
    docs_only_allowed: bool


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check,
        env=merged_env,
    )


def print_step(message: str) -> None:
    print(f"{CYAN}[..]{RESET} {message}")


def print_ok(message: str) -> None:
    print(f"{GREEN}[ok]{RESET} {message}")


def print_warn(message: str) -> None:
    print(f"{YELLOW}[warn]{RESET} {message}")


def fail(message: str) -> None:
    raise SystemExit(f"{RED}[error]{RESET} {message}")


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        fail(f"missing required command: {name}")


def git(repo_path: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo_path, check=check)


def load_repo_config(config_file: Path, repo: str) -> RepoConfig:
    if not config_file.exists():
        fail(f"missing config file: {config_file}")
    for raw in config_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 4:
            continue
        if parts[0] == repo:
            return RepoConfig(
                repo=parts[0],
                base=parts[1] or "main",
                check_command=parts[2],
                docs_only_allowed=parts[3] == "1",
            )
    fail(f"unknown repo: {repo}. Set REPO to one of the repos in {config_file}")


def current_branch(repo_path: Path) -> str:
    return git(repo_path, "rev-parse", "--abbrev-ref", "HEAD", check=True).stdout.strip()


def count_ahead(repo_path: Path, ref: str) -> int:
    result = git(repo_path, "rev-list", "--count", f"{ref}..HEAD")
    if result.returncode != 0:
        return 0
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def ensure_clean(repo_path: Path) -> None:
    dirty = git(repo_path, "status", "--porcelain", check=True).stdout.strip()
    if dirty:
        print(dirty)
        fail("working tree has uncommitted changes. Commit them before running make review.")


def slugify(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def roadmap_branch_name(roadmap_item: str, slice_name: str) -> str:
    item = slugify(roadmap_item)
    suffix = slugify(slice_name)
    if item and suffix:
        return f"{item}-{suffix}"
    if item:
        return item
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"review-{stamp}"


def branch_exists(repo_path: Path, branch: str) -> bool:
    local = git(repo_path, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0
    remote = git(repo_path, "ls-remote", "--exit-code", "--heads", "origin", branch).returncode == 0
    return local or remote


def unique_branch_name(repo_path: Path, preferred: str) -> str:
    if not branch_exists(repo_path, preferred):
        return preferred
    suffix = 2
    while branch_exists(repo_path, f"{preferred}-{suffix}"):
        suffix += 1
    return f"{preferred}-{suffix}"


def ensure_review_branch(
    repo_path: Path,
    cfg: RepoConfig,
    requested: str,
    roadmap_item: str,
    slice_name: str,
) -> str:
    branch = current_branch(repo_path)
    git(repo_path, "fetch", "--quiet", "origin", cfg.base, check=True)
    base_ref = f"origin/{cfg.base}"

    if branch != cfg.base:
        return branch

    ahead = count_ahead(repo_path, base_ref)
    if ahead <= 0:
        fail(f"{cfg.repo} is on {cfg.base} with no local commits to review.")

    preferred = requested.strip() or roadmap_branch_name(roadmap_item, slice_name)
    new_branch = preferred if requested.strip() else unique_branch_name(repo_path, preferred)
    if git(repo_path, "check-ref-format", "--branch", new_branch).returncode != 0:
        fail(f"invalid review branch name: {new_branch}")
    if requested.strip() and branch_exists(repo_path, new_branch):
        fail(f"branch already exists: {new_branch}")

    print_step(f"current branch is {cfg.base} with {ahead} ahead commits; creating {new_branch}")
    git(repo_path, "switch", "-c", new_branch, check=True)
    return new_branch


def run_validation(repo_path: Path, cfg: RepoConfig) -> None:
    if not cfg.check_command:
        print_warn("no validation command configured; skipping local check")
        return
    print_step(f"running validation: {cfg.check_command}")
    result = run(["bash", "-lc", cfg.check_command], cwd=repo_path)
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout[-4000:])
        if result.stderr.strip():
            print(result.stderr[-4000:], file=sys.stderr)
        fail("validation failed; not pushing")
    print_ok("validation passed")


def push_branch(repo_path: Path, branch: str) -> None:
    upstream = git(repo_path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").stdout.strip()
    print_step(f"pushing {branch} to origin/{branch}")
    if upstream != f"origin/{branch}":
        result = run(
            ["git", "push", "-u", "origin", f"HEAD:{branch}"],
            cwd=repo_path,
            env={"TV7_ALLOW_PUSH": "1"},
        )
    else:
        result = run(["git", "push"], cwd=repo_path, env={"TV7_ALLOW_PUSH": "1"})
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        fail("push failed")
    print_ok("branch pushed")


def gh_json(args: list[str], *, cwd: Path | None = None) -> Any:
    result = run(["gh", *args], cwd=cwd)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh error"
        fail(f"gh {' '.join(args)} failed: {stderr}")
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON from gh {' '.join(args)}: {exc}")


def gh_api_list(path: str) -> list[dict[str, Any]]:
    result = run(["gh", "api", path, "--paginate", "--slurp"])
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown gh error"
        fail(f"gh api {path} failed: {stderr}")
    try:
        pages = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON from gh api {path}: {exc}")
    if not isinstance(pages, list):
        return []
    rows: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, list):
            continue
        rows.extend(item for item in page if isinstance(item, dict))
    return rows


def find_pr(owner: str, repo: str, branch: str) -> dict[str, Any] | None:
    rows = gh_json(
        [
            "pr",
            "list",
            "--repo",
            f"{owner}/{repo}",
            "--head",
            branch,
            "--state",
            "open",
            "--limit",
            "1",
            "--json",
            "number,title,url,state,reviewDecision,headRefName,baseRefName,isDraft",
        ]
    )
    if not isinstance(rows, list):
        return None
    return rows[0] if rows else None


def last_commit_title(repo_path: Path) -> str:
    title = git(repo_path, "log", "-1", "--pretty=%s", check=True).stdout.strip()
    return title or "Update TV7 repo"


def recent_commit_body(repo_path: Path) -> str:
    lines = git(repo_path, "log", "--oneline", "-n", "5", check=True).stdout.strip()
    status = git(repo_path, "status", "--short", check=True).stdout.strip()
    body = [
        "Automated ready PR created by `make review`.",
        "",
        "Recent commits:",
        lines or "-",
    ]
    if status:
        body.extend(["", "Local status at PR creation:", "```", status, "```"])
    return "\n".join(body).strip()


def ensure_pr(owner: str, repo_path: Path, cfg: RepoConfig, branch: str) -> dict[str, Any]:
    existing = find_pr(owner, cfg.repo, branch)
    if existing:
        print_ok(f"existing PR #{existing['number']}: {existing['url']}")
        return existing

    print_step("creating ready Pull Request")
    result = run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            f"{owner}/{cfg.repo}",
            "--base",
            cfg.base,
            "--head",
            branch,
            "--title",
            last_commit_title(repo_path),
            "--body",
            recent_commit_body(repo_path),
        ],
        cwd=repo_path,
    )
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        fail("PR creation failed")

    created = find_pr(owner, cfg.repo, branch)
    if not created:
        fail("PR was created but could not be found")
    print_ok(f"created PR #{created['number']}: {created['url']}")
    return created


DEEPSEEK_RE = re.compile(r"(deepseek review|final_verdict|final verdict)", re.IGNORECASE)
VERDICT_RE = re.compile(r"(?:FINAL_VERDICT|Final verdict):\s*(?:[✅❌]\s*)?(APPROVED|REJECTED)", re.IGNORECASE)
CONFIDENCE_RE = re.compile(r"Confidence:\s*(\d{1,3})%", re.IGNORECASE)


def collect_pr_threads(owner: str, repo: str, number: int) -> list[dict[str, Any]]:
    full = f"{owner}/{repo}"
    comments = gh_api_list(f"repos/{full}/issues/{number}/comments")
    reviews = gh_api_list(f"repos/{full}/pulls/{number}/reviews")
    entries: list[dict[str, Any]] = []
    for item in comments:
        body = str(item.get("body") or "")
        if DEEPSEEK_RE.search(body):
            entries.append({"kind": "issue_comment", **item})
    for item in reviews:
        body = str(item.get("body") or "")
        if DEEPSEEK_RE.search(body):
            entries.append({"kind": "review", **item})
    entries.sort(key=lambda row: str(row.get("submitted_at") or row.get("created_at") or ""))
    return entries


def parse_github_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def review_matches_head(entry: dict[str, Any], head_sha: str, head_time: datetime) -> bool:
    commit_id = str(entry.get("commit_id") or "").strip()
    if commit_id and commit_id != head_sha:
        return False
    review_time = parse_github_time(entry.get("submitted_at") or entry.get("created_at"))
    return review_time is not None and review_time >= head_time


def summarize_deepseek(body: str) -> dict[str, str | list[str]]:
    verdict_match = VERDICT_RE.search(body)
    confidence_match = CONFIDENCE_RE.search(body)
    highlights: list[str] = []
    capture = False
    for raw in body.splitlines():
        line = raw.strip()
        lower = line.lower()
        if lower in {"findings", "### findings", "## findings"}:
            capture = True
            continue
        if capture and line.startswith(("#", "risks", "recommendations", "summary")):
            break
        if capture and line.startswith(("-", "*")):
            highlights.append(line.lstrip("-* ").strip())
        if len(highlights) >= 5:
            break
    if not highlights:
        for raw in body.splitlines():
            line = raw.strip()
            if line.startswith(("-", "*")) and "final verdict" not in line.lower():
                highlights.append(line.lstrip("-* ").strip())
            if len(highlights) >= 5:
                break
    return {
        "verdict": verdict_match.group(1).upper() if verdict_match else "UNKNOWN",
        "confidence": f"{confidence_match.group(1)}%" if confidence_match else "unknown",
        "highlights": highlights,
    }


def confidence_value(confidence: Any) -> int | None:
    match = re.search(r"(\d{1,3})", str(confidence or ""))
    if not match:
        return None
    value = int(match.group(1))
    if value < 0 or value > 100:
        return None
    return value


def review_is_approved(review: dict[str, Any], threshold: int) -> bool:
    verdict = str(review.get("verdict") or "").upper()
    confidence = confidence_value(review.get("confidence"))
    return verdict == "APPROVED" and confidence is not None and confidence >= threshold


def print_full_review(review: dict[str, Any]) -> None:
    artifact = Path(str(review.get("artifact") or ""))
    if not artifact.is_file():
        print_warn("DeepSeek review artifact is unavailable.")
        return
    print(f"\n{CYAN}=== Full DeepSeek Review ==={RESET}")
    print(f"Artifact: {artifact}")
    print(artifact.read_text(encoding="utf-8").rstrip())
    print(f"{CYAN}=== End DeepSeek Review ==={RESET}")


def ask_after_review_round(
    owner: str,
    repo_path: Path,
    cfg: RepoConfig,
    repo: str,
    number: int,
    branch: str,
    review: dict[str, Any],
    threshold: int,
) -> int:
    print_full_review(review)
    strong_approval = review_is_approved(review, threshold)
    if strong_approval:
        print(f"\nDeepSeek approved at {review.get('confidence')}; merge is available after human confirmation.")
    else:
        print(
            f"\nDeepSeek did not meet the merge threshold "
            f"({review.get('verdict')} {review.get('confidence')}; required APPROVED {threshold}%+)."
        )
    print("\nNext action:")
    if strong_approval:
        print("  1) Merge Pull Request and delete branch")
        print("  2) Run another Codex round (fresh DeepSeek review only if the PR head changes)")
        print("  3) Keep PR open and return to sync")
        choice = input("Select option [1-3, default: 3]: ").strip() or "3"
        if choice == "1":
            return merge_pr(owner, repo_path, cfg, number, branch)
        if choice == "2":
            print("Starting another Codex review-resolution round in this PR flow.")
            return REVIEW_DECISION_ANOTHER_ROUND
        return REVIEW_DECISION_PAUSE
    print("  1) Run another Codex round (fresh DeepSeek review only if the PR head changes)")
    print("  2) Keep PR open and return to sync")
    choice = input("Select option [1-2, default: 2]: ").strip() or "2"
    if choice == "1":
        print("Starting another Codex review-resolution round in this PR flow.")
        return REVIEW_DECISION_ANOTHER_ROUND
    return REVIEW_DECISION_PAUSE


def write_round_state(
    artifact_dir: Path,
    *,
    round_number: int,
    input_head: str,
    output_head: str,
    review: dict[str, Any],
    outcome: str,
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "round": round_number,
        "input_head": input_head,
        "output_head": output_head,
        "head_changed": input_head != output_head,
        "codex_outcome": outcome,
        "deepseek": {
            "verdict": review.get("verdict"),
            "confidence": review.get("confidence"),
            "commit_id": review.get("commit_id"),
            "submitted_at": review.get("submitted_at") or review.get("created_at"),
        },
    }
    (artifact_dir / "review-state.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_review_artifact(out_dir: Path, repo: str, number: int, entries: list[dict[str, Any]]) -> Path:
    pr_dir = out_dir / repo / f"pr-{number}"
    pr_dir.mkdir(parents=True, exist_ok=True)
    path = pr_dir / f"deepseek-round-{len(entries)}.md"
    latest = entries[-1]
    body = str(latest.get("body") or "").strip()
    header = [
        f"# DeepSeek Review - {repo} PR #{number}",
        "",
        f"- collected_at: {datetime.now(timezone.utc).isoformat()}",
        f"- source_kind: {latest.get('kind')}",
        f"- author: {(latest.get('user') or {}).get('login', '-')}",
        "",
    ]
    path.write_text("\n".join(header) + body + "\n", encoding="utf-8")
    json_path = path.with_suffix(".json")
    json_path.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def wait_for_deepseek(
    *,
    owner: str,
    repo: str,
    number: int,
    out_dir: Path,
    poll_seconds: int,
    poll_interval: int,
    repo_path: Path,
) -> dict[str, Any] | None:
    print_step(f"waiting for DeepSeek review on PR #{number}")
    deadline = time.monotonic() + max(1, poll_seconds)
    head_sha = git(repo_path, "rev-parse", "HEAD", check=True).stdout.strip()
    head_time_text = git(repo_path, "show", "-s", "--format=%cI", "HEAD", check=True).stdout.strip()
    head_time = parse_github_time(head_time_text) or datetime.now(timezone.utc)
    entries: list[dict[str, Any]] = []
    while time.monotonic() <= deadline:
        entries = [
            entry
            for entry in collect_pr_threads(owner, repo, number)
            if review_matches_head(entry, head_sha, head_time)
        ]
        if entries:
            artifact = write_review_artifact(out_dir, repo, number, entries)
            body = str(entries[-1].get("body") or "")
            summary = summarize_deepseek(body)
            print_ok(f"DeepSeek review: {summary['verdict']} ({summary['confidence']})")
            highlights = summary.get("highlights") or []
            if highlights:
                print("Highlights:")
                for item in highlights:
                    print(f"  - {item}")
            print(f"Full review saved to: {artifact}")
            return {
                **summary,
                "artifact": str(artifact),
                "entry": entries[-1],
            }
        remaining = int(deadline - time.monotonic())
        if remaining <= 0:
            break
        time.sleep(min(max(1, poll_interval), remaining))
    print_warn(f"DeepSeek review not found within {poll_seconds}s. Re-run make review REPO={repo} to check again.")
    return None


def run_gated_review_flow(
    conductor_repo: Path,
    repo_path: Path,
    artifact_dir: Path,
    max_rounds: int,
    head_time: str,
    auto_round: bool,
) -> int:
    conductor_script = conductor_repo / "tooling" / "conductor.py"
    if not conductor_script.is_file():
        print_warn(f"Conductor CLI not found at {conductor_script}; PR remains open for manual review.")
        return 0
    python = conductor_repo / ".venv" / "bin" / "python"
    command = [str(python) if python.is_file() else sys.executable, str(conductor_script), "resolve-pr-review", "--repo", str(repo_path)]
    print_step("opening gated DeepSeek resolution flow via Conductor")
    env = os.environ.copy()
    env["TV7_REVIEW_MAX_ROUNDS"] = str(max_rounds)
    env["TV7_REVIEW_HEAD_TIME"] = head_time
    env["TV7_REVIEW_ARTIFACT_DIR"] = str(artifact_dir)
    if auto_round:
        env["TV7_REVIEW_AUTO_ROUND"] = "1"
    result = subprocess.run(command, cwd=str(conductor_repo), env=env)
    if result.returncode != 0:
        print_warn("Conductor review flow did not complete; rerun make review to resume the open PR.")
    return result.returncode


def pr_mergeable(owner: str, repo: str, number: int) -> tuple[bool, str]:
    pr = gh_json([
        "pr",
        "view",
        str(number),
        "--repo",
        f"{owner}/{repo}",
        "--json",
        "mergeStateStatus,state,isDraft,reviewDecision",
    ])
    if not isinstance(pr, dict):
        return False, "PR details unavailable"
    if pr.get("state") != "OPEN":
        return False, f"PR state is {pr.get('state')}"
    if pr.get("isDraft"):
        return False, "PR is draft"
    merge_state = str(pr.get("mergeStateStatus") or "UNKNOWN")
    if merge_state not in {"CLEAN", "HAS_HOOKS", "UNKNOWN"}:
        return False, f"merge state is {merge_state}"
    return True, merge_state


def merge_pr(owner: str, repo_path: Path, cfg: RepoConfig, number: int, branch: str) -> int:
    ok, reason = pr_mergeable(owner, cfg.repo, number)
    if not ok:
        print_warn(f"PR #{number} is not auto-mergeable: {reason}")
        return 0
    print_step(f"auto-merging PR #{number} and deleting branch")
    result = run(
        [
            "gh",
            "pr",
            "merge",
            str(number),
            "--repo",
            f"{owner}/{cfg.repo}",
            "--squash",
            "--delete-branch",
        ],
        cwd=repo_path,
        env={"TV7_ALLOW_PUSH": "1"},
    )
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout)
        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)
        print_warn("auto-merge failed; PR remains open")
        return 0
    print_ok(f"merged PR #{number} and deleted remote branch {branch}")
    return 0


def list_configured_repos(config_file: Path) -> list[RepoConfig]:
    if not config_file.exists():
        return []
    configs = []
    for raw in config_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 4:
            continue
        configs.append(RepoConfig(
            repo=parts[0],
            base=parts[1] or "main",
            check_command=parts[2],
            docs_only_allowed=parts[3] == "1"
        ))
    return configs


def main() -> int:
    init_colors()
    repo = os.environ.get("REPO", "").strip()
    repo_root = Path(os.environ.get("REPO_ROOT", "..")).resolve()
    config_file = Path(os.environ.get("CONFIG_FILE", "tooling/repos-checks.conf")).resolve()

    if not repo:
        if not sys.stdin.isatty():
            fail("REPO is required, for example: make review REPO=tv7-engine")

        configs = list_configured_repos(config_file)
        if not configs:
            fail("no repositories configured in config file")

        print("\nSelect a repository to run review:")
        for idx, cfg in enumerate(configs, 1):
            r_path = repo_root / cfg.repo
            status = "missing"
            if (r_path / ".git").is_dir():
                branch = git(r_path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
                ahead = count_ahead(r_path, f"origin/{cfg.base}")
                if branch != cfg.base:
                    status = f"{CYAN}{branch}{RESET} ({YELLOW}{ahead} ahead{RESET})"
                elif ahead > 0:
                    status = f"{CYAN}{cfg.base}{RESET} ({YELLOW}{ahead} ahead{RESET})"
                else:
                    status = f"{GREEN}clean {cfg.base}{RESET}"
            print(f"  {idx}) {cfg.repo:<15} [{status}]")
        print(f"  {len(configs) + 1}) Exit")

        try:
            choice = input(f"Select option [1-{len(configs) + 1}]: ").strip()
            if not choice or choice == str(len(configs) + 1):
                return 0
            if not choice.isdigit() or not 1 <= int(choice) <= len(configs):
                fail("invalid selection")
            repo = configs[int(choice) - 1].repo
        except (KeyboardInterrupt, EOFError):
            print()
            return 0

    require_tool("git")
    require_tool("gh")
    if run(["gh", "auth", "status"]).returncode != 0:
        fail("gh auth is missing")

    owner = os.environ.get("OWNER", "TV7-Clip-Studio")
    reviews_dir = Path(os.environ.get("REVIEWS_DIR", "docs/code-reviews")).resolve()
    branch_request = os.environ.get("REVIEW_BRANCH", "").strip()
    roadmap_item = os.environ.get("ROADMAP_ITEM", "").strip()
    slice_name = os.environ.get("REVIEW_SLICE", "").strip()
    review_resolve = os.environ.get("REVIEW_RESOLVE", "1") == "1"
    review_auto_round = os.environ.get("REVIEW_AUTO_ROUND", "0") == "1"
    review_automerge = os.environ.get("REVIEW_AUTOMERGE", "0") == "1"
    review_human_decision = os.environ.get("REVIEW_HUMAN_DECISION", "0") == "1"
    conductor_repo = Path(os.environ.get("CONDUCTOR_REPO", str(repo_root / "tv7-conductor"))).resolve()
    max_rounds = max(1, min(2, int(os.environ.get("REVIEW_MAX_ROUNDS", "1"))))
    automerge_threshold = max(0, min(100, int(os.environ.get("REVIEW_AUTOMERGE_THRESHOLD", "90"))))
    poll_seconds = max(1, int(os.environ.get("REVIEW_POLL_SECONDS", "600")))
    poll_interval = max(1, int(os.environ.get("REVIEW_POLL_INTERVAL", "15")))

    cfg = load_repo_config(config_file, repo)
    repo_path = repo_root / repo
    if not (repo_path / ".git").is_dir():
        fail(f"repo not found: {repo_path}")

    print(f"{CYAN}=== TV7 Review Assistant ==={RESET}")
    print(f"Repo: {repo}")

    ensure_clean(repo_path)
    branch = ensure_review_branch(
        repo_path,
        cfg,
        branch_request,
        roadmap_item,
        slice_name or last_commit_title(repo_path).removeprefix(f"{repo}:").strip(),
    )
    run_validation(repo_path, cfg)
    push_branch(repo_path, branch)
    pr = ensure_pr(owner, repo_path, cfg, branch)
    number = int(pr["number"])
    print(f"PR: {pr['url']}")

    round_number = 0
    review: dict[str, Any] | None = None
    while True:
        try:
            pr_status = gh_json([
                "pr",
                "view",
                str(number),
                "--repo",
                f"{owner}/{repo}",
                "--json",
                "state",
            ])
            if pr_status and isinstance(pr_status, dict) and pr_status.get("state") != "OPEN":
                print_ok(f"PR #{number} is already {pr_status.get('state').lower()}. Review flow complete.")
                return 0
        except Exception:
            pass

        if review is None:
            review = wait_for_deepseek(
                owner=owner,
                repo=repo,
                number=number,
                out_dir=reviews_dir,
                poll_seconds=poll_seconds,
                poll_interval=poll_interval,
                repo_path=repo_path,
            )
            if review is None:
                return 0
        if review_human_decision and not review_resolve and sys.stdin.isatty():
            return ask_after_review_round(owner, repo_path, cfg, repo, number, branch, review, automerge_threshold)
        if review_automerge and review_is_approved(review, automerge_threshold) and not review_resolve:
            return merge_pr(owner, repo_path, cfg, number, branch)
        if review_resolve and sys.stdin.isatty():
            round_number += 1
            head_time = git(repo_path, "show", "-s", "--format=%cI", "HEAD", check=True).stdout.strip()
            input_head = git(repo_path, "rev-parse", "HEAD", check=True).stdout.strip()
            artifact_dir = reviews_dir / repo / f"pr-{number}"
            rc = run_gated_review_flow(
                conductor_repo,
                repo_path,
                artifact_dir,
                max_rounds,
                head_time,
                review_auto_round,
            )
            if rc != 0:
                write_round_state(
                    artifact_dir,
                    round_number=round_number,
                    input_head=input_head,
                    output_head=input_head,
                    review=review,
                    outcome="failed",
                )
                return rc
            output_head = git(repo_path, "rev-parse", "HEAD", check=True).stdout.strip()
            head_changed = output_head != input_head
            write_round_state(
                artifact_dir,
                round_number=round_number,
                input_head=input_head,
                output_head=output_head,
                review=review,
                outcome="changes_pushed" if head_changed else "no_changes",
            )
            try:
                pr_status = gh_json([
                    "pr",
                    "view",
                    str(number),
                    "--repo",
                    f"{owner}/{repo}",
                    "--json",
                    "state",
                ])
                if pr_status and isinstance(pr_status, dict) and pr_status.get("state") != "OPEN":
                    print_ok(f"PR #{number} is now {pr_status.get('state').lower()}. Review flow complete.")
                    return 0
            except Exception:
                pass

            if review_human_decision or review_automerge:
                if head_changed:
                    refreshed = wait_for_deepseek(
                        owner=owner,
                        repo=repo,
                        number=number,
                        out_dir=reviews_dir,
                        poll_seconds=poll_seconds,
                        poll_interval=poll_interval,
                        repo_path=repo_path,
                    )
                    if refreshed is None:
                        print_warn(f"review fixes were pushed; a fresh DeepSeek review is still pending on PR #{number}.")
                        return 0
                    review = refreshed
                else:
                    print_warn(
                        "Codex made no changes, so the PR head did not change and no fresh DeepSeek review was requested."
                    )
                if review_human_decision and sys.stdin.isatty():
                    decision = ask_after_review_round(
                        owner,
                        repo_path,
                        cfg,
                        repo,
                        number,
                        branch,
                        review,
                        automerge_threshold,
                    )
                    if decision == REVIEW_DECISION_ANOTHER_ROUND:
                        continue
                    return decision
                if review_is_approved(review, automerge_threshold):
                    return merge_pr(owner, repo_path, cfg, number, branch)
                print_warn(
                    "DeepSeek still has concerns after one review round. "
                    f"Verdict: {review.get('verdict')} ({review.get('confidence')})."
                )
                print(f"Next: rerun make review REPO={repo} to run another human-approved round, or inspect PR #{number}.")
                return 0
            return 0
        if review_resolve:
            print_warn(f"interactive resolution skipped without a TTY; rerun make review REPO={repo}")
        break

    print_ok("review flow complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
