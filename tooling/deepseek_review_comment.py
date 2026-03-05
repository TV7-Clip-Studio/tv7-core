#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

RE_VERDICT = re.compile(r"FINAL_VERDICT:\s*(?:[✅❌]\s*)?(APPROVED|REJECTED)", re.IGNORECASE)
RE_CONFIDENCE = re.compile(r"\((\d{1,3})%\)")


def _extract_verdict(raw: str) -> tuple[str, str, str]:
    event = "COMMENT"
    verdict_label = "COMMENT"
    confidence = "unknown"
    for line in str(raw or "").splitlines():
        if "final_verdict" not in line.lower():
            continue
        match = RE_VERDICT.search(line)
        if not match:
            continue
        verdict = match.group(1).strip().upper()
        verdict_label = verdict
        event = "APPROVE" if verdict == "APPROVED" else "REQUEST_CHANGES"
        conf = RE_CONFIDENCE.search(line)
        if conf:
            confidence = f"{min(100, max(0, int(conf.group(1))))}%"
        break
    return event, verdict_label, confidence


def _normalize_model_body(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return "No model narrative was returned."
    # Remove duplicate schema header if present; wrapper heading is always added below.
    lines = [line.rstrip() for line in text.splitlines()]
    if lines and lines[0].strip().lower() in {"deepseek review", "### deepseek review"}:
        lines = lines[1:]
    return "\n".join(lines).strip() or "No model narrative was returned."


def normalize_review_comment(
    *,
    content: str,
    changed_files: Iterable[str],
    max_findings: int = 0,
    max_body_chars: int = 0,
) -> dict[str, object]:
    # Keep signature compatibility with previous versions.
    _ = list(changed_files)
    _ = int(max_findings)

    event, verdict_label, confidence = _extract_verdict(content)
    narrative = _normalize_model_body(content)

    lines = [
        "### DeepSeek review",
        f"- Confidence: {confidence}",
        f"- Final verdict: {verdict_label}",
        "",
        "### Model narrative",
        narrative,
    ]
    if event == "COMMENT":
        lines.extend(
            [
                "",
                "_Parser note: verdict not detected; posted as informational comment._",
            ]
        )

    body = "\n".join(lines).strip()
    body_limit = int(max_body_chars)
    if body_limit > 0 and len(body) > max(200, body_limit):
        body = body[: body_limit - 40].rstrip() + "\n\n_[truncated by workflow]_"

    return {
        "event": event,
        "verdict": verdict_label,
        "confidence": confidence,
        "findings": [],
        "finding_code_refs": [],
        "body": body,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize DeepSeek raw review into a minimal comment wrapper.")
    parser.add_argument("--content-file", required=True, help="Path to file containing raw DeepSeek response text.")
    parser.add_argument(
        "--changed-files-file",
        default="",
        help="Unused compatibility flag (kept for workflow stability).",
    )
    parser.add_argument("--max-findings", type=int, default=0, help="Unused compatibility flag.")
    parser.add_argument("--max-body-chars", type=int, default=0, help="Maximum output body length (0 means no truncation).")
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    content_path = Path(args.content_file)
    content = content_path.read_text(encoding="utf-8", errors="ignore") if content_path.is_file() else ""

    normalized = normalize_review_comment(
        content=content,
        changed_files=[],
        max_findings=int(args.max_findings),
        max_body_chars=int(args.max_body_chars),
    )
    payload = json.dumps(normalized, indent=2)
    if str(args.output_json).strip():
        Path(args.output_json).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
