"""Tests for recording lifecycle — start and stop screen capture."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from project import init_project, load_project
from project import data_dir
from recording import start_recording, stop_recording


class TestStartRecording(unittest.TestCase):
    """Tests for start_recording."""

    @patch("recording.subprocess.Popen")
    def test_starts_recording_and_creates_state_file(self, mock_popen):
        """start_recording starts screencapture and writes .recording.json."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            pid, clip_file = start_recording(project_path)

            self.assertEqual(pid, 12345)
            self.assertEqual(clip_file, "clip_001.mov")

            # Verify .recording.json was created with correct content
            state_path = data_dir(project_path) / ".recording.json"
            self.assertTrue(state_path.exists())
            state = json.loads(state_path.read_text())
            self.assertEqual(state["pid"], 12345)
            self.assertEqual(state["clip_file"], "clip_001.mov")

            # Verify screencapture was called with correct arguments
            mock_popen.assert_called_once_with(
                [
                    "screencapture",
                    "-v",
                    "-x",
                    "-l",
                    "11121",
                    str(data_dir(project_path) / "clip_001.mov"),
                ]
            )

    @patch("recording.subprocess.Popen")
    def test_generates_sequential_clip_filenames(self, mock_popen):
        """start_recording generates clip_002.mov when clip_001 already exists."""
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=42)

            # Add an existing clip to metadata
            data["clips"].append({"file": "clip_001.mov", "subtitle": "First clip."})
            from project import save_project

            save_project(project_path, data)

            pid, clip_file = start_recording(project_path)

            self.assertEqual(pid, 99999)
            self.assertEqual(clip_file, "clip_002.mov")
            state = json.loads((data_dir(project_path) / ".recording.json").read_text())
            self.assertEqual(state["clip_file"], "clip_002.mov")

    @patch("recording.subprocess.Popen")
    def test_generates_third_clip_filename(self, mock_popen):
        """start_recording generates clip_003.mov when two clips already exist."""
        mock_proc = MagicMock()
        mock_proc.pid = 55555
        mock_popen.return_value = mock_proc

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=42)

            data["clips"].append({"file": "clip_001.mov", "subtitle": "First."})
            data["clips"].append({"file": "clip_002.mov", "subtitle": "Second."})
            from project import save_project

            save_project(project_path, data)

            start_recording(project_path)

            state = json.loads((data_dir(project_path) / ".recording.json").read_text())
            self.assertEqual(state["clip_file"], "clip_003.mov")

    @patch("recording.subprocess.Popen")
    def test_fails_if_recording_already_in_progress(self, mock_popen):
        """start_recording raises RuntimeError when .recording.json exists."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            # Create a fake .recording.json
            state_path = data_dir(project_path) / ".recording.json"
            state_path.write_text(
                json.dumps({"pid": 11111, "clip_file": "clip_001.mov"})
            )

            with self.assertRaises(RuntimeError) as ctx:
                start_recording(project_path)

            self.assertIn("already in progress", str(ctx.exception))
            # Popen should NOT have been called
            mock_popen.assert_not_called()


class TestStopRecording(unittest.TestCase):
    """Tests for stop_recording."""

    @patch("recording.time.sleep")
    @patch("recording.os.kill")
    def test_stops_recording_successfully(self, mock_kill, mock_sleep):
        """stop_recording stops the process, updates metadata, and cleans up."""

        # os.kill(pid, 0) should raise OSError to indicate process exited
        def kill_side_effect(pid, sig):
            if sig == 0:
                raise OSError("No such process")

        mock_kill.side_effect = kill_side_effect

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            # Create fake recording state
            state_path = data_dir(project_path) / ".recording.json"
            state_path.write_text(
                json.dumps({"pid": 12345, "clip_file": "clip_001.mov"})
            )

            # Create fake clip file (simulates screencapture output)
            (data_dir(project_path) / "clip_001.mov").touch()

            clip = stop_recording(project_path, "Here we configure settings.")

            self.assertEqual(clip, "clip_001.mov")

            # Verify SIGINT was sent
            import signal

            mock_kill.assert_any_call(12345, signal.SIGINT)

            # Verify .recording.json was deleted
            self.assertFalse(state_path.exists())

            # Verify metadata was updated
            metadata = load_project(project_path)
            self.assertEqual(len(metadata["clips"]), 1)
            self.assertEqual(metadata["clips"][0]["file"], "clip_001.mov")
            self.assertEqual(
                metadata["clips"][0]["subtitle"], "Here we configure settings."
            )

    @patch("recording.time.sleep")
    @patch("recording.os.kill")
    def test_fails_if_no_recording_in_progress(self, mock_kill, mock_sleep):
        """stop_recording raises RuntimeError when .recording.json doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            with self.assertRaises(RuntimeError) as ctx:
                stop_recording(project_path, "Some subtitle.")

            self.assertIn("No recording in progress", str(ctx.exception))
            mock_kill.assert_not_called()

    @patch("recording.time.sleep")
    @patch("recording.os.kill")
    def test_fails_if_clip_file_not_created(self, mock_kill, mock_sleep):
        """stop_recording raises RuntimeError when the clip file doesn't exist."""

        def kill_side_effect(pid, sig):
            if sig == 0:
                raise OSError("No such process")

        mock_kill.side_effect = kill_side_effect

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            # Create fake recording state but do NOT create the clip file
            state_path = data_dir(project_path) / ".recording.json"
            state_path.write_text(
                json.dumps({"pid": 12345, "clip_file": "clip_001.mov"})
            )

            with self.assertRaises(RuntimeError) as ctx:
                stop_recording(project_path, "Some subtitle.")

            self.assertIn("not created", str(ctx.exception))

    @patch("recording.time.time")
    @patch("recording.time.sleep")
    @patch("recording.os.kill")
    def test_fails_if_process_does_not_stop(self, mock_kill, mock_sleep, mock_time):
        """stop_recording raises RuntimeError if process doesn't exit within timeout."""
        # os.kill(pid, 0) never raises — process stays alive
        mock_kill.return_value = None

        # Simulate time progressing past the 10-second deadline
        # First call sets the deadline, subsequent calls exceed it
        mock_time.side_effect = [100.0, 100.0, 111.0]

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            state_path = data_dir(project_path) / ".recording.json"
            state_path.write_text(
                json.dumps({"pid": 12345, "clip_file": "clip_001.mov"})
            )

            with self.assertRaises(RuntimeError) as ctx:
                stop_recording(project_path, "Some subtitle.")

            self.assertIn("did not stop", str(ctx.exception))

    @patch("recording.time.sleep")
    @patch("recording.os.kill")
    def test_appends_to_existing_clips(self, mock_kill, mock_sleep):
        """stop_recording appends to existing clips in metadata."""

        def kill_side_effect(pid, sig):
            if sig == 0:
                raise OSError("No such process")

        mock_kill.side_effect = kill_side_effect

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=11121)

            # Add an existing clip
            data["clips"].append({"file": "clip_001.mov", "subtitle": "First clip."})
            from project import save_project

            save_project(project_path, data)

            # Set up recording state for clip_002
            state_path = data_dir(project_path) / ".recording.json"
            state_path.write_text(
                json.dumps({"pid": 12345, "clip_file": "clip_002.mov"})
            )
            (data_dir(project_path) / "clip_002.mov").touch()

            clip = stop_recording(project_path, "Second clip subtitle.")

            self.assertEqual(clip, "clip_002.mov")

            metadata = load_project(project_path)
            self.assertEqual(len(metadata["clips"]), 2)
            self.assertEqual(metadata["clips"][0]["file"], "clip_001.mov")
            self.assertEqual(metadata["clips"][1]["file"], "clip_002.mov")
            self.assertEqual(metadata["clips"][1]["subtitle"], "Second clip subtitle.")


if __name__ == "__main__":
    unittest.main()
