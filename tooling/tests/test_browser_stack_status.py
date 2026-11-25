import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "dev-browser-stack.py"
spec = importlib.util.spec_from_file_location("browser_stack", path)
stack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stack)


class BrowserStackStatusTests(unittest.TestCase):
    def test_health_exit_codes_and_all_services_checked(self):
        for responses, expected in [([True, True, True], 0), ([False, True, True], 1)]:
            with self.subTest(responses=responses), patch.object(
                stack, "healthy", side_effect=responses
            ) as healthy, patch("builtins.print"):
                self.assertEqual(stack.status(), expected)
                self.assertEqual([call.args[0] for call in healthy.call_args_list], list(stack.HEALTH))
