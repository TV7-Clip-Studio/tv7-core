from __future__ import annotations

import unittest

from deepseek_review_comment import normalize_review_comment


class DeepseekReviewCommentTests(unittest.TestCase):
    def test_wraps_narrative_with_minimal_metadata(self) -> None:
        content = """
Overall summary: solid change with one medium risk.
- Possible stage transition mismatch in tooling/orchestrator/lifecycle.py:83.
## FINAL_VERDICT: ❌ REJECTED (81%)
""".strip()
        normalized = normalize_review_comment(
            content=content,
            changed_files=["tooling/orchestrator/lifecycle.py"],
        )
        self.assertEqual(normalized["event"], "REQUEST_CHANGES")
        self.assertEqual(normalized["confidence"], "81%")
        self.assertEqual(normalized["verdict"], "REJECTED")
        self.assertIn("### Model narrative", normalized["body"])
        self.assertIn("Overall summary: solid change with one medium risk.", normalized["body"])
        self.assertIn("tooling/orchestrator/lifecycle.py:83", normalized["body"])

    def test_comment_fallback_when_verdict_missing(self) -> None:
        content = "General commentary without final verdict."
        normalized = normalize_review_comment(
            content=content,
            changed_files=["src/components/Hero.astro"],
        )
        self.assertEqual(normalized["event"], "COMMENT")
        self.assertEqual(normalized["confidence"], "unknown")
        self.assertEqual(normalized["verdict"], "COMMENT")
        self.assertIn("General commentary without final verdict.", normalized["body"])
        self.assertIn("Parser note", normalized["body"])

    def test_drops_duplicate_deepseek_heading_from_model_text(self) -> None:
        content = """
DeepSeek review
Summary first.
## FINAL_VERDICT: ✅ APPROVED (95%)
""".strip()
        normalized = normalize_review_comment(
            content=content,
            changed_files=[],
        )
        self.assertEqual(normalized["event"], "APPROVE")
        self.assertIn("Summary first.", normalized["body"])
        self.assertNotIn("DeepSeek review\nDeepSeek review", normalized["body"])


if __name__ == "__main__":
    unittest.main()
