#!/usr/bin/env python3
"""Build structured follow-up context for DeepSeek PR reviews."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


PATH_RE = re.compile(
    r"(?P<path>(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\."
    r"(?:dart|rs|py|toml|yaml|yml|json|md|txt|sh|js|ts|tsx|jsx))"
    r"(?::(?P<line>\d+))?"
)
HEADER_RE = re.compile(r"^\s*#{1,6}\s+(?P<title>.+?)\s*$")
NUMBERED_RE = re.compile(r"^\s*(?:[-*]\s+|\d+[.)]\s+)")
SKIP_PATH_PREFIXES = (".git/", "node_modules/", "target/", "build/", "dist/")
KNOWN_SECTIONS = {
    "summary",
    "follow-up on previous review",
    "findings",
    "risks",
    "recommendations",
    "final_verdict",
}


@dataclass
class PriorFinding:
    id: str
    claim: str
    file_refs: list[str]
    required_evidence_to_still_fail: str
    prior_status_hint: str = "needs_current_verification"


def extract_section(markdown: str, section_name: str) -> str:
    lines = markdown.splitlines()
    start: int | None = None
    start_level: int | None = None
    wanted = section_name.strip().lower()

    def heading(line: str) -> tuple[str, int | None] | None:
        match = HEADER_RE.match(line)
        if match:
            level = len(line) - len(line.lstrip("#"))
            return match.group("title").strip().lower(), level
        stripped = line.strip()
        if stripped.lower() in KNOWN_SECTIONS:
            return stripped.lower(), None
        return None

    for index, line in enumerate(lines):
        parsed = heading(line)
        if not parsed:
            continue
        title, level = parsed
        if title == wanted:
            start = index + 1
            start_level = level
            break

    if start is None:
        return ""

    end = len(lines)
    for index in range(start, len(lines)):
        parsed = heading(lines[index])
        if not parsed:
            continue
        _, level = parsed
        if start_level is None or level is None or level <= start_level:
            end = index
            break

    return "\n".join(lines[start:end]).strip()


def _normalise_claim(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[-*]\s+", "", text)
    text = re.sub(r"^\d+[.)]\s+", "", text)
    return text


def _split_finding_blocks(findings_section: str) -> list[str]:
    paragraph_blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n", findings_section.strip())
        if block.strip()
    ]
    if len(paragraph_blocks) > 1:
        return paragraph_blocks

    blocks: list[str] = []
    current: list[str] = []

    for line in findings_section.splitlines():
        if NUMBERED_RE.match(line) and current:
            blocks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        blocks.append("\n".join(current).strip())

    return [block for block in blocks if block.strip()]


def _file_refs(text: str) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for match in PATH_RE.finditer(text):
        path = match.group("path")
        line = match.group("line")
        if path.startswith(SKIP_PATH_PREFIXES):
            continue
        ref = f"{path}:{line}" if line else path
        if ref not in seen:
            refs.append(ref)
            seen.add(ref)
    return refs


def extract_prior_findings(previous_review: str) -> list[PriorFinding]:
    findings = extract_section(previous_review, "Findings")
    if not findings:
        return []

    lowered = findings.lower()
    if "no meaningful findings" in lowered or "no findings" in lowered:
        return []

    result: list[PriorFinding] = []
    for block in _split_finding_blocks(findings):
        claim = _normalise_claim(block)
        if not claim:
            continue
        refs = _file_refs(block)
        result.append(
            PriorFinding(
                id=f"PF-{len(result) + 1:02d}",
                claim=claim,
                file_refs=refs,
                required_evidence_to_still_fail=(
                    "Current diff or current source context must show the same "
                    "defect still exists. Prior recommendation text alone is not evidence."
                ),
            )
        )

    return result


def _line_numbers(refs: list[str], path: str) -> list[int]:
    lines: list[int] = []
    prefix = f"{path}:"
    for ref in refs:
        if ref.startswith(prefix):
            raw = ref[len(prefix) :]
            if raw.isdigit():
                lines.append(int(raw))
    return sorted(set(lines))


def build_current_file_context(
    findings: list[PriorFinding],
    workspace: Path,
    *,
    total_cap: int = 60000,
    file_cap: int = 14000,
    window: int = 45,
) -> tuple[str, list[str]]:
    workspace = workspace.resolve()
    paths: list[str] = []
    seen_paths: set[str] = set()
    for finding in findings:
        for ref in finding.file_refs:
            path = ref.split(":", 1)[0]
            if path not in seen_paths:
                paths.append(path)
                seen_paths.add(path)

    parts = ["## Current Source Context For Prior Findings"]
    attached: list[str] = []
    used = 0

    for rel_path in paths[:8]:
        safe_path = (workspace / rel_path).resolve()
        if not safe_path.is_file() or not str(safe_path).startswith(str(workspace)):
            continue
        file_lines = safe_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        line_refs = _line_numbers(
            [ref for finding in findings for ref in finding.file_refs],
            rel_path,
        )

        if line_refs:
            ranges: list[tuple[int, int]] = []
            for line in line_refs[:6]:
                start = max(1, line - window)
                end = min(len(file_lines), line + window)
                ranges.append((start, end))
            merged: list[tuple[int, int]] = []
            for start, end in ranges:
                if merged and start <= merged[-1][1] + 1:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            snippet_parts = []
            for start, end in merged:
                body = "\n".join(
                    f"{idx}: {file_lines[idx - 1]}" for idx in range(start, end + 1)
                )
                snippet_parts.append(f"--- {rel_path}:{start}-{end} ---\n{body}")
            snippet = "\n".join(snippet_parts)
        else:
            snippet = "\n".join(
                f"{idx}: {line}" for idx, line in enumerate(file_lines[:160], start=1)
            )

        encoded = snippet.encode("utf-8", errors="ignore")
        if len(encoded) > file_cap:
            snippet = encoded[:file_cap].decode("utf-8", errors="ignore")
            snippet += f"\n[current source context truncated at {file_cap} bytes]"

        block = f"=== Current file: {rel_path} ===\n{snippet}"
        block_bytes = len(block.encode("utf-8", errors="ignore"))
        if used + block_bytes > total_cap:
            parts.append(f"[current source context truncated at {total_cap} bytes]")
            break
        parts.append(block)
        attached.append(rel_path)
        used += block_bytes

    if len(parts) == 1:
        return "", attached
    return "\n\n".join(parts), attached


def render_checklist(findings: list[PriorFinding]) -> str:
    if not findings:
        return "No prior Findings checklist items were extracted."

    parts = ["## Prior Review Checklist"]
    for finding in findings:
        refs = ", ".join(finding.file_refs) if finding.file_refs else "none"
        parts.append(
            "\n".join(
                [
                    f"### {finding.id}",
                    f"- claim: {finding.claim}",
                    f"- file_refs: {refs}",
                    f"- status_hint: {finding.prior_status_hint}",
                    f"- required_evidence_to_still_fail: {finding.required_evidence_to_still_fail}",
                ]
            )
        )
    return "\n\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-review", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--checklist-json", required=True, type=Path)
    parser.add_argument("--checklist-md", required=True, type=Path)
    parser.add_argument("--current-context-md", required=True, type=Path)
    parser.add_argument("--debug-json", required=True, type=Path)
    args = parser.parse_args()

    previous_review = (
        args.previous_review.read_text(encoding="utf-8", errors="ignore")
        if args.previous_review.exists()
        else ""
    )
    findings = extract_prior_findings(previous_review)
    current_context, attached_paths = build_current_file_context(
        findings,
        args.workspace,
    )

    args.checklist_json.write_text(
        json.dumps([asdict(finding) for finding in findings], indent=2) + "\n",
        encoding="utf-8",
    )
    args.checklist_md.write_text(render_checklist(findings) + "\n", encoding="utf-8")
    args.current_context_md.write_text(current_context + "\n", encoding="utf-8")
    args.debug_json.write_text(
        json.dumps(
            {
                "prior_finding_count": len(findings),
                "attached_current_context_paths": attached_paths,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"prior_finding_count={len(findings)}")
    print(
        "attached_current_context_paths="
        + (",".join(attached_paths) if attached_paths else "none")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
