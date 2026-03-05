from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import deepseek_followup
from orchestrator import cli


class FollowupLimitParseTests(unittest.TestCase):
    def test_parse_limit_valid(self) -> None:
        self.assertEqual(deepseek_followup._parse_limit("25", default=20), 25)

    def test_parse_limit_invalid_warns_and_defaults(self) -> None:
        err = StringIO()
        with redirect_stderr(err):
            value = deepseek_followup._parse_limit("abc", default=20)
        self.assertEqual(value, 20)
        self.assertIn("invalid LIMIT", err.getvalue())

    def test_parse_limit_zero_warns_and_defaults(self) -> None:
        err = StringIO()
        with redirect_stderr(err):
            value = deepseek_followup._parse_limit("0", default=20)
        self.assertEqual(value, 20)
        self.assertIn("defaulting to 20", err.getvalue())


class BatchIdDefaultTests(unittest.TestCase):
    def test_default_batch_id_from_codex_branch(self) -> None:
        fake = SimpleNamespace(returncode=0, stdout="codex/batch-tv7-core-20260305-001\n")
        with patch("orchestrator.cli.subprocess.run", return_value=fake):
            self.assertEqual(cli._default_batch_id(Path("/tmp")), "20260305-001")

    def test_default_batch_id_generated_on_failure(self) -> None:
        fake = SimpleNamespace(returncode=1, stdout="")
        with (
            patch("orchestrator.cli.subprocess.run", return_value=fake),
            patch("orchestrator.cli.now_iso", return_value="2026-03-05T10:11:12+00:00"),
        ):
            self.assertEqual(cli._default_batch_id(Path("/tmp")), "manual-20260305T101112z")

    def test_default_batch_id_generated_for_non_codex_branch(self) -> None:
        fake = SimpleNamespace(returncode=0, stdout="main\n")
        with (
            patch("orchestrator.cli.subprocess.run", return_value=fake),
            patch("orchestrator.cli.now_iso", return_value="2026-03-05T10:11:12+00:00"),
        ):
            self.assertEqual(cli._default_batch_id(Path("/tmp")), "manual-20260305T101112z")


if __name__ == "__main__":
    unittest.main()
