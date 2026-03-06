"""Tests for window discovery JSON parsing logic."""

import json
import subprocess
import unittest
from unittest.mock import patch

from window import find_chrome_windows


class TestFindChromeWindows(unittest.TestCase):
    """Tests for find_chrome_windows using mocked subprocess calls."""

    def _mock_swift_result(self, windows_json, returncode=0, stderr=""):
        """Create a mock subprocess.CompletedProcess with the given JSON output."""
        return subprocess.CompletedProcess(
            args=["swift", "-"],
            returncode=returncode,
            stdout=json.dumps(windows_json)
            if isinstance(windows_json, list)
            else windows_json,
            stderr=stderr,
        )

    @patch("window.subprocess.run")
    def test_multiple_windows(self, mock_run):
        """Parsing valid JSON with multiple windows returns correct dicts."""
        mock_run.return_value = self._mock_swift_result(
            [
                {
                    "window_id": 11121,
                    "name": "My App - Dashboard",
                    "width": 1680,
                    "height": 1890,
                },
                {
                    "window_id": 10460,
                    "name": "Google - Search",
                    "width": 1440,
                    "height": 900,
                },
            ]
        )

        windows = find_chrome_windows()

        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["window_id"], 11121)
        self.assertEqual(windows[0]["name"], "My App - Dashboard")
        self.assertEqual(windows[0]["width"], 1680)
        self.assertEqual(windows[0]["height"], 1890)
        self.assertEqual(windows[1]["window_id"], 10460)
        self.assertEqual(windows[1]["name"], "Google - Search")
        self.assertEqual(windows[1]["width"], 1440)
        self.assertEqual(windows[1]["height"], 900)

    @patch("window.subprocess.run")
    def test_null_window_name(self, mock_run):
        """Windows with null names (no Screen Recording permission) are parsed correctly."""
        mock_run.return_value = self._mock_swift_result(
            [
                {"window_id": 5000, "name": None, "width": 800, "height": 600},
            ]
        )

        windows = find_chrome_windows()

        self.assertEqual(len(windows), 1)
        self.assertIsNone(windows[0]["name"])
        self.assertEqual(windows[0]["window_id"], 5000)
        self.assertEqual(windows[0]["width"], 800)
        self.assertEqual(windows[0]["height"], 600)

    @patch("window.subprocess.run")
    def test_empty_array(self, mock_run):
        """Empty JSON array returns empty list (no Chrome windows found)."""
        mock_run.return_value = self._mock_swift_result([])

        windows = find_chrome_windows()

        self.assertEqual(windows, [])

    @patch("window.subprocess.run")
    def test_swift_failure_raises_runtime_error(self, mock_run):
        """Non-zero exit code from Swift script raises RuntimeError."""
        mock_run.return_value = self._mock_swift_result(
            "",
            returncode=1,
            stderr="error: something went wrong",
        )

        with self.assertRaises(RuntimeError) as ctx:
            find_chrome_windows()

        self.assertIn("exit code 1", str(ctx.exception))
        self.assertIn("something went wrong", str(ctx.exception))

    @patch("window.subprocess.run")
    def test_window_values_are_correct_types(self, mock_run):
        """Window ID, width, and height are always returned as ints."""
        mock_run.return_value = self._mock_swift_result(
            [
                {"window_id": 42, "name": "Test", "width": 1920, "height": 1080},
            ]
        )

        windows = find_chrome_windows()
        w = windows[0]

        self.assertIsInstance(w["window_id"], int)
        self.assertIsInstance(w["width"], int)
        self.assertIsInstance(w["height"], int)
        self.assertIsInstance(w["name"], str)


if __name__ == "__main__":
    unittest.main()
