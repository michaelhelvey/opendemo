"""Tests for --json output mode across all commands."""

import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from project import init_project, save_project, data_dir
from status import _handle_status
from window import _handle_find_window
from project import _handle_init
from recording import _handle_record, _handle_stop
from render import _handle_render


def _capture_stdout(func, *args, **kwargs):
    """Call func and return whatever it printed to stdout."""
    with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
        # Patch print in each module to write to our StringIO
        func(*args, **kwargs)
        return mock_stdout.getvalue()


class TestFindWindowJsonOutput(unittest.TestCase):
    """Tests for find-window --json output."""

    @patch("window.find_chrome_windows")
    def test_json_output_with_windows(self, mock_find):
        """find-window --json produces valid JSON with windows."""
        mock_find.return_value = [
            {"window_id": 11121, "name": "My App", "width": 1680, "height": 1890},
            {"window_id": 10460, "name": "Google", "width": 1440, "height": 900},
        ]

        args = Namespace(json_output=True)

        with patch("builtins.print") as mock_print:
            _handle_find_window(args)
            output = mock_print.call_args[0][0]

        parsed = json.loads(output)
        self.assertIn("windows", parsed)
        self.assertEqual(len(parsed["windows"]), 2)
        self.assertEqual(parsed["windows"][0]["window_id"], 11121)
        self.assertEqual(parsed["windows"][1]["name"], "Google")

    @patch("window.find_chrome_windows")
    def test_json_output_empty_windows(self, mock_find):
        """find-window --json produces valid JSON even with no windows."""
        mock_find.return_value = []

        args = Namespace(json_output=True)

        with patch("builtins.print") as mock_print:
            _handle_find_window(args)
            output = mock_print.call_args[0][0]

        parsed = json.loads(output)
        self.assertEqual(parsed["windows"], [])


class TestInitJsonOutput(unittest.TestCase):
    """Tests for init --json output."""

    def test_json_output(self):
        """init --json produces valid JSON with project_path and window_id."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = str(Path(tmp) / "my-demo")
            args = Namespace(
                json_output=True, path=project_path, window_id=11121, speed=None
            )

            with patch("builtins.print") as mock_print:
                _handle_init(args)
                output = mock_print.call_args[0][0]

            parsed = json.loads(output)
            self.assertEqual(parsed["project_path"], project_path)
            self.assertEqual(parsed["window_id"], 11121)


class TestRecordJsonOutput(unittest.TestCase):
    """Tests for record --json output."""

    @patch("recording.subprocess.Popen")
    def test_json_output(self, mock_popen):
        """record --json produces valid JSON with pid and clip_file."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            args = Namespace(json_output=True, path=str(project_path))

            with patch("builtins.print") as mock_print:
                _handle_record(args)
                output = mock_print.call_args[0][0]

            parsed = json.loads(output)
            self.assertEqual(parsed["pid"], 12345)
            self.assertEqual(parsed["clip_file"], "clip_001.mov")


class TestStopJsonOutput(unittest.TestCase):
    """Tests for stop --json output."""

    @patch("recording.time.sleep")
    @patch("recording.os.kill")
    def test_json_output(self, mock_kill, mock_sleep):
        """stop --json produces valid JSON with clip_file and subtitle."""

        def kill_side_effect(pid, sig):
            if sig == 0:
                raise OSError("No such process")

        mock_kill.side_effect = kill_side_effect

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            # Create fake recording state
            state = {"pid": 12345, "clip_file": "clip_001.mov"}
            (data_dir(project_path) / ".recording.json").write_text(json.dumps(state))
            (data_dir(project_path) / "clip_001.mov").touch()

            args = Namespace(
                json_output=True,
                path=str(project_path),
                subtitle="Here we configure settings.",
            )

            with patch("builtins.print") as mock_print:
                _handle_stop(args)
                output = mock_print.call_args[0][0]

            parsed = json.loads(output)
            self.assertEqual(parsed["clip_file"], "clip_001.mov")
            self.assertEqual(parsed["subtitle"], "Here we configure settings.")


class TestRenderJsonOutput(unittest.TestCase):
    """Tests for render --json output."""

    @patch("render.subprocess.run")
    def test_json_output(self, mock_run):
        """render --json produces valid JSON with output and size_bytes."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=11121)

            data["clips"] = [
                {"file": "clip_001.mov", "subtitle": "First clip."},
            ]
            save_project(project_path, data)
            (data_dir(project_path) / "clip_001.mov").touch()

            # Mock ffmpeg to create the output file on concat
            def side_effect(cmd, **kwargs):
                if "-f" in cmd and "concat" in cmd:
                    output_file = Path(cmd[-1])
                    output_file.write_bytes(b"fake video data " * 100)

            mock_run.side_effect = side_effect

            args = Namespace(json_output=True, path=str(project_path))

            with patch("builtins.print") as mock_print:
                _handle_render(args)
                output = mock_print.call_args[0][0]

            parsed = json.loads(output)
            self.assertEqual(parsed["output"], ".data/demo.mp4")
            self.assertIsInstance(parsed["size_bytes"], int)
            self.assertGreater(parsed["size_bytes"], 0)


class TestStatusJsonOutput(unittest.TestCase):
    """Tests for status --json output."""

    def test_json_output_fresh_project(self):
        """status --json produces valid JSON for a fresh project."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            args = Namespace(json_output=True, path=str(project_path))

            with patch("builtins.print") as mock_print:
                _handle_status(args)
                output = mock_print.call_args[0][0]

            parsed = json.loads(output)
            self.assertEqual(parsed["window_id"], 11121)
            self.assertEqual(parsed["clip_count"], 0)
            self.assertFalse(parsed["recording_in_progress"])

    def test_json_output_with_clips_and_recording(self):
        """status --json includes clips and recording state."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=42)

            data["clips"] = [
                {"file": "clip_001.mov", "subtitle": "First."},
            ]
            save_project(project_path, data)

            state = {"pid": 99999, "clip_file": "clip_002.mov"}
            (data_dir(project_path) / ".recording.json").write_text(json.dumps(state))

            args = Namespace(json_output=True, path=str(project_path))

            with patch("builtins.print") as mock_print:
                _handle_status(args)
                output = mock_print.call_args[0][0]

            parsed = json.loads(output)
            self.assertEqual(parsed["clip_count"], 1)
            self.assertTrue(parsed["recording_in_progress"])
            self.assertEqual(parsed["current_clip"], "clip_002.mov")


if __name__ == "__main__":
    unittest.main()
