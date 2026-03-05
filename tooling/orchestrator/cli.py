from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import subprocess
import time

from .agent_profiles import list_profiles, resolve_profile
from .execution_bridge import execute_repo_handoffs
from .iteration_runner import run_once
from .models import now_iso
from .planning_pipeline import run_planning_pipeline
from .planner import merge_work_items, parse_roadmap_markdown
from .review_gate import review_repo_items
from .roadmap_id_config import load_roadmap_config
from .state_store import append_event, ensure_layout, load_state, paths, read_events, run_lock, save_state
from .tickets import (
    check_stage_label_consistency,
    expand_repo_issues,
    reset_repo_issues,
    sync_repo_issues,
)


def _default_core_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_repo_for_roadmap(roadmap: Path) -> list[str]:
    cfg = load_roadmap_config()
    mapped = cfg.repo_for_roadmap(roadmap.name)
    if mapped:
        return [mapped]

    name = roadmap.name
    if "tv7-fastapi-backend" in name:
        return ["tv7-fastapi-backend"]
    if "tv7-flutter-studio" in name:
        return ["tv7-flutter-studio"]
    if "tv7-astro-site" in name:
        return ["tv7-astro-site"]
    if "tv7-axum-engine" in name:
        return ["tv7-axum-engine"]
    return ["tv7-core"]


def _discover_roadmaps(core_dir: Path) -> list[Path]:
    root = core_dir / "docs" / "roadmaps"
    files: list[Path] = []
    for p in sorted(root.glob("tv7-*.md")):
        if p.is_file():
            files.append(p)
    core_roadmap = root / "core" / "agent-orchestration-roadmap.md"
    if core_roadmap.is_file():
        files.append(core_roadmap)
    return files


