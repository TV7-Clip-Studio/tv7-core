from __future__ import annotations

import unittest

from cockpit_assessments import parse_github_deepseek
from cockpit_common import workflow_from_state


class CockpitAssessmentsTest(unittest.TestCase):
    def test_github_deepseek_review_is_normalized(self) -> None:
        review = {
            "id": "review-1",
            "submittedAt": "2026-07-05T02:00:00Z",
            "commit": {"oid": "abc123"},
            "body": """### DeepSeek review
- Confidence: 95%
- Final verdict: APPROVED

### Summary
The current PR is ready.

### Valid Findings
No critical issues found.

## FINAL_VERDICT: APPROVED (95%)
MERGE_RECOMMENDATION: MERGE
""",
        }
        parsed = parse_github_deepseek("tv7-core", "feature", {"number": 52}, review)
        self.assertEqual(parsed["scope"], "pull_request")
        self.assertEqual(parsed["head_sha"], "abc123")
        self.assertEqual(parsed["confidence"], 95)
        self.assertEqual(parsed["verdict"], "APPROVED")
        self.assertEqual(parsed["issues"], [])

    def test_non_deepseek_review_is_ignored(self) -> None:
        self.assertIsNone(parse_github_deepseek("tv7-core", "feature", {"number": 52}, {"body": "LGTM"}))

    def test_fresh_pr_review_enters_decision_mode(self) -> None:
        latest_review = {
            "id": "github-pr-52-review-1",
            "head_sha": "abc123",
            "verdict": "APPROVED",
            "confidence": 95,
        }
        state = workflow_from_state({
            "repo": "tv7-core",
            "head_sha": "abc123",
            "dirty_file_count": 0,
            "ahead": 0,
            "pr": {"number": 52},
            "action": {"state": "pr-ready"},
        }, latest_review)
        self.assertEqual(state["mode"], "pr-review-decision")
        self.assertEqual(state["allowed_actions"], ["fix-pr-review", "merge-pr", "defer"])

    def test_dirty_pr_without_validation_enters_validation_mode(self) -> None:
        latest_review = {
            "id": "github-pr-52-review-1",
            "head_sha": "abc123",
            "verdict": "APPROVED",
            "confidence": 95,
        }
        state = workflow_from_state({
            "repo": "tv7-core",
            "head_sha": "def456",
            "dirty_file_count": 2,
            "ahead": 0,
            "pr": {"number": 52},
            "action": {"state": "dirty-pr-needs-ready"},
        }, latest_review)
        self.assertEqual(state["mode"], "dirty-validation")
        self.assertEqual(state["allowed_actions"], ["ready"])

    def test_ready_dirty_pr_waits_for_human_validation_before_review(self) -> None:
        latest_review = {
            "id": "github-pr-52-review-1",
            "head_sha": "abc123",
            "verdict": "APPROVED",
            "confidence": 95,
        }
        state = workflow_from_state({
            "repo": "tv7-core",
            "head_sha": "abc123",
            "dirty_file_count": 2,
            "ahead": 0,
            "pr": {"number": 52},
            "queue_status": "ready",
            "action": {"state": "awaiting-human-validation"},
        }, latest_review)
        self.assertEqual(state["mode"], "human-validation")
        self.assertEqual(state["allowed_actions"], ["record-validation"])

    def test_passed_dirty_pr_enters_commit_mode_before_review(self) -> None:
        latest_review = {
            "id": "github-pr-52-review-1",
            "head_sha": "abc123",
            "verdict": "APPROVED",
            "confidence": 95,
        }
        state = workflow_from_state({
            "repo": "tv7-core",
            "head_sha": "abc123",
            "dirty_file_count": 2,
            "ahead": 0,
            "pr": {"number": 52},
            "queue_status": "passed",
            "action": {"state": "validated-needs-commit"},
        }, latest_review)
        self.assertEqual(state["mode"], "validated-commit")
        self.assertEqual(state["allowed_actions"], ["commit"])


if __name__ == "__main__":
    unittest.main()
