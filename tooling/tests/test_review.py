from __future__ import annotations

import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from review import (
    REVIEW_DECISION_ANOTHER_ROUND,
    RepoConfig,
    ask_after_review_round,
    confidence_value,
    review_is_approved,
    review_matches_head,
    roadmap_branch_name,
    unique_branch_name,
)


class ReviewBranchNameTest(unittest.TestCase):
    def test_roadmap_branch_uses_item_and_slice(self) -> None:
        self.assertEqual(
            roadmap_branch_name("EN-A03-01-03", "Engine transcript generation contract"),
            "en-a03-01-03-engine-transcript-generation-contract",
        )

    def test_roadmap_branch_normalizes_symbols(self) -> None:
        self.assertEqual(
            roadmap_branch_name("ST-A01-03-01", "Quick Clip / diagnostics"),
            "st-a01-03-01-quick-clip-diagnostics",
        )

    @patch("review.branch_exists")
    def test_unique_branch_adds_numeric_suffix(self, exists) -> None:
        exists.side_effect = lambda _repo, branch: branch in {"en-a01-task", "en-a01-task-2"}
        self.assertEqual(unique_branch_name(object(), "en-a01-task"), "en-a01-task-3")

    def test_review_rejects_previous_head(self) -> None:
        entry = {"commit_id": "old", "submitted_at": "2026-06-19T16:00:01Z"}
        head_time = datetime(2026, 6, 19, 16, 0, tzinfo=timezone.utc)
        self.assertFalse(review_matches_head(entry, "new", head_time))

    def test_comment_must_be_newer_than_head(self) -> None:
        entry = {"created_at": "2026-06-19T15:59:59Z"}
        head_time = datetime(2026, 6, 19, 16, 0, tzinfo=timezone.utc)
        self.assertFalse(review_matches_head(entry, "new", head_time))

    def test_confidence_value_parses_percent(self) -> None:
        self.assertEqual(confidence_value("95%"), 95)

    def test_confidence_value_rejects_invalid(self) -> None:
        self.assertIsNone(confidence_value("unknown"))
        self.assertIsNone(confidence_value("120%"))

    def test_review_is_approved_requires_threshold(self) -> None:
        self.assertTrue(review_is_approved({"verdict": "APPROVED", "confidence": "95%"}, 90))
        self.assertFalse(review_is_approved({"verdict": "APPROVED", "confidence": "80%"}, 90))
        self.assertFalse(review_is_approved({"verdict": "REJECTED", "confidence": "95%"}, 90))

    def test_review_is_approved_accepts_threshold_boundary(self) -> None:
        self.assertTrue(review_is_approved({"verdict": "APPROVED", "confidence": "90%"}, 90))

    @patch("review.print_full_review")
    @patch("builtins.input", return_value="2")
    def test_approved_review_another_round_stays_in_flow(self, _input, _print_review) -> None:
        with redirect_stdout(StringIO()):
            decision = ask_after_review_round(
                "TV7-Clip-Studio",
                Path("/tmp/tv7-studio"),
                RepoConfig(
                    repo="tv7-studio",
                    base="main",
                    check_command="",
                    docs_only_allowed=False,
                ),
                "tv7-studio",
                26,
                "feature",
                {"verdict": "APPROVED", "confidence": "95%"},
                90,
            )
        self.assertEqual(decision, REVIEW_DECISION_ANOTHER_ROUND)


if __name__ == "__main__":
    unittest.main()
