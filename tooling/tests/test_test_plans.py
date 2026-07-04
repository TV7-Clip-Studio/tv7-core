from __future__ import annotations

import sys
from pathlib import Path
import unittest


TOOLING_DIR = Path(__file__).resolve().parents[1]
if str(TOOLING_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLING_DIR))

from test_plans import build_test_plan  # noqa: E402


class TestHumanValidationPlans(unittest.TestCase):
    def assert_valid_plan(self, plan: dict[str, object]) -> None:
        self.assertTrue(str(plan.get("title", "")))
        self.assertTrue(str(plan.get("where", "")))
        for key in ("roadmap_items", "preconditions", "steps", "expected", "known_limitations"):
            self.assertIsInstance(plan.get(key), list)

    def test_engine_transcript_plan_maps_slice_roadmap(self) -> None:
        plan = build_test_plan("tv7-engine", "Engine transcript generation contract")

        self.assert_valid_plan(plan)
        self.assertEqual(
            plan["roadmap_items"],
            ["EN-A03-01-03", "EN-A05-01-01", "EN-A06-01-04"],
        )
        self.assertIn("TRANSCRIPTION_SETUP_REQUIRED", " ".join(plan["expected"]))

    def test_studio_plan_includes_quick_clip_path(self) -> None:
        plan = build_test_plan("tv7-studio", "Studio Quick Clip and diagnostics integration")

        self.assert_valid_plan(plan)
        self.assertIn("Quick Clip", plan["where"])
        self.assertIn("ST-A01-03-01", plan["roadmap_items"])

    def test_unknown_repo_has_usable_fallback(self) -> None:
        plan = build_test_plan("tv7-unknown", "Unknown slice", {"id": "XX-A01"})

        self.assert_valid_plan(plan)
        self.assertEqual(plan["roadmap_items"], ["XX-A01"])


if __name__ == "__main__":
    unittest.main()
