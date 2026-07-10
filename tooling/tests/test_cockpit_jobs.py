from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cockpit_jobs import JobStore


class CockpitJobsTest(unittest.TestCase):
    def test_job_persists_plain_output_and_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JobStore(Path(temp))
            job = store.create(
                repo="tv7-core",
                kind="test",
                command=["printf", "ready output\\n"],
                cwd=Path(temp),
            )
            deadline = time.time() + 3
            while time.time() < deadline:
                current = store.get(job["id"])
                if current and current["status"] in {"succeeded", "failed"}:
                    break
                time.sleep(0.02)
            self.assertEqual(store.get(job["id"])["status"], "succeeded")
            output, _ = store.log(job["id"])
            self.assertIn("ready output", output)
            self.assertNotIn("1b", output)

    def test_log_removes_terminal_color_sequences(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JobStore(Path(temp))
            (Path(temp) / "job.log").write_text("\x1b[0;32mready\x1b[0m\n", encoding="utf-8")
            output, _ = store.log("job")
            self.assertEqual(output, "ready\n")

    @patch("cockpit_jobs.subprocess.Popen")
    def test_background_process_has_piped_interactive_stdin(self, popen) -> None:
        popen.return_value.poll.return_value = 0
        popen.return_value.returncode = 0
        popen.return_value.pid = 12345
        popen.return_value.stdin = __import__("unittest").mock.MagicMock()
        with tempfile.TemporaryDirectory() as temp:
            store = JobStore(Path(temp))
            job = store.create(repo="tv7-core", kind="review", command=["make", "review"], cwd=Path(temp))
            deadline = time.time() + 2
            while time.time() < deadline and store.get(job["id"])["status"] not in {"succeeded", "failed"}:
                time.sleep(0.02)
            self.assertEqual(popen.call_args.kwargs["stdin"], __import__("subprocess").PIPE)
            self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_timed_out_job_is_failed_with_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JobStore(Path(temp))
            job = store.create(
                repo="tv7-core", kind="slow", command=["sleep", "5"], cwd=Path(temp), timeout=1,
            )
            deadline = time.time() + 3
            while time.time() < deadline and store.get(job["id"])["status"] not in {"failed", "succeeded"}:
                time.sleep(0.05)
            current = store.get(job["id"])
            self.assertEqual(current["status"], "failed")
            self.assertEqual(current["phase"], "timed_out")

    def test_startup_marks_abandoned_job_interrupted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "old.json").write_text(
                '{"id":"old","status":"running","phase":"running"}\n', encoding="utf-8"
            )
            store = JobStore(root)
            self.assertEqual(store.get("old")["status"], "interrupted")


if __name__ == "__main__":
    unittest.main()
