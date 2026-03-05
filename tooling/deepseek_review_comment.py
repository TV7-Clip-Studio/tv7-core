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


def _extract_changed_code_refs(line: str, changed_files: set[str]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for match in RE_FILE_REF.finditer(str(line or "")):
        raw = str(match.group(1) or "").strip().strip("`")
        canonical = _canonical_file_ref(raw)
        if not canonical or canonical not in changed_files:
            continue
        normalized = canonical
        if ":" in raw:
            suffix = raw.rsplit(":", 1)[-1]
            if suffix.isdigit():
                normalized = f"{canonical}:{suffix}"
        if normalized in seen:
            continue
        seen.add(normalized)
        refs.append(normalized)
    return refs


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


def _extract_findings(raw: str, changed_files: set[str], max_findings: int) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    seen: set[str] = set()
    max_items = max(0, int(max_findings))
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
        refs = _extract_changed_code_refs(cleaned, changed_files)
        if not refs:
            continue
        if cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        findings.append({"summary": cleaned, "code_refs": refs})
        if max_items > 0 and len(findings) >= max_items:
            break
    return findings


def normalize_review_comment(
    *,
    content: str,
    changed_files: Iterable[str],
    max_findings: int = 0,
    max_body_chars: int = 0,
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
            summary = str(item.get("summary", "")).strip()
            code_refs = [str(x).strip() for x in item.get("code_refs", []) if str(x).strip()]
            lines.append(f"{idx}. {summary}")
            lines.append(f"   Code refs: {', '.join(f'`{ref}`' for ref in code_refs)}")
    else:
        lines.append("1. No file-scoped findings with explicit code refs extracted from model output.")
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
        "findings": [str(item.get("summary", "")).strip() for item in findings],
        "finding_code_refs": [item.get("code_refs", []) for item in findings],
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
    parser.add_argument("--max-findings", type=int, default=0, help="Maximum findings to include (0 means no limit).")
    parser.add_argument("--max-body-chars", type=int, default=0, help="Maximum output body length (0 means no truncation).")
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
