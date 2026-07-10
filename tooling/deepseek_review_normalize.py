#!/usr/bin/env python3
"""Normalize DeepSeek output into the shared GitHub review contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


VERDICT_RE = re.compile(r"FINAL_VERDICT:\s*(?:[✅❌]\s*)?(APPROVED|REJECTED)", re.I)
CONFIDENCE_RE = re.compile(r"\((\d{1,3})%\)")
MERGE_RE = re.compile(r"MERGE_RECOMMENDATION:\s*(MERGE_WITH_WARNING|DO_NOT_MERGE|MERGE)\b", re.I)
SELF_DISPROOF_RE = re.compile(
    r"(?:impact\s*:\s*none|\bfalse alarm\b|\bno issue here\b|"
    r"\bthat's actually\b|\bthe import\b[^.\n]*\bis present\b)",
    re.I,
)


def extract_contract(raw: str) -> tuple[str, int | None, str]:
    verdict_match = VERDICT_RE.search(raw)
    confidence_match = CONFIDENCE_RE.search(raw)
    verdict = verdict_match.group(1).upper() if verdict_match else "COMMENT"
    confidence = min(100, max(0, int(confidence_match.group(1)))) if confidence_match else None
    merge_match = MERGE_RE.search(raw)
    if merge_match:
        recommendation = merge_match.group(1).upper()
    elif verdict == "APPROVED":
        recommendation = "MERGE" if confidence is not None and confidence >= 90 else "MERGE_WITH_WARNING"
    else:
        recommendation = "DO_NOT_MERGE"
    return verdict, confidence, recommendation


def remove_self_disproving_findings(raw: str) -> tuple[str, int]:
    """Remove only findings that explicitly disprove their own claim."""
    section_re = re.compile(
        r"(?P<header>^###\s+(?:Valid\s+)?Findings\s*$)(?P<body>.*?)(?=^###\s+|^##\s+FINAL_VERDICT|\Z)",
        re.I | re.M | re.S,
    )
    removed = 0

    def clean(match: re.Match[str]) -> str:
        nonlocal removed
        body = match.group("body")
        blocks = [block for block in re.split(r"\n\s*\n", body) if block.strip()]
        kept = []
        for block in blocks:
            if SELF_DISPROOF_RE.search(block):
                removed += 1
            else:
                kept.append(block.strip())
        if not kept:
            kept = ["No valid current-head findings."]
        return match.group("header") + "\n\n" + "\n\n".join(kept) + "\n\n"

    return section_re.sub(clean, raw), removed


def normalize_review(raw: str, head_sha: str) -> dict[str, object]:
    verdict, confidence, recommendation = extract_contract(raw)
    narrative, removed = remove_self_disproving_findings(raw.strip())
    event = "APPROVE" if verdict == "APPROVED" else "REQUEST_CHANGES" if verdict == "REJECTED" else "COMMENT"
    confidence_text = f"{confidence}%" if confidence is not None else "unknown"
    body = "\n".join(
        [
            "### DeepSeek review",
            f"- Reviewed SHA: `{head_sha}`",
            f"- Confidence: {confidence_text}",
            f"- Final verdict: {verdict}",
            f"- Merge recommendation: {recommendation}",
            "",
            narrative or "No model narrative was returned.",
            "",
            f"<!-- REVIEWED_SHA: {head_sha} -->",
        ]
    ).strip()
    return {
        "event": event,
        "verdict": verdict,
        "confidence": confidence_text,
        "merge_recommendation": recommendation,
        "removed_self_disproving_findings": removed,
        "body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--head-sha", required=True)
    args = parser.parse_args()
    raw = args.content.read_text(encoding="utf-8", errors="ignore") if args.content.exists() else ""
    args.output.write_text(json.dumps(normalize_review(raw, args.head_sha), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
