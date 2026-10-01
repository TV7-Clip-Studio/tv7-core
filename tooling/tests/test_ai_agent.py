from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import ai_agent
from cockpit_common import action_command, focus_display, normalize_action


class AiAgentTest(unittest.TestCase):
    def test_structured_focus_uses_slice(self) -> None:
        self.assertEqual(focus_display({"slice": "Core cockpit tooling"}), "Core cockpit tooling")

    def test_structured_focus_never_stringifies_object(self) -> None:
        self.assertEqual(focus_display({"unknown": "value"}), "General / Clean Slice")

    def test_unknown_repo_is_rejected(self) -> None:
        with patch("ai_agent.configured_repos", return_value={"tv7-core"}):
            with self.assertRaisesRegex(ValueError, "unknown repository"):
                ai_agent.repo_path("../../tmp")

    @patch("cockpit_common.allowed_repos", return_value={"tv7-core"})
    def test_cockpit_action_rejects_command_injection(self, _allowed) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid roadmap"):
            action_command("tv7-core", "start", "start CO-A01; rm -rf /tmp/example")

    def test_sync_action_state_maps_to_operation(self) -> None:
        self.assertEqual(normalize_action("dirty-needs-ready"), "ready")
        self.assertEqual(normalize_action("dirty-pr-needs-ready"), "ready")
        self.assertEqual(normalize_action("clean-needs-agent-work"), "start")
        self.assertEqual(normalize_action("validated-needs-commit"), "commit")

    def test_deepseek_review_uses_profile_and_read_only_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as temp, patch("ai_agent.deepseek_ready"):
            command, output = ai_agent.codex_command("deepseek", Path(temp), "review", write=False)
            try:
                self.assertIn("deepseek", command)
                self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
                self.assertIn('plugins."github@openai-curated".enabled=false', command)
            finally:
                output.unlink(missing_ok=True)

    def test_codex_resolution_uses_workspace_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            command, output = ai_agent.codex_command("codex", Path(temp), "resolve", write=True)
            try:
                self.assertIn("workspace-write", command)
                self.assertNotIn("--profile", command)
            finally:
                output.unlink(missing_ok=True)

    def test_deepseek_resolution_uses_workspace_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            command, output = ai_agent.codex_command("deepseek", Path(temp), "resolve", write=True)
            try:
                self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
                self.assertEqual(command[command.index("--profile") + 1], "deepseek")
            finally:
                output.unlink(missing_ok=True)

    def test_load_runs_reads_immutable_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.json").write_text(json.dumps({"runs": [{"id": "run-1"}]}), encoding="utf-8")
            self.assertEqual(ai_agent.load_runs(root), [{"id": "run-1"}])

    def test_roadmap_prompt_uses_planning_not_code_review_language(self) -> None:
        prompt = ai_agent.review_prompt(
            "tv7-engine", "main", '{"roadmap_focus":"EN-A01-02-01"}', [], "roadmap"
        )
        self.assertIn("technical planner", prompt)
        self.assertIn("ACTIVE ROADMAP SLICE", prompt)
        self.assertIn("Do not edit files", prompt)

    def test_roadmap_resolution_becomes_implementation(self) -> None:
        prompt = ai_agent.resolve_prompt(
            "tv7-engine", {"id": "plan-1", "provider": "gemini", "scope": "roadmap", "issues": ["Implement probe"]}
        )
        self.assertIn("Implement the selected roadmap plan", prompt)
        self.assertIn("Do not commit or push", prompt)


if __name__ == "__main__":
    unittest.main()