def _default_batch_id(core_dir: Path) -> str:
    generated = f"manual-{now_iso().replace('+00:00', 'z').replace(':', '').replace('-', '')}"
    result = subprocess.run(
        ["git", "-C", str(core_dir), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return generated
    branch = result.stdout.strip()
    prefix = "codex/batch-tv7-core-"
    if branch.startswith(prefix):
        return branch[len(prefix):]
    return generated


def _default_graph_batch_code() -> str:
    cfg = load_roadmap_config()
    return cfg.batch_for_roadmap("project-conductor-roadmap.md")


def _write_ticket_sync_report(
    *,
    core_dir: Path,
    mode: str,
    summary: dict[str, int | str],
    actions: list[dict[str, str]],
) -> tuple[Path, Path]:
    report_dir = paths(core_dir)["root"] / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "").replace("-", "").replace("+00:00", "z")
    json_path = report_dir / f"ticket-sync-{mode}-{stamp}.json"
    md_path = report_dir / f"ticket-sync-{mode}-{stamp}.md"

    json_path.write_text(json.dumps({"summary": summary, "actions": actions}, indent=2) + "\n")

    lines = [
        f"# Ticket Sync Report ({mode})",
        "",
        "## Summary",
        "",
    ]
    for k, v in summary.items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(
        [
            "",
            "## Actions",
            "",
            "| Action | Repo | Item ID | Title | URL | Note |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for a in actions:
        lines.append(
            f"| {a.get('action','')} | {a.get('repo','')} | {a.get('item_id','')} | "
            f"{a.get('title','')} | {a.get('url','')} | {a.get('note','')} |"
        )
    md_path.write_text("\n".join(lines) + "\n")
    return json_path, md_path


def _extract_json_list(raw: str) -> list[dict[str, object]]:
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
    except Exception:
        pass
    first = text.find("[")
    last = text.rfind("]")
    if first >= 0 and last > first:
        try:
            parsed = json.loads(text[first : last + 1])
            if isinstance(parsed, list):
                return [x for x in parsed if isinstance(x, dict)]
        except Exception:
            return []
    return []


def _ops_hint(
    *,
    row: dict[str, object],
    execute_run: dict[str, object] | None,
) -> str:
    status = str(row.get("status", "")).strip().lower()
    activity = str(row.get("activity", "")).strip().lower()
    ci_status = str(row.get("ciStatus", "")).strip().lower()
    review_decision = str(row.get("reviewDecision", "")).strip().lower()
    pending_threads_raw = row.get("pendingThreads")
    try:
        pending_threads = int(pending_threads_raw) if pending_threads_raw is not None else 0
    except Exception:
        pending_threads = 0

    if status in {"spawning"}:
        bootstrap = str((execute_run or {}).get("spawn_bootstrap", "")).strip()
        if bootstrap:
            return (
                f"Startup pending (bootstrap={bootstrap}). "
                "If stuck, attach tmux and confirm prompts."
            )
        return "Startup pending. If stuck, run `ao send --no-wait <session> 1`."
    if status in {"killed", "failed", "exited"} or activity in {"exited"}:
        return "Session stopped. Re-run execute handoff with --force."
    if ci_status in {"failed", "failure", "error"}:
        return "CI failed. Trigger fix loop for this PR."
    if pending_threads > 0:
        return f"{pending_threads} review thread(s) pending. Address reviewer comments."
    if review_decision in {"changes_requested", "request_changes"}:
        return "Review changes requested. Run follow-up fix pass."
    if status in {"working"}:
        return "Agent is running."
    if status in {"pr_open", "review_pending"}:
        return "PR open. Monitor CI/review."
    if status in {"approved", "mergeable"}:
        return "Ready to merge after policy checks."
    if status in {"merged"}:
        return "Completed."
    return "Check session output for next action."


def cmd_ops_status(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    def _norm(value: object) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if text.lower() == "none":
            return ""
        return text

    repo_filters: set[str] = set()
    for raw in args.repo or []:
        for part in str(raw).split(","):
            token = part.strip()
            if token:
                repo_filters.add(token)

    ao_cmd = str(args.ao_command or "ao").strip() or "ao"
    result = subprocess.run(
        [ao_cmd, "status", "--json"],
        cwd=core_dir.parent,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Failed to query AO status with `{ao_cmd}`.")
        if result.stderr.strip():
            print(result.stderr.strip())
        return 1

    sessions = _extract_json_list(result.stdout)
    if repo_filters:
        sessions = [row for row in sessions if str(row.get("project", "")).strip() in repo_filters]

    agent_runs = state.get("agent_runs", [])
    latest_execute_by_session: dict[str, dict[str, object]] = {}
    if isinstance(agent_runs, list):
        for run in agent_runs:
            if not isinstance(run, dict):
                continue
            if str(run.get("run_type", "")).strip() != "execute_handoff":
                continue
            session_id = str(run.get("session_id", "")).strip()
            if not session_id:
                continue
            latest_execute_by_session[session_id] = run

    rows: list[dict[str, object]] = []
    for row in sessions:
        session = str(row.get("name", "")).strip()
        execute_run = latest_execute_by_session.get(session)
        hint = _ops_hint(row=row, execute_run=execute_run)
        rows.append(
            {
                "session": session,
                "project": _norm(row.get("project", "")),
                "status": _norm(row.get("status", "")),
                "activity": _norm(row.get("activity", "")),
                "issue": _norm(row.get("issue", "")),
                "branch": _norm(row.get("branch", "")),
                "last_activity": _norm(row.get("lastActivity", "")),
                "pr": _norm(row.get("pr", "")) or _norm(row.get("prNumber", "")),
                "ci_status": _norm(row.get("ciStatus", "")),
                "review_decision": _norm(row.get("reviewDecision", "")),
                "pending_threads": row.get("pendingThreads"),
                "spawn_health": str((execute_run or {}).get("spawn_health", "")).strip(),
                "spawn_bootstrap": str((execute_run or {}).get("spawn_bootstrap", "")).strip(),
                "hint": hint,
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"{'SESSION':<16} {'PROJECT':<18} {'STATUS':<12} {'ISSUE':<8} {'BRANCH':<20} HINT")
    print(f"{'-'*16:<16} {'-'*18:<18} {'-'*12:<12} {'-'*8:<8} {'-'*20:<20} {'-'*60}")
    for row in rows:
        print(
            f"{str(row.get('session',''))[:16]:<16} "
            f"{str(row.get('project',''))[:18]:<18} "
            f"{str(row.get('status',''))[:12]:<12} "
            f"{str(row.get('issue',''))[:8]:<8} "
            f"{str(row.get('branch',''))[:20]:<20} "
            f"{row.get('hint','')}"
        )
    if not rows:
        print("(no sessions)")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    p = ensure_layout(core_dir)
    print("State storage ready:")
    print(f"- root: {p['root']}")
    print(f"- state: {p['state']}")
    print(f"- events: {p['events']}")
    print(f"- runs: {p['runs']}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)

    roadmap_files: list[Path]
    if args.all_roadmaps:
        roadmap_files = _discover_roadmaps(core_dir)
    else:
        roadmap_files = [Path(args.roadmap).resolve()]

    items = []
    for roadmap in roadmap_files:
        if args.default_repos:
            default_repos = [x.strip() for x in str(args.default_repos).split(",") if x.strip()]
        else:
            default_repos = _default_repo_for_roadmap(roadmap)
        items.extend(parse_roadmap_markdown(roadmap, default_repos=default_repos))

    if args.replace_roadmap_items:
        kept = []
        for item in state.get("work_items", []):
            source_file = str(item.get("source_file", ""))
            if "/docs/roadmaps/" in source_file.replace("\\", "/"):
                continue
            kept.append(item)
        state["work_items"] = kept

    created, updated = merge_work_items(state, items)
    save_state(core_dir, state)
    append_event(
        core_dir,
        "plan.sync",
        "Synchronized work items from roadmap files",
        {
            "created": created,
            "updated": updated,
            "roadmaps": [str(x) for x in roadmap_files],
            "replace_roadmap_items": bool(args.replace_roadmap_items),
        },
    )
    print(
        f"Plan sync complete: files={len(roadmap_files)} created={created} "
        f"updated={updated} total={len(state.get('work_items', []))}"
    )
    return 0


def cmd_graph_plan(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    started = time.monotonic()
    mode = "apply" if args.apply else "dry-run"
    progress = bool(args.progress or args.apply)
    idea_file = Path(args.idea_file).resolve()

    if progress:
        print(
            f"[graph-plan] starting mode={mode} idea_file={idea_file} "
            f"default_repo={args.default_repo} roadmap_code={args.roadmap_code or 'auto'} "
            f"batch_code={args.batch_code} default_epic={args.default_epic} "
            f"handoff_expand={bool(args.handoff_expand)} strict_expand={bool(args.strict_expand)} "
            f"limit={int(args.limit)} resume_from={args.resume_from or 'none'} "
            f"dry_run_diff={bool(args.dry_run_diff)}",
            flush=True,
        )

    target_state = state if args.apply else copy.deepcopy(state)
    try:
        run_summary, actions = run_planning_pipeline(
            core_dir=core_dir,
            state=target_state,
            idea_file=idea_file,
            default_repo=str(args.default_repo).strip(),
            roadmap_code=str(args.roadmap_code).strip(),
            batch_code=str(args.batch_code).strip(),
            default_epic=str(args.default_epic).strip(),
            owner=args.owner,
            apply_changes=bool(args.apply),
            handoff_expand=bool(args.handoff_expand),
            strict_expand=bool(args.strict_expand),
            batch_id=str(args.batch_id or "").strip(),
            progress=progress,
            limit=int(args.limit),
            resume_from=str(args.resume_from or "").strip(),
            dry_run_diff=bool(args.dry_run_diff),
        )
    except FileNotFoundError:
        print(f"Missing IDEA file: {idea_file}")
        return 2

    if args.apply:
        save_state(core_dir, state)

    handoff = run_summary.get("handoff", {})
    summary = {
        "mode": mode,
        "idea_file": str(idea_file),
        "ingested": int(run_summary.get("ingested", 0)),
        "work_items_created": int(run_summary.get("work_items_created", 0)),
        "work_items_updated": int(run_summary.get("work_items_updated", 0)),
        "queue_records": int(run_summary.get("queue_records", 0)),
        "queue_created": int(run_summary.get("queue_created", 0)),
        "queue_updated": int(run_summary.get("queue_updated", 0)),
        "handoff_expand": bool(handoff.get("handoff_enabled", False)),
        "handoff_expanded": int(handoff.get("expanded", 0)),
        "handoff_already_expanded": int(handoff.get("already_expanded", 0)),
        "handoff_skipped": int(handoff.get("skipped", 0)),
        "handoff_fallback": int(handoff.get("fallback", 0)),
        "handoff_work_items": int(handoff.get("work_items", 0)),
        "handoff_repo_targets": int(handoff.get("repo_targets", 0)),
        "batch_id": str(args.batch_id or "").strip(),
    }
    report_json, report_md = _write_ticket_sync_report(
        core_dir=core_dir,
        mode=f"graph-plan-{mode}",
        summary=summary,
        actions=actions,
    )
    append_event(
        core_dir,
        "graph.plan",
        f"Graph plan pipeline completed ({mode})",
        {**summary, "report_json": str(report_json), "report_md": str(report_md)},
    )
    print(
        f"Graph plan ({mode}): ingested={summary['ingested']} queue_records={summary['queue_records']} "
        f"handoff_expand={summary['handoff_expand']} handoff_expanded={summary['handoff_expanded']} "
        f"handoff_already_expanded={summary['handoff_already_expanded']}"
    )
    print(f"Report JSON: {report_json}")
    print(f"Report MD: {report_md}")
    print(f"Elapsed: {time.monotonic() - started:.1f}s")
    if args.verbose:
        for a in actions:
            print(
                f"[{a.get('action','')}] repo={a.get('repo','')} "
                f"item={a.get('item_id','')} note={a.get('note','')} url={a.get('url','')}"
            )
    return 0


def cmd_tickets(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    started = time.monotonic()

    if bool(args.list_agent_profiles):
        print("Available agent profiles:")
        for profile in list_profiles():
            print(
                f"- {profile.name}: assess_agent={profile.assess_agent} "
                f"model={profile.model} reasoning={profile.reasoning} "
                f"personality={profile.personality}"
            )
            if profile.notes:
                print(f"  note: {profile.notes}")
        return 0

    profile = resolve_profile(str(args.agent_profile or "").strip())
    assess_agent = str(args.assess_agent or "").strip() or profile.assess_agent
    model = str(args.model or args.codex_model or "").strip() or profile.model
    reasoning = str(args.reasoning or args.codex_reasoning or "").strip() or profile.reasoning
    personality = str(args.personality or args.codex_personality or "").strip() or profile.personality

    progress = bool(args.progress or args.apply)
    repo_filters = list(args.repo or [])
    roadmap_filters = list(args.roadmap or [])
    item_prefix_filters = list(args.item_prefix or [])
    if progress:
        mode = "apply" if args.apply else "dry-run"
        print(
            f"[ticket] starting mode={mode} owner={args.owner} "
            f"profile={profile.name} "
            f"assess={bool(args.assess and args.apply and assess_agent != 'none')} "
            f"assess_agent={assess_agent} model={model} "
            f"strict_assess={args.strict_assess} "
            f"reasoning={reasoning or 'default'} "
            f"batch_id={args.batch_id or 'none'} "
            f"repo_filter={','.join(repo_filters) or 'all'} "
            f"roadmap_filter={','.join(roadmap_filters) or 'all'} "
            f"item_prefix_filter={','.join(item_prefix_filters) or 'all'}",
            flush=True,
        )
    created, linked, skipped, planned, item_count, target_count, actions = sync_repo_issues(
        core_dir=core_dir,
        state=state,
        owner=args.owner,
        apply_changes=args.apply,
        assess_before_create=bool(args.assess and args.apply and assess_agent != "none"),
        assess_agent=assess_agent,
        strict_assess=bool(args.strict_assess),
        agent_profile=profile.name,
        agent_model=model,
        agent_reasoning=reasoning,
        agent_personality=personality,
        assess_timeout_sec=int(args.assess_timeout_sec),
        assess_log_max_chars=int(args.assess_log_max_chars),
        batch_id=str(args.batch_id or "").strip(),
        progress=progress,
        repo_filters=repo_filters,
        roadmap_filters=roadmap_filters,
        item_prefix_filters=item_prefix_filters,
    )
    assessed_count = sum(1 for a in actions if a.get("action") == "assessed")
    fallback_count = sum(1 for a in actions if a.get("action") == "assess_failed_fallback")
    save_state(core_dir, state)
    mode = "apply" if args.apply else "dry-run"
    summary = {
        "mode": mode,
        "work_items": item_count,
        "repo_targets": target_count,
        "created": created,
        "linked_existing": linked,
        "would_create": planned,
        "skipped_no_repo": skipped,
        "assessed": assessed_count,
        "assess_fallback": fallback_count,
        "batch_id": str(args.batch_id or "").strip(),
        "agent_profile": profile.name,
        "assess_agent": assess_agent,
        "model": model,
        "reasoning": reasoning,
        "repo_filter": ",".join(repo_filters),
        "roadmap_filter": ",".join(roadmap_filters),
        "item_prefix_filter": ",".join(item_prefix_filters),
    }
    report_json, report_md = _write_ticket_sync_report(
        core_dir=core_dir,
        mode=mode,
        summary=summary,
        actions=actions,
    )
    append_event(
        core_dir,
        "ticket.sync",
        f"Ticket sync completed ({mode})",
        {**summary, "report_json": str(report_json), "report_md": str(report_md)},
    )
    if target_count == 0:
        print(
            "Ticket sync warning: no repo targets were processed. "
            "Run `make conductor-status` (or `make orchestrator-status`) and verify "
            "`work_items` and `repos` are populated."
        )
    print(
        f"Ticket sync ({mode}): work_items={item_count} repo_targets={target_count} "
        f"created={created} linked_existing={linked} would_create={planned} skipped_no_repo={skipped}"
    )
    print(f"Report JSON: {report_json}")
    print(f"Report MD: {report_md}")
    print(f"Elapsed: {time.monotonic() - started:.1f}s")
    if args.verbose:
        for a in actions:
            print(
                f"[{a.get('action','')}] repo={a.get('repo','')} "
                f"item={a.get('item_id','')} note={a.get('note','')} url={a.get('url','')}"
            )
    return 0


def cmd_expand(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    started = time.monotonic()

    mode = "apply" if args.apply else "dry-run"
    progress = bool(args.progress or args.apply)
    repo_filters = list(args.repo or [])
    roadmap_filters = list(args.roadmap or [])
    item_prefix_filters = list(args.item_prefix or [])
    if progress:
        print(
            f"[expand] starting mode={mode} owner={args.owner} "
            f"strict_expand={bool(args.strict_expand)} "
            f"expand_agent={args.expand_agent or 'auto'} "
            f"batch_id={args.batch_id or 'none'} "
            f"repo_filter={','.join(repo_filters) or 'all'} "
            f"roadmap_filter={','.join(roadmap_filters) or 'all'} "
            f"item_prefix_filter={','.join(item_prefix_filters) or 'all'} "
            f"limit={int(args.limit)} resume_from={args.resume_from or 'none'} "
            f"dry_run_diff={bool(args.dry_run_diff)}",
            flush=True,
        )

    expanded, unchanged, skipped, fallback, item_count, target_count, actions = expand_repo_issues(
        core_dir=core_dir,
        state=state,
        owner=args.owner,
        apply_changes=args.apply,
        strict_expand=bool(args.strict_expand),
        batch_id=str(args.batch_id or "").strip(),
        progress=progress,
        repo_filters=repo_filters,
        roadmap_filters=roadmap_filters,
        item_prefix_filters=item_prefix_filters,
        limit=int(args.limit),
        resume_from=str(args.resume_from or "").strip(),
        dry_run_diff=bool(args.dry_run_diff),
        expand_agent=str(args.expand_agent or "").strip(),
        expand_model=str(args.expand_model or "").strip(),
        expand_reasoning=str(args.expand_reasoning or "").strip(),
        expand_personality=str(args.expand_personality or "").strip(),
        expand_timeout_sec=int(args.expand_timeout_sec),
        expand_log_max_chars=int(args.expand_log_max_chars),
    )
    if args.apply:
        save_state(core_dir, state)

    summary = {
        "mode": mode,
        "work_items": item_count,
        "repo_targets": target_count,
        "expanded": expanded,
        "already_expanded": unchanged,
        "skipped": skipped,
        "fallback": fallback,
        "batch_id": str(args.batch_id or "").strip(),
        "repo_filter": ",".join(repo_filters),
        "roadmap_filter": ",".join(roadmap_filters),
        "item_prefix_filter": ",".join(item_prefix_filters),
        "limit": int(args.limit),
        "resume_from": str(args.resume_from or "").strip(),
        "dry_run_diff": bool(args.dry_run_diff),
        "expand_agent": str(args.expand_agent or "").strip(),
        "expand_model": str(args.expand_model or "").strip(),
    }
    report_json, report_md = _write_ticket_sync_report(
        core_dir=core_dir,
        mode=f"expand-{mode}",
        summary=summary,
        actions=actions,
    )
    append_event(
        core_dir,
        "expand.sync",
        f"Expand sync completed ({mode})",
        {**summary, "report_json": str(report_json), "report_md": str(report_md)},
    )
    print(
        f"Expand sync ({mode}): work_items={item_count} repo_targets={target_count} "
        f"expanded={expanded} already_expanded={unchanged} skipped={skipped} fallback={fallback}"
    )
    print(f"Report JSON: {report_json}")
    print(f"Report MD: {report_md}")
    print(f"Elapsed: {time.monotonic() - started:.1f}s")
    if args.verbose:
        for a in actions:
            print(
                f"[{a.get('action','')}] repo={a.get('repo','')} "
                f"item={a.get('item_id','')} note={a.get('note','')} url={a.get('url','')}"
            )
    return 0


def cmd_expand_label_check(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    started = time.monotonic()
    mode = "apply" if args.apply else "dry-run"
    progress = bool(args.progress or args.apply)
    repo_filters = list(args.repo or [])
    item_prefix_filters = list(args.item_prefix or [])

    if progress:
        print(
            f"[expand-label-check] starting mode={mode} owner={args.owner} "
            f"repo_filter={','.join(repo_filters) or 'all'} "
            f"item_prefix_filter={','.join(item_prefix_filters) or 'all'}",
            flush=True,
        )

    checked, drift, fixed, actions = check_stage_label_consistency(
        core_dir=core_dir,
        state=state,
        owner=args.owner,
        apply_changes=args.apply,
        progress=progress,
        repo_filters=repo_filters,
        item_prefix_filters=item_prefix_filters,
    )

    summary = {
        "mode": mode,
        "checked": checked,
        "drift": drift,
        "fixed": fixed,
        "repo_filter": ",".join(repo_filters),
        "item_prefix_filter": ",".join(item_prefix_filters),
    }
    report_json, report_md = _write_ticket_sync_report(
        core_dir=core_dir,
        mode=f"expand-label-check-{mode}",
        summary=summary,
        actions=actions,
    )
    append_event(
        core_dir,
        "expand.label_check",
        f"Expand label check completed ({mode})",
        {**summary, "report_json": str(report_json), "report_md": str(report_md)},
    )
    print(
        f"Expand label check ({mode}): checked={checked} drift={drift} fixed={fixed}"
    )
    print(f"Report JSON: {report_json}")
    print(f"Report MD: {report_md}")
    print(f"Elapsed: {time.monotonic() - started:.1f}s")
    if args.verbose:
        for a in actions:
            print(
                f"[{a.get('action','')}] repo={a.get('repo','')} "
                f"item={a.get('item_id','')} note={a.get('note','')} url={a.get('url','')}"
            )
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    started = time.monotonic()
    mode = "apply" if args.apply else "dry-run"
    progress = bool(args.progress or args.apply)
    repo_filters = list(args.repo or [])
    roadmap_filters = list(args.roadmap or [])
    item_prefix_filters = list(args.item_prefix or [])

    if progress:
        print(
            f"[execute] starting mode={mode} ao_command={args.ao_command} "
            f"policy={args.policy_path or 'default'} batch_id={args.batch_id or 'none'} "
            f"repo_filter={','.join(repo_filters) or 'all'} "
            f"roadmap_filter={','.join(roadmap_filters) or 'all'} "
            f"item_prefix_filter={','.join(item_prefix_filters) or 'all'} "
            f"limit={int(args.limit)} resume_from={args.resume_from or 'none'} "
            f"force={bool(args.force)}",
            flush=True,
        )

    spawned, failed, skipped, planned, item_count, target_count, actions = execute_repo_handoffs(
        core_dir=core_dir,
        state=state,
        apply_changes=bool(args.apply),
        ao_command=str(args.ao_command).strip() or "ao",
        policy_path=str(args.policy_path or "").strip(),
        batch_id=str(args.batch_id or "").strip(),
        progress=progress,
        repo_filters=repo_filters,
        roadmap_filters=roadmap_filters,
        item_prefix_filters=item_prefix_filters,
        limit=int(args.limit),
        resume_from=str(args.resume_from or "").strip(),
        force=bool(args.force),
    )
    if args.apply:
        save_state(core_dir, state)

    summary = {
        "mode": mode,
        "work_items": item_count,
        "repo_targets": target_count,
        "spawned": spawned,
        "failed": failed,
        "skipped": skipped,
        "would_spawn": planned,
        "batch_id": str(args.batch_id or "").strip(),
        "ao_command": str(args.ao_command).strip() or "ao",
        "policy_path": str(args.policy_path or "").strip(),
        "repo_filter": ",".join(repo_filters),
        "roadmap_filter": ",".join(roadmap_filters),
        "item_prefix_filter": ",".join(item_prefix_filters),
        "limit": int(args.limit),
        "resume_from": str(args.resume_from or "").strip(),
        "force": bool(args.force),
    }
    report_json, report_md = _write_ticket_sync_report(
        core_dir=core_dir,
        mode=f"execute-{mode}",
        summary=summary,
        actions=actions,
    )
    append_event(
        core_dir,
        "execute.handoff",
        f"Execution handoff completed ({mode})",
        {**summary, "report_json": str(report_json), "report_md": str(report_md)},
    )
    print(
        f"Execute handoff ({mode}): work_items={item_count} repo_targets={target_count} "
        f"spawned={spawned} failed={failed} skipped={skipped} would_spawn={planned}"
    )
    print(f"Report JSON: {report_json}")
    print(f"Report MD: {report_md}")
    print(f"Elapsed: {time.monotonic() - started:.1f}s")
    if args.verbose:
        for a in actions:
            print(
                f"[{a.get('action','')}] repo={a.get('repo','')} "
                f"item={a.get('item_id','')} note={a.get('note','')} url={a.get('url','')}"
            )
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    started = time.monotonic()
    mode = "apply" if args.apply else "dry-run"
    progress = bool(args.progress or args.apply)
    repo_filters = list(args.repo or [])
    roadmap_filters = list(args.roadmap or [])
    item_prefix_filters = list(args.item_prefix or [])

    include_recommendations_override: bool | None
    if bool(args.hard_only):
        include_recommendations_override = False
    elif bool(args.include_recommendations):
        include_recommendations_override = True
    else:
        include_recommendations_override = None

    if progress:
        print(
            f"[review] starting mode={mode} owner={args.owner} "
            f"max_loops_override={int(args.max_loops)} "
            f"review_policy={args.review_policy_path or 'default'} "
            f"execution_policy={args.execution_policy_path or 'default'} "
            f"include_recommendations={include_recommendations_override if include_recommendations_override is not None else 'policy-default'} "
            f"repo_filter={','.join(repo_filters) or 'all'} "
            f"roadmap_filter={','.join(roadmap_filters) or 'all'} "
            f"item_prefix_filter={','.join(item_prefix_filters) or 'all'} "
            f"limit={int(args.limit)} resume_from={args.resume_from or 'none'}",
            flush=True,
        )

    passed, failed, escalated, skipped, planned, item_count, target_count, actions = review_repo_items(
        core_dir=core_dir,
        state=state,
        owner=args.owner,
        apply_changes=bool(args.apply),
        max_loops_override=int(args.max_loops),
        review_policy_path=str(args.review_policy_path or "").strip(),
        execution_policy_path=str(args.execution_policy_path or "").strip(),
        include_recommendations_override=include_recommendations_override,
        progress=progress,
        repo_filters=repo_filters,
        roadmap_filters=roadmap_filters,
        item_prefix_filters=item_prefix_filters,
        limit=int(args.limit),
        resume_from=str(args.resume_from or "").strip(),
    )
    if args.apply:
        save_state(core_dir, state)

    summary = {
        "mode": mode,
        "work_items": item_count,
        "repo_targets": target_count,
        "passed": passed,
        "failed": failed,
        "escalated": escalated,
        "skipped": skipped,
        "would_review": planned,
        "max_loops_override": int(args.max_loops),
        "review_policy_path": str(args.review_policy_path or "").strip(),
        "execution_policy_path": str(args.execution_policy_path or "").strip(),
        "include_recommendations": (
            include_recommendations_override
            if include_recommendations_override is not None
            else "policy-default"
        ),
        "repo_filter": ",".join(repo_filters),
        "roadmap_filter": ",".join(roadmap_filters),
        "item_prefix_filter": ",".join(item_prefix_filters),
        "limit": int(args.limit),
        "resume_from": str(args.resume_from or "").strip(),
    }
    report_json, report_md = _write_ticket_sync_report(
        core_dir=core_dir,
        mode=f"review-{mode}",
        summary=summary,
        actions=actions,
    )
    append_event(
        core_dir,
        "review.gate",
        f"Review gate completed ({mode})",
        {**summary, "report_json": str(report_json), "report_md": str(report_md)},
    )
    print(
        f"Review gate ({mode}): work_items={item_count} repo_targets={target_count} "
        f"passed={passed} failed={failed} escalated={escalated} skipped={skipped} would_review={planned}"
    )
    print(f"Report JSON: {report_json}")
    print(f"Report MD: {report_md}")
    print(f"Elapsed: {time.monotonic() - started:.1f}s")
    if args.verbose:
        for a in actions:
            print(
                f"[{a.get('action','')}] repo={a.get('repo','')} "
                f"item={a.get('item_id','')} note={a.get('note','')} url={a.get('url','')}"
            )
    return 0


def cmd_tickets_reset(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    started = time.monotonic()
    mode = "apply" if args.apply else "dry-run"
    progress = bool(args.progress or args.apply)
    if progress:
        print(
            f"[ticket-reset] starting mode={mode} owner={args.owner} "
            f"scope={args.scope} scan_open={bool(args.scan_open)} "
            f"batch_id={args.batch_id or 'none'}",
            flush=True,
        )
    closed, planned, skipped, actions = reset_repo_issues(
        core_dir=core_dir,
        state=state,
        owner=args.owner,
        apply_changes=args.apply,
        batch_id=str(args.batch_id or "").strip(),
        scope=args.scope,
        scan_open=bool(args.scan_open),
        progress=progress,
    )
    if args.apply:
        save_state(core_dir, state)
    summary = {
        "mode": mode,
        "scope": args.scope,
        "scan_open": bool(args.scan_open),
        "batch_id": str(args.batch_id or "").strip(),
        "closed": closed,
        "would_close": planned,
        "skipped": skipped,
    }
    report_json, report_md = _write_ticket_sync_report(
        core_dir=core_dir,
        mode=f"reset-{mode}",
        summary=summary,
        actions=actions,
    )
    append_event(
        core_dir,
        "ticket.reset",
        f"Ticket reset completed ({mode})",
        {**summary, "report_json": str(report_json), "report_md": str(report_md)},
    )
    print(
        f"Ticket reset ({mode}): scope={args.scope} scan_open={bool(args.scan_open)} "
        f"batch_id={args.batch_id or 'none'} "
        f"closed={closed} would_close={planned} skipped={skipped}"
    )
    print(f"Report JSON: {report_json}")
    print(f"Report MD: {report_md}")
    print(f"Elapsed: {time.monotonic() - started:.1f}s")
    if args.verbose:
        for a in actions:
            print(
                f"[{a.get('action','')}] repo={a.get('repo','')} "
                f"item={a.get('item_id','')} note={a.get('note','')} url={a.get('url','')}"
            )
    return 0


def cmd_run_once(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)

    try:
        with run_lock(core_dir):
            iteration = run_once(
                core_dir=core_dir,
                state=state,
                max_review_loops=args.max_review_loops,
                agent_retries=args.agent_retries,
                auto_push=not args.no_auto_push,
            )
    except FileExistsError:
        print("Another orchestrator run is active (lock file exists).")
        return 2

    state.setdefault("iterations", []).append(iteration.to_dict())
    save_state(core_dir, state)

    print(f"Iteration {iteration.iteration_id} finished: {iteration.status}")
    print(f"Summary: {iteration.summary_file}")
    if iteration.errors:
        print("Errors:")
        for err in iteration.errors:
            print(f"- {err}")
        return 1
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    state = load_state(core_dir)
    state_path = paths(core_dir)["state"]
    work_items = state.get("work_items", [])
    iterations = state.get("iterations", [])
    agent_runs = state.get("agent_runs", [])
    planning = state.get("planning", {})
    idea_runs = planning.get("idea_runs", []) if isinstance(planning, dict) else []
    intent_queue = planning.get("intent_queue", []) if isinstance(planning, dict) else []
    execute_runs = [
        x for x in agent_runs if isinstance(x, dict) and str(x.get("run_type", "")).strip() == "execute_handoff"
    ] if isinstance(agent_runs, list) else []
    schema = state.get("schema", {})
    idempotency = state.get("idempotency", {})
    idem_keys = idempotency.get("keys", {}) if isinstance(idempotency, dict) else {}
    print(f"State file: {state_path}")
    print(
        f"Schema: {schema.get('name', 'unknown')} "
        f"v{schema.get('version', state.get('version', '?'))}"
    )
    print(f"Work items: {len(work_items)}")
    print(f"Idea runs: {len(idea_runs) if isinstance(idea_runs, list) else 0}")
    print(f"Intent queue records: {len(intent_queue) if isinstance(intent_queue, list) else 0}")
    print(f"Iterations: {len(iterations)}")
    print(f"Agent runs: {len(agent_runs)}")
    print(f"Execution handoffs: {len(execute_runs)}")
    print(f"Idempotency keys: {len(idem_keys) if isinstance(idem_keys, dict) else 0}")
    print()
    print(f"{'ITEM ID':<42} {'STATUS':<12} {'STAGE':<14} {'REPOS':<30} TITLE")
    print(f"{'-'*42:<42} {'-'*12:<12} {'-'*14:<14} {'-'*30:<30} {'-'*40}")
    for item in work_items[-20:]:
        repos = ",".join(item.get("repos", []))[:30]
        print(
            f"{item.get('item_id','')[:42]:<42} "
            f"{item.get('status','')[:12]:<12} "
            f"{str(item.get('stage',''))[:14]:<14} "
            f"{repos:<30} {item.get('title','')}"
        )
    if iterations:
        last = iterations[-1]
        print()
        print("Last iteration:")
        print(json.dumps(last, indent=2))
    return 0


def cmd_events(args: argparse.Namespace) -> int:
    core_dir = Path(args.core_dir).resolve()
    events = read_events(core_dir, limit=args.limit)
    for e in events:
        print(f"{e.get('ts','')} [{e.get('event_type','')}] {e.get('message','')}")
        ctx = e.get("context", {})
        if ctx:
            print(json.dumps(ctx, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TV7 orchestrator CLI (single-run mode).")
    parser.add_argument("--core-dir", default=str(_default_core_dir()), help="Path to tv7-core repository root.")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize orchestrator state directories.")
    p_init.set_defaults(func=cmd_init)

    p_plan = sub.add_parser("plan", help="Sync roadmap tasks into orchestrator work items.")
    p_plan.add_argument(
        "--roadmap",
        default=str(_default_core_dir() / "docs" / "roadmaps" / "core" / "agent-orchestration-roadmap.md"),
        help="Roadmap markdown path to parse.",
    )
    p_plan.add_argument(
        "--default-repos",
        default="",
        help="Optional comma-separated repos applied when task text has no repo hints. If omitted, uses roadmap-file mapping.",
    )
    p_plan.add_argument(
        "--all-roadmaps",
        action="store_true",
        default=True,
        help="Parse all repo roadmap files (default: true).",
    )
    p_plan.add_argument(
        "--single-roadmap",
        dest="all_roadmaps",
        action="store_false",
        help="Parse only --roadmap instead of all roadmap files.",
    )
    p_plan.add_argument(
        "--replace-roadmap-items",
        action="store_true",
        default=True,
        help="Replace existing roadmap-derived work items before merging (default: true).",
    )
    p_plan.add_argument(
        "--no-replace-roadmap-items",
        dest="replace_roadmap_items",
        action="store_false",
        help="Do not remove old roadmap-derived work items before merge.",
    )
    p_plan.set_defaults(func=cmd_plan)

    p_graph = sub.add_parser(
        "graph-plan",
        help="Run idea ingestion -> queue emission -> optional expand handoff pipeline.",
    )
    p_graph.add_argument(
        "--idea-file",
        default=str(_default_core_dir() / "IDEA.md"),
        help="Path to IDEA markdown input file.",
    )
    p_graph.add_argument(
        "--default-repo",
        default="tv7-core",
        help="Default repo hint when IDEA lines do not include repo targets.",
    )
    p_graph.add_argument(
        "--roadmap-code",
        default="",
        help="Optional repo code prefix for generated item IDs (auto from --default-repo if omitted).",
    )
    p_graph.add_argument(
        "--batch-code",
        default=_default_graph_batch_code(),
        help="Batch code for generated item IDs (default: project-conductor roadmap batch).",
    )
    p_graph.add_argument(
        "--default-epic",
        default="01",
        help="Default epic code when IDEA line does not specify epic hint.",
    )
    p_graph.add_argument("--owner", default="TV7-Clip-Studio", help="GitHub org/user owner.")
    p_graph.add_argument(
        "--apply",
        action="store_true",
        help="Persist state changes and apply expand handoff updates.",
    )
    p_graph.add_argument(
        "--handoff-expand",
        action="store_true",
        default=True,
        help="Trigger expand-stage handoff after queue emission (default: true).",
    )
    p_graph.add_argument(
        "--no-handoff-expand",
        dest="handoff_expand",
        action="store_false",
        help="Skip expand-stage handoff and stop after queue emission.",
    )
    p_graph.add_argument(
        "--strict-expand",
        action="store_true",
        default=False,
        help="Fail handoff run if expansion payload validation fails.",
    )
    p_graph.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N expand handoff repo targets (0 means no limit).",
    )
    p_graph.add_argument(
        "--resume-from",
        default="",
        help="Resume expand handoff from this item id/prefix in sorted order (inclusive).",
    )
    p_graph.add_argument(
        "--dry-run-diff",
        action="store_true",
        default=False,
        help="Write expand dry-run diff artifacts into docs/.conductor/reports/expand-diff-*/.",
    )
    p_graph.add_argument(
        "--batch-id",
        default=_default_batch_id(_default_core_dir()),
        help="Batch id used for expand handoff idempotency/labels (default: inferred from core branch).",
    )
    p_graph.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print real-time pipeline progress (apply mode enables this automatically).",
    )
    p_graph.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-action details in stdout in addition to summary/report files.",
    )
    p_graph.set_defaults(func=cmd_graph_plan)

    p_tickets = sub.add_parser("tickets", help="Create/link GitHub issues for work items by repo.")
    p_tickets.add_argument("--owner", default="TV7-Clip-Studio", help="GitHub org/user owner.")
    p_tickets.add_argument("--apply", action="store_true", help="Actually create issues (default is dry-run).")
    p_tickets.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Limit sync to one or more repos (repeat flag or use comma-separated values).",
    )
    p_tickets.add_argument(
        "--roadmap",
        action="append",
        default=[],
        help="Limit sync to roadmap source file(s) by basename or path (repeat/comma-separated supported).",
    )
    p_tickets.add_argument(
        "--item-prefix",
        action="append",
        default=[],
        help="Limit sync to item id prefix(es), e.g. ST-A01 or PY-B01-02.",
    )
    p_tickets.add_argument(
        "--agent-profile",
        default="local_auto_medium",
        help="Assessment profile name (default: local_auto_medium).",
    )
    p_tickets.add_argument(
        "--list-agent-profiles",
        action="store_true",
        default=False,
        help="List available agent profiles and exit.",
    )
    p_tickets.add_argument(
        "--assess-agent",
        choices=["auto", "gemini", "antigravity", "codex", "none"],
        default="",
        help="Override assessment provider. Defaults to the selected agent profile.",
    )
    p_tickets.add_argument(
        "--model",
        default="",
        help="Override model from selected agent profile.",
    )
    p_tickets.add_argument(
        "--reasoning",
        default="",
        help='Override reasoning level from selected agent profile (e.g. "medium").',
    )
    p_tickets.add_argument(
        "--personality",
        default="",
        help="Override personality from selected agent profile.",
    )
    p_tickets.add_argument(
        "--assess",
        action="store_true",
        default=True,
        help="Run assessment before creating issues (apply mode only).",
    )
    p_tickets.add_argument(
        "--no-assess",
        dest="assess",
        action="store_false",
        help="Disable pre-ticket assessment.",
    )
    p_tickets.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-action details in stdout in addition to summary/report files.",
    )
    p_tickets.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print real-time progress updates during ticket sync (apply mode enables this automatically).",
    )
    p_tickets.add_argument(
        "--strict-assess",
        action="store_true",
        default=False,
        help="Fail ticket sync if assessment fails. Default is fallback mode.",
    )
    p_tickets.add_argument(
        "--codex-model",
        default="",
        help="Legacy alias for --model (kept for backward compatibility).",
    )
    p_tickets.add_argument(
        "--codex-reasoning",
        default="",
        help='Legacy alias for --reasoning (kept for backward compatibility).',
    )
    p_tickets.add_argument(
        "--codex-personality",
        default="",
        help="Legacy alias for --personality (kept for backward compatibility).",
    )
    p_tickets.add_argument(
        "--assess-timeout-sec",
        type=int,
        default=300,
        help="Timeout in seconds for each Codex assessment call.",
    )
    p_tickets.add_argument(
        "--assess-log-max-chars",
        type=int,
        default=4000,
        help="Max stdout/stderr characters to keep in assessment log excerpts.",
    )
    p_tickets.add_argument(
        "--batch-id",
        default=_default_batch_id(_default_core_dir()),
        help="Batch id written into created issue bodies/metadata (default: inferred from core branch).",
    )
    p_tickets.set_defaults(func=cmd_tickets)

    p_expand = sub.add_parser("expand", help="Enrich seeded issues with structured expansion sections.")
    p_expand.add_argument("--owner", default="TV7-Clip-Studio", help="GitHub org/user owner.")
    p_expand.add_argument("--apply", action="store_true", help="Actually update issue bodies/labels (default dry-run).")
    p_expand.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Limit expand to one or more repos (repeat flag or use comma-separated values).",
    )
    p_expand.add_argument(
        "--roadmap",
        action="append",
        default=[],
        help="Limit expand to roadmap source file(s) by basename or path (repeat/comma-separated supported).",
    )
    p_expand.add_argument(
        "--item-prefix",
        action="append",
        default=[],
        help="Limit expand to item id prefix(es), e.g. CO-C01-04.",
    )
    p_expand.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N repo targets (0 means no limit).",
    )
    p_expand.add_argument(
        "--resume-from",
        default="",
        help="Resume from this item id/prefix in sorted order (inclusive).",
    )
    p_expand.add_argument(
        "--dry-run-diff",
        action="store_true",
        default=False,
        help="Write unified diff artifacts during dry-run into docs/.conductor/reports/expand-diff-*/.",
    )
    p_expand.add_argument(
        "--strict-expand",
        action="store_true",
        default=False,
        help="Fail expand run if structured payload validation fails; default is fallback mode.",
    )
    p_expand.add_argument(
        "--expand-agent",
        choices=["auto", "gemini", "antigravity", "codex", "none"],
        default="auto",
        help="Expansion provider strategy (default: auto).",
    )
    p_expand.add_argument(
        "--expand-model",
        default="",
        help="Optional model override for expansion provider.",
    )
    p_expand.add_argument(
        "--expand-reasoning",
        default="",
        help='Optional reasoning level for expansion provider (e.g. "medium").',
    )
    p_expand.add_argument(
        "--expand-personality",
        default="",
        help="Optional personality override for expansion provider.",
    )
    p_expand.add_argument(
        "--expand-timeout-sec",
        type=int,
        default=300,
        help="Timeout in seconds for each Codex expansion call.",
    )
    p_expand.add_argument(
        "--expand-log-max-chars",
        type=int,
        default=4000,
        help="Max stdout/stderr characters to keep in expansion log excerpts.",
    )
    p_expand.add_argument(
        "--batch-id",
        default=_default_batch_id(_default_core_dir()),
        help="Batch id used for idempotency key/labels (default: inferred from core branch).",
    )
    p_expand.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print real-time progress updates during expand (apply mode enables this automatically).",
    )
    p_expand.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-action details in stdout in addition to summary/report files.",
    )
    p_expand.set_defaults(func=cmd_expand)

    p_expand_label = sub.add_parser(
        "expand-label-check",
        help="Check/fix stage label consistency for seeded/expanded work items.",
    )
    p_expand_label.add_argument("--owner", default="TV7-Clip-Studio", help="GitHub org/user owner.")
    p_expand_label.add_argument(
        "--apply",
        action="store_true",
        help="Actually fix mismatched stage labels (default dry-run).",
    )
    p_expand_label.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Limit check to one or more repos (repeat flag or comma-separated values).",
    )
    p_expand_label.add_argument(
        "--item-prefix",
        action="append",
        default=[],
        help="Limit check to item id prefix(es).",
    )
    p_expand_label.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print real-time progress updates during label check (apply mode enables this automatically).",
    )
    p_expand_label.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-action details in stdout in addition to summary/report files.",
    )
    p_expand_label.set_defaults(func=cmd_expand_label_check)

    p_execute = sub.add_parser(
        "execute",
        help="Bridge expanded work items into execution runs (`ao spawn <repo> <item_id>`).",
    )
    p_execute.add_argument("--apply", action="store_true", help="Actually run execution handoff (default dry-run).")
    p_execute.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Limit execute to one or more repos (repeat flag or comma-separated values).",
    )
    p_execute.add_argument(
        "--roadmap",
        action="append",
        default=[],
        help="Limit execute to roadmap source file(s) by basename or path (repeat/comma-separated supported).",
    )
    p_execute.add_argument(
        "--item-prefix",
        action="append",
        default=[],
        help="Limit execute to item id prefix(es), e.g. CO-C01-06.",
    )
    p_execute.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N repo targets (0 means no limit).",
    )
    p_execute.add_argument(
        "--resume-from",
        default="",
        help="Resume execute handoff from this item id/prefix in sorted order (inclusive).",
    )
    p_execute.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Ignore execute-stage idempotency key and re-run handoff for matching targets.",
    )
    p_execute.add_argument(
        "--ao-command",
        default="ao",
        help="Execution bridge command name (default: ao).",
    )
    p_execute.add_argument(
        "--policy-path",
        default="",
        help="Optional execution policy TOML path (default: tooling/orchestrator/execution_policy.toml).",
    )
    p_execute.add_argument(
        "--batch-id",
        default=_default_batch_id(_default_core_dir()),
        help="Batch id used for execute idempotency keys (default: inferred from core branch).",
    )
    p_execute.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print real-time progress updates during execute handoff (apply mode enables this automatically).",
    )
    p_execute.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-action details in stdout in addition to summary/report files.",
    )
    p_execute.set_defaults(func=cmd_execute)

    p_review = sub.add_parser(
        "review",
        help="Evaluate DeepSeek/GitHub review signals for executing items and gate lifecycle transitions.",
    )
    p_review.add_argument("--owner", default="TV7-Clip-Studio", help="GitHub org/user owner.")
    p_review.add_argument("--apply", action="store_true", help="Persist review verdicts/stage transitions (default dry-run).")
    p_review.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Limit review gate to one or more repos (repeat flag or comma-separated values).",
    )
    p_review.add_argument(
        "--roadmap",
        action="append",
        default=[],
        help="Limit review gate to roadmap source file(s) by basename or path (repeat/comma-separated supported).",
    )
    p_review.add_argument(
        "--item-prefix",
        action="append",
        default=[],
        help="Limit review gate to item id prefix(es), e.g. CO-C01-07.",
    )
    p_review.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N repo targets (0 means no limit).",
    )
    p_review.add_argument(
        "--resume-from",
        default="",
        help="Resume review gate from this item id/prefix in sorted order (inclusive).",
    )
    p_review.add_argument(
        "--max-loops",
        type=int,
        default=0,
        help="Override max review loops per repo target (0 uses review policy config).",
    )
    p_review.add_argument(
        "--review-policy-path",
        default="",
        help="Optional review policy TOML path (default: tooling/orchestrator/review_policy.toml).",
    )
    p_review.add_argument(
        "--execution-policy-path",
        default="",
        help="Optional execution policy TOML path for task-class detection.",
    )
    p_review.add_argument(
        "--include-recommendations",
        action="store_true",
        default=False,
        help="Treat recommendation-style comments as actionable for this run.",
    )
    p_review.add_argument(
        "--hard-only",
        action="store_true",
        default=False,
        help="Ignore recommendations and only gate on hard/explicit blocking findings.",
    )
    p_review.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print real-time progress updates during review gate (apply mode enables this automatically).",
    )
    p_review.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-action details in stdout in addition to summary/report files.",
    )
    p_review.set_defaults(func=cmd_review)

    p_tickets_reset = sub.add_parser(
        "tickets-reset",
        help="Close orchestrator-linked issues from state (batch-scoped or all linked).",
    )
    p_tickets_reset.add_argument("--owner", default="TV7-Clip-Studio", help="GitHub org/user owner.")
    p_tickets_reset.add_argument("--apply", action="store_true", help="Actually close issues (default is dry-run).")
    p_tickets_reset.add_argument(
        "--scope",
        choices=["batch", "all-linked"],
        default="batch",
        help="Reset scope. 'batch' closes only issues tagged with --batch-id metadata.",
    )
    p_tickets_reset.add_argument(
        "--scan-open",
        action="store_true",
        default=False,
        help="Scan GitHub open issues by orchestrator body marker instead of state-linked issues.",
    )
    p_tickets_reset.add_argument(
        "--batch-id",
        default=_default_batch_id(_default_core_dir()),
        help="Batch id for scope=batch (default: inferred from core branch).",
    )
    p_tickets_reset.add_argument(
        "--progress",
        action="store_true",
        default=False,
        help="Print real-time progress updates during ticket reset (apply mode enables this automatically).",
    )
    p_tickets_reset.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-action details in stdout in addition to summary/report files.",
    )
    p_tickets_reset.set_defaults(func=cmd_tickets_reset)

    p_run = sub.add_parser("run-once", help="Run one full orchestration iteration.")
    p_run.add_argument("--max-review-loops", type=int, default=2, help="Maximum DeepSeek fix loops.")
    p_run.add_argument("--agent-retries", type=int, default=1, help="Retries per repo agent run.")
    p_run.add_argument("--no-auto-push", action="store_true", help="Disable auto-push flag in state metadata.")
    p_run.set_defaults(func=cmd_run_once)

    p_status = sub.add_parser("status", help="Show current orchestrator state.")
    p_status.set_defaults(func=cmd_status)

    p_ops_status = sub.add_parser(
        "ops-status",
        help="Show AO spawned-agent sessions with actionable operator hints.",
    )
    p_ops_status.add_argument(
        "--ao-command",
        default="ao",
        help="AO CLI command name (default: ao).",
    )
    p_ops_status.add_argument(
        "--repo",
        action="append",
        default=[],
        help="Filter sessions by project repo id (repeat flag or comma-separated values).",
    )
    p_ops_status.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit JSON instead of table output.",
    )
    p_ops_status.set_defaults(func=cmd_ops_status)

    p_events = sub.add_parser("events", help="Show recent orchestrator events.")
    p_events.add_argument("--limit", type=int, default=30, help="Number of recent events.")
    p_events.set_defaults(func=cmd_events)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
