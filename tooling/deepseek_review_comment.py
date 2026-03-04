#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

RE_VERDICT = re.compile(r"FINAL_VERDICT:\s*(?:[✅❌]\s*)?(APPROVED|REJECTED)", re.IGNORECASE)
RE_CONFIDENCE = re.compile(r"\((\d{1,3})%\)")
RE_FILE_REF = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9_+-]+(?::\d+)?)")


def _normalize_path(path: str) -> str:
    return str(path or "").strip().replace("\\", "/").lower()


def _canonical_file_ref(token: str) -> str:
    raw = str(token or "").strip().strip("`")
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    return _normalize_path(raw)


def _load_changed_files(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        token = _normalize_path(line)
        if token:
            out.add(token)
    return out


def _clean_line(line: str) -> str:
    text = str(line or "").strip()
    text = re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _line_has_changed_file_ref(line: str, changed_files: set[str]) -> bool:
    if not changed_files:
        return False
    lowered = _normalize_path(line)
    if any(path in lowered for path in changed_files):
        return True
    for match in RE_FILE_REF.finditer(line):
        token = _canonical_file_ref(match.group(1))
        if token and token in changed_files:
            return True
    return False


def _extract_verdict(raw: str) -> tuple[str, str, str]:
    event = "COMMENT"
    verdict_label = "COMMENT"
    confidence = "unknown"
    match = None
    for line in str(raw or "").splitlines():
        if "final_verdict" not in line.lower():
            continue
        match = RE_VERDICT.search(line)
        if match:
            verdict = match.group(1).strip().upper()
            verdict_label = verdict
            event = "APPROVE" if verdict == "APPROVED" else "REQUEST_CHANGES"
            conf = RE_CONFIDENCE.search(line)
            if conf:
                confidence = f"{min(100, max(0, int(conf.group(1))))}%"
            break
    return event, verdict_label, confidence


def _extract_findings(raw: str, changed_files: set[str], max_findings: int) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    for line in str(raw or "").splitlines():
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if cleaned.lower().startswith("final_verdict:"):
            continue
        if cleaned.startswith("#"):
            continue
        if len(cleaned) < 10:
            continue
        if not _line_has_changed_file_ref(cleaned, changed_files):
            continue
        if cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        findings.append(cleaned[:240])
        if len(findings) >= max(1, max_findings):
            break
    return findings


def normalize_review_comment(
    *,
    content: str,
    changed_files: Iterable[str],
    max_findings: int = 5,
    max_body_chars: int = 4500,
) -> dict[str, object]:
    changed = {_normalize_path(x) for x in changed_files if _normalize_path(x)}
    event, verdict_label, confidence = _extract_verdict(content)
    findings = _extract_findings(content, changed, max_findings=max_findings)

    lines = [
        "### DeepSeek review",
        f"- Confidence: {confidence}",
        f"- Final verdict: {verdict_label}",
        "",
        "### Top findings (changed-file evidence only)",
    ]
    if findings:
        for idx, item in enumerate(findings, start=1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("1. No file-scoped findings extracted from model output.")
    if event == "COMMENT":
        lines.extend(
            [
                "",
                "_Parser note: verdict not detected; posted as informational comment._",
            ]
        )

    body = "\n".join(lines).strip()
    body_limit = max(200, int(max_body_chars))
    if len(body) > body_limit:
        body = body[: body_limit - 40].rstrip() + "\n\n_[truncated by workflow]_"

    return {
        "event": event,
        "verdict": verdict_label,
        "confidence": confidence,
        "findings": findings,
        "body": body,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize DeepSeek raw review into a strict comment schema.")
    parser.add_argument("--content-file", required=True, help="Path to file containing raw DeepSeek response text.")
    parser.add_argument(
        "--changed-files-file",
        default="",
        help="Optional path to newline-delimited changed file list for evidence filtering.",
    )
    parser.add_argument("--max-findings", type=int, default=5, help="Maximum findings to include.")
    parser.add_argument("--max-body-chars", type=int, default=4500, help="Maximum output body length.")
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    content_path = Path(args.content_file)
    changed_path = Path(args.changed_files_file) if str(args.changed_files_file).strip() else None

    content = content_path.read_text(encoding="utf-8", errors="ignore") if content_path.is_file() else ""
    changed = _load_changed_files(changed_path)

    normalized = normalize_review_comment(
        content=content,
        changed_files=changed,
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
