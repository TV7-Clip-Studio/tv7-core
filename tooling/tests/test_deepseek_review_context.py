import tempfile
import unittest
from pathlib import Path

from deepseek_review_context import (
    build_current_file_context,
    extract_prior_findings,
    extract_section,
)


class DeepSeekReviewContextTest(unittest.TestCase):
    def test_extracts_only_findings_section(self):
        review = """### Summary
ok

### Findings
- EngineJobPoller can loop forever.
Evidence: forgotten_client/lib/data/local/engine_job_poller.dart:62

### Recommendations
- Consider replacing the MP4 fixture.
"""

        findings = extract_prior_findings(review)

        self.assertEqual(len(findings), 1)
        self.assertIn("EngineJobPoller can loop forever", findings[0].claim)
        self.assertNotIn("MP4 fixture", findings[0].claim)
        self.assertEqual(
            findings[0].file_refs,
            ["forgotten_client/lib/data/local/engine_job_poller.dart:62"],
        )

    def test_no_findings_text_is_empty_checklist(self):
        review = """### Findings
No meaningful findings.

### Recommendations
- Optional cleanup.
"""

        self.assertEqual(extract_prior_findings(review), [])

    def test_section_extraction_stops_at_next_heading(self):
        review = """### Findings
one
two
### Risks
three
"""

        self.assertEqual(extract_section(review, "Findings"), "one\ntwo")

    def test_plain_section_headings_are_supported(self):
        review = """Summary
ok

Findings
Engine bug.
Evidence: forgotten_client/lib/data/local/engine_job_poller.dart:62

Recommendations
Optional cleanup.
"""

        findings = extract_prior_findings(review)

        self.assertEqual(len(findings), 1)
        self.assertIn("Engine bug", findings[0].claim)
        self.assertNotIn("Optional cleanup", findings[0].claim)

    def test_plain_findings_split_on_blank_lines(self):
        review = """Findings
First bug.
Impact: High.
Evidence: a/b.dart:10

Second bug.
Impact: Low.
Evidence: c/d.dart:20

Risks
Something.
"""

        findings = extract_prior_findings(review)

        self.assertEqual(len(findings), 2)
        self.assertIn("First bug", findings[0].claim)
        self.assertIn("Second bug", findings[1].claim)
        self.assertEqual(findings[0].file_refs, ["a/b.dart:10"])
        self.assertEqual(findings[1].file_refs, ["c/d.dart:20"])

    def test_builds_current_context_for_cited_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "forgotten_client/lib/data/local"
            target.mkdir(parents=True)
            file_path = target / "engine_job_poller.dart"
            file_path.write_text("\n".join(f"line {i}" for i in range(1, 101)))
            review = """### Findings
- Poller bug.
Evidence: forgotten_client/lib/data/local/engine_job_poller.dart:50
"""
            findings = extract_prior_findings(review)

            context, attached = build_current_file_context(findings, root, window=2)

            self.assertEqual(
                attached,
                ["forgotten_client/lib/data/local/engine_job_poller.dart"],
            )
            self.assertIn("48: line 48", context)
            self.assertIn("50: line 50", context)
            self.assertIn("52: line 52", context)


if __name__ == "__main__":
    unittest.main()
