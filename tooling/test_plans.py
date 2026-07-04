#!/usr/bin/env python3
"""Shared human validation plans for TV7 repo slices."""

from __future__ import annotations

from typing import Any


def build_test_plan(repo: str, slice_name: str, focus: dict[str, Any] | None = None) -> dict[str, Any]:
    focus = focus or {}
    roadmap = [str(focus.get("id"))] if focus.get("id") else []
    common: dict[str, Any] = {
        "title": slice_name,
        "roadmap_items": roadmap,
        "known_limitations": [],
    }

    if repo == "tv7-engine" and "transcript" in slice_name.lower():
        return {
            **common,
            "roadmap_items": ["EN-A03-01-03", "EN-A05-01-01", "EN-A06-01-04"],
            "where": "Studio > Diagnostics and Studio > Videos > Quick Clip",
            "preconditions": [
                "Start Backend, Engine, and Studio from tv7-core.",
                "Keep transcription unconfigured for the setup-required check.",
                "Optionally configure TV7_ENGINE_WHISPER_BIN and TV7_ENGINE_WHISPER_MODEL for the success path.",
            ],
            "steps": [
                "Open Diagnostics and confirm Engine health is ready while transcription readiness is not_ready.",
                "Open a local imported video without a transcript and launch Quick Clip.",
                "Confirm the app explains that transcript generation is supported after explicit transcription setup.",
                "When Whisper is configured, start transcript generation and poll the Engine job to completion.",
            ],
            "expected": [
                "Missing setup produces TRANSCRIPTION_SETUP_REQUIRED without creating a job or downloading assets.",
                "Configured setup produces a transcript_generate job and a result.transcript_path VTT file.",
                "Engine health remains ready independently of transcription readiness.",
            ],
            "known_limitations": [
                "A missing Whisper runtime/model is an expected setup state, not a failed Engine implementation.",
            ],
        }

    if repo == "tv7-studio":
        return {
            **common,
            "roadmap_items": ["ST-A01-03-01", "ST-A04-01-05", "ST-A01-02-01", "ST-A01-02-02"],
            "where": "Studio > Videos > Quick Clip and Studio > Diagnostics",
            "preconditions": ["Start Backend, Engine, and Studio from tv7-core.", "Use a local imported video without a transcript."],
            "steps": [
                "Open Quick Clip for the local video.",
                "Verify the setup-required message and its Diagnostics/setup action.",
                "With Engine transcription configured, start generation and observe job progress.",
                "Confirm the generated transcript is attached and Quick Clip becomes available.",
            ],
            "expected": [
                "Studio never runs transcription tools directly.",
                "Setup-required, progress, success, and failure states are actionable and do not crash the app.",
                "Diagnostics agrees with the Quick Clip readiness state.",
            ],
            "known_limitations": ["Without configured Whisper assets, only the setup-required path can pass."],
        }

    if repo == "tv7-backend":
        return {
            **common,
            "roadmap_items": ["BE-A01-02-05", "BE-A01-02-06", "BE-A01-02-07"],
            "where": "Studio login/license diagnostics and Backend /admin/cloud-ai",
            "preconditions": ["Start Backend and Postgres.", "Use an active development user."],
            "steps": [
                "Log in through Studio and confirm /api/v1/auth/license responds without a server error.",
                "Inspect cloud AI readiness with zero and positive credit balances.",
                "Request an Engine delegation token and verify normal user tokens cannot call Engine execution.",
                "Inspect /admin/cloud-ai for balances, request status, latency, and provider errors.",
            ],
            "expected": [
                "No provider secret or prompt body appears in logs or responses.",
                "License, quota, and inactive-account states are stable and consistent across endpoints.",
                "Cloud AI metering records success and failure outcomes correctly.",
            ],
            "known_limitations": [],
        }

    if repo == "tv7-core":
        return {
            **common,
            "roadmap_items": ["CO-A01-02-02", "CO-A01-03-02"],
            "where": "Terminal in tv7-core",
            "preconditions": ["All sibling TV7 repositories are present."],
            "steps": [
                "Run make sync and inspect Last 5 plus Next for every repository.",
                "Run make ready REPO=tv7-engine and verify the detected slice and validation summary.",
                "Generate handoffs and confirm Human Validation matches the active repo slices.",
                "Exit and rerun make sync to verify the queue resumes without losing state.",
            ],
            "expected": [
                "Sync does not commit, push, or merge without an explicit human choice.",
                "Pass/fail results are tied to the current HEAD and dirty-state hash.",
                "Stale results are reset when relevant code changes.",
            ],
            "known_limitations": ["Queue state is local under docs/.tmp and is not committed."],
        }

    if repo == "tv7-site":
        return {
            **common,
            "where": "Local Site in desktop and mobile-width browser views",
            "preconditions": ["Start the Site from tv7-core."],
            "steps": ["Visit every changed route.", "Check navigation, responsive layout, hover/focus states, and first-load styling."],
            "expected": ["No layout overlap, FOUC, broken link, or stale product claim is visible."],
            "known_limitations": [],
        }

    return {
        **common,
        "where": f"{repo} local development surface",
        "preconditions": ["Run the repo's configured development dependencies."],
        "steps": ["Exercise the changed behavior and its nearest failure path."],
        "expected": ["The intended behavior works without regressions or unhandled errors."],
        "known_limitations": [],
    }


def markdown_test_plan(plan: dict[str, Any]) -> str:
    lines = [f"- Where: {plan.get('where', '-')}"]
    for heading, key in (
        ("Preconditions", "preconditions"),
        ("Steps", "steps"),
        ("Expected", "expected"),
        ("Known limitations", "known_limitations"),
    ):
        values = [str(value) for value in plan.get(key, [])]
        lines.append(f"- {heading}:")
        lines.extend(f"  {index}. {value}" for index, value in enumerate(values, 1))
        if not values:
            lines.append("  - None.")
    return "\n".join(lines)


def terminal_test_plan(plan: dict[str, Any]) -> str:
    lines = [f"Where: {plan.get('where', '-')}"]
    for heading, key in (
        ("Preconditions", "preconditions"),
        ("Test steps", "steps"),
        ("Expected", "expected"),
        ("Known limitations", "known_limitations"),
    ):
        values = [str(value) for value in plan.get(key, [])]
        lines.append(f"{heading}:")
        lines.extend(f"  {index}. {value}" for index, value in enumerate(values, 1))
        if not values:
            lines.append("  - None.")
    return "\n".join(lines)
