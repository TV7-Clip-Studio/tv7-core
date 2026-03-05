from __future__ import annotations

import unittest

from deepseek_review_comment import normalize_review_comment


class DeepseekReviewCommentTests(unittest.TestCase):
    def test_normalizes_approved_with_file_scoped_finding(self) -> None:
        content = """
DeepSeek review
Confidence: 92%
This PR is generally good.
1. Updated token usage in src/pages/index.astro:44 to rely on tv7 palette.
## FINAL_VERDICT: ✅ APPROVED (92%)
""".strip()
        normalized = normalize_review_comment(
            content=content,
            changed_files=["src/pages/index.astro", "src/styles/global.css"],
        )
        self.assertEqual(normalized["event"], "APPROVE")
        self.assertEqual(normalized["confidence"], "92%")
        self.assertEqual(normalized["verdict"], "APPROVED")
        self.assertEqual(len(normalized["findings"]), 1)
        self.assertIn("src/pages/index.astro:44", normalized["body"])
        self.assertIn("Code refs: `src/pages/index.astro:44`", normalized["body"])

    def test_filters_out_non_changed_file_claims(self) -> None:
        content = """
1. Risk in tooling/orchestrator/cli.py:42.
2. Real issue in src/components/Hero.astro:87.
## FINAL_VERDICT: ❌ REJECTED (81%)
""".strip()
        normalized = normalize_review_comment(
            content=content,
            changed_files=["src/components/Hero.astro"],
        )
        self.assertEqual(normalized["event"], "REQUEST_CHANGES")
        self.assertEqual(normalized["confidence"], "81%")
        self.assertEqual(len(normalized["findings"]), 1)
        self.assertIn("src/components/Hero.astro:87", normalized["body"])
        self.assertNotIn("tooling/orchestrator/cli.py:42", normalized["body"])

    def test_does_not_apply_default_top_five_limit(self) -> None:
        lines = [
            "1. Finding in src/a.py:1.",
            "2. Finding in src/b.py:2.",
            "3. Finding in src/c.py:3.",
            "4. Finding in src/d.py:4.",
            "5. Finding in src/e.py:5.",
            "6. Finding in src/f.py:6.",
            "## FINAL_VERDICT: ✅ APPROVED (90%)",
        ]
        normalized = normalize_review_comment(
            content="\n".join(lines),
            changed_files=[
                "src/a.py",
                "src/b.py",
                "src/c.py",
                "src/d.py",
                "src/e.py",
                "src/f.py",
            ],
        )
        self.assertEqual(len(normalized["findings"]), 6)
        self.assertIn("6. Finding in src/f.py:6.", normalized["body"])

    def test_respects_optional_max_findings_override(self) -> None:
        content = """
1. Finding in src/a.py:1.
2. Finding in src/b.py:2.
3. Finding in src/c.py:3.
## FINAL_VERDICT: ✅ APPROVED (90%)
""".strip()
        normalized = normalize_review_comment(
            content=content,
            changed_files=["src/a.py", "src/b.py", "src/c.py"],
            max_findings=2,
        )
        self.assertEqual(len(normalized["findings"]), 2)
        self.assertNotIn("3. Finding in src/c.py:3.", normalized["body"])

    def test_comment_fallback_when_verdict_missing(self) -> None:
        content = "General commentary without final verdict."
        normalized = normalize_review_comment(
            content=content,
            changed_files=["src/components/Hero.astro"],
        )
        self.assertEqual(normalized["event"], "COMMENT")
        self.assertEqual(normalized["confidence"], "unknown")
        self.assertIn("Parser note", normalized["body"])


if __name__ == "__main__":
    unittest.main()
