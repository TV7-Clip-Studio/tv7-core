from __future__ import annotations

import unittest

from handoff import format_resolved_focus


class HandoffFormattingTest(unittest.TestCase):
    def test_structured_focus_is_rendered_as_operator_text(self) -> None:
        rendered = format_resolved_focus(
            {
                "slice": "Engine transcript generation contract",
                "next_roadmap": {"id": "EN-A01-02-01", "title": "Implement probing"},
                "pending_changes": "No pending changes (repository is clean).",
                "next_action": "Start EN-A01-02-01.",
            }
        )

        self.assertIn("Slice: Engine transcript generation contract", rendered)
        self.assertIn("Roadmap: EN-A01-02-01: Implement probing", rendered)
        self.assertNotIn("{'slice'", rendered)


if __name__ == "__main__":
    unittest.main()
