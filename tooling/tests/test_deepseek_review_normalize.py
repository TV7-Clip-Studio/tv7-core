from __future__ import annotations

import unittest

from deepseek_review_normalize import normalize_review


class DeepSeekReviewNormalizeTest(unittest.TestCase):
    def test_approved_below_90_is_merge_with_warning(self) -> None:
        review = normalize_review(
            """### Valid Findings
No valid current-head findings.

## FINAL_VERDICT: ✅ APPROVED (85%)
""",
            "abc123",
        )
        self.assertEqual(review["merge_recommendation"], "MERGE_WITH_WARNING")
        self.assertEqual(review["event"], "APPROVE")
        self.assertIn("<!-- REVIEWED_SHA: abc123 -->", review["body"])

    def test_explicit_merge_recommendation_wins(self) -> None:
        review = normalize_review(
            "## FINAL_VERDICT: ✅ APPROVED (85%)\nMERGE_RECOMMENDATION: MERGE",
            "abc123",
        )
        self.assertEqual(review["merge_recommendation"], "MERGE")

    def test_self_disproving_finding_is_removed(self) -> None:
        review = normalize_review(
            """### Valid Findings

F-01: hashlib is not imported.
Impact: None - import hashlib is present at line 8. This is a false alarm.

### Risks
None.

## FINAL_VERDICT: ✅ APPROVED (85%)
""",
            "abc123",
        )
        self.assertNotIn("hashlib is not imported", review["body"])
        self.assertEqual(review["removed_self_disproving_findings"], 1)
