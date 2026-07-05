from __future__ import annotations

import unittest
from pathlib import Path
from sync import RepoState, RoadmapItem, action_profile, is_repo_unchanged, sanitize_resolved_focus


class SyncCachingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.state = RepoState(
            repo="tv7-test",
            path=Path("/tmp/tv7-test"),
            exists=True,
            branch="main",
            status_ok=True,
            note="clean",
            changes=0,
            ahead=0,
            roadmap_items=[
                RoadmapItem(done=True, item_id="TE-A01-01", title="Done item", section="Needs to be done", path="roadmap.md"),
                RoadmapItem(done=False, item_id="TE-A01-02", title="Pending item", section="Needs to be done", path="roadmap.md"),
            ],
            pr=None,
            head_sha="current-head",
            dirty_status_hash="clean-hash",
        )
        self.prev_item = {
            "repo": "tv7-test",
            "branch": "main",
            "git_note": "clean",
            "status_ok": True,
            "head_sha": "current-head",
            "dirty_status_hash": "clean-hash",
            "resolved_focus": "Working on TE-A01-02",
            "pr": None,
            "completed_count": 1,
            "open_required_count": 1,
            "open_other_count": 0,
            "test_plan": {"where": "terminal"},
        }

    def test_unchanged_repo_returns_true(self) -> None:
        self.assertTrue(is_repo_unchanged(self.state, self.prev_item))

    def test_missing_prev_item_returns_false(self) -> None:
        self.assertFalse(is_repo_unchanged(self.state, None))

    def test_missing_resolved_focus_returns_false(self) -> None:
        self.prev_item["resolved_focus"] = ""
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_local_changes_returns_false(self) -> None:
        self.state.changes = 1
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_ahead_commits_returns_false(self) -> None:
        self.state.ahead = 1
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_feature_branch_returns_false(self) -> None:
        self.state.branch = "feature-branch"
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_branch_mismatch_returns_false(self) -> None:
        self.prev_item["branch"] = "dev"
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_prev_run_dirty_returns_false(self) -> None:
        self.prev_item["git_note"] = "1 pending"
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_changed_head_invalidates_cache(self) -> None:
        self.prev_item["head_sha"] = "previous-head"
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_changed_dirty_hash_invalidates_cache(self) -> None:
        self.prev_item["dirty_status_hash"] = "previous-hash"
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_failed_previous_sync_invalidates_cache(self) -> None:
        self.prev_item["status_ok"] = False
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_clean_repo_discards_cached_conflict_claims(self) -> None:
        focus = sanitize_resolved_focus(
            self.state,
            {
                "slice": "Current slice",
                "pending_changes": "2 files with rebase conflicts: UU src/main.rs",
                "signals": "Active conflicts remain.",
                "next_action": "Resolve rebase conflicts.",
            },
        )
        self.assertEqual(focus["pending_changes"], "No pending changes (repository is clean).")
        self.assertNotIn("conflict", focus["signals"].lower())
        self.assertNotIn("conflict", focus["next_action"].lower())

    def test_pr_presence_mismatch_returns_false(self) -> None:
        self.state.pr = {"number": 123, "state": "OPEN"}
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_pr_details_mismatch_returns_false(self) -> None:
        self.state.pr = {"number": 123, "state": "OPEN"}
        self.prev_item["pr"] = {"number": 124, "state": "OPEN"}
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_roadmap_progress_mismatch_returns_false(self) -> None:
        # Change completion metrics
        self.state.roadmap_items[1].done = True
        self.assertFalse(is_repo_unchanged(self.state, self.prev_item))

    def test_action_profile_prioritizes_requested_changes_pr(self) -> None:
        self.state.pr = {"number": 42, "state": "OPEN", "reviewDecision": "CHANGES_REQUESTED"}
        action = action_profile(self.state)
        self.assertEqual(action["state"], "pr-changes-requested")
        self.assertIn("REVIEW_AUTO_ROUND=1", action["command"])

    def test_action_profile_dirty_repo_needs_ready(self) -> None:
        self.state.changes = 2
        action = action_profile(self.state)
        self.assertEqual(action["state"], "dirty-needs-ready")
        self.assertEqual(action["command"], "make ready REPO=tv7-test")

    def test_action_profile_dirty_open_pr_requires_followup_ready(self) -> None:
        self.state.pr = {"number": 52, "state": "OPEN", "reviewDecision": "APPROVED"}
        self.state.changes = 3
        action = action_profile(self.state)
        self.assertEqual(action["state"], "dirty-pr-needs-ready")

    def test_action_profile_ahead_open_pr_requires_updated_review(self) -> None:
        self.state.pr = {"number": 52, "state": "OPEN", "reviewDecision": "APPROVED"}
        self.state.ahead = 1
        action = action_profile(self.state)
        self.assertEqual(action["state"], "pr-updates-need-review")

    def test_action_profile_validated_repo_needs_commit(self) -> None:
        self.state.changes = 2
        self.state.queue_status = "passed"
        action = action_profile(self.state)
        self.assertEqual(action["state"], "validated-needs-commit")


if __name__ == "__main__":
    unittest.main()
