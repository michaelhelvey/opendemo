"""Tests for project status command."""

import json
import tempfile
import unittest
from pathlib import Path

from project import init_project, save_project, data_dir
from status import get_status


class TestGetStatus(unittest.TestCase):
    """Tests for get_status."""

    def test_fresh_project_status(self):
        """Status of a fresh project shows no clips and no recording."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            info = get_status(project_path)

            self.assertEqual(info["project_path"], str(project_path))
            self.assertEqual(info["window_id"], 11121)
            self.assertEqual(info["clip_count"], 0)
            self.assertEqual(info["clips"], [])
            self.assertFalse(info["recording_in_progress"])
            self.assertIsNone(info["current_clip"])
            self.assertIn("output", info["render_settings"])
            self.assertIn("resolution", info["render_settings"])

    def test_status_with_clips(self):
        """Status shows correct clip count and clip details."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=42)

            data["clips"] = [
                {"file": "clip_001.mov", "subtitle": "First, let's navigate..."},
                {"file": "clip_002.mov", "subtitle": "Here we configure..."},
                {"file": "clip_003.mov", "subtitle": "And that's how..."},
            ]
            save_project(project_path, data)

            info = get_status(project_path)

            self.assertEqual(info["clip_count"], 3)
            self.assertEqual(len(info["clips"]), 3)
            self.assertEqual(info["clips"][0]["file"], "clip_001.mov")
            self.assertEqual(info["clips"][0]["subtitle"], "First, let's navigate...")
            self.assertEqual(info["clips"][2]["file"], "clip_003.mov")
            self.assertFalse(info["recording_in_progress"])

    def test_status_recording_in_progress(self):
        """Status shows recording in progress when .recording.json exists."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            # Create a .recording.json to simulate an active recording
            state = {"pid": 12345, "clip_file": "clip_001.mov"}
            (data_dir(project_path) / ".recording.json").write_text(json.dumps(state))

            info = get_status(project_path)

            self.assertTrue(info["recording_in_progress"])
            self.assertEqual(info["current_clip"], "clip_001.mov")

    def test_status_json_output(self):
        """get_status returns JSON-serializable data."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=11121)

            data["clips"] = [
                {"file": "clip_001.mov", "subtitle": "Testing JSON output."},
            ]
            save_project(project_path, data)

            info = get_status(project_path)

            # Verify it's JSON-serializable
            json_str = json.dumps(info)
            parsed = json.loads(json_str)
            self.assertEqual(parsed["clip_count"], 1)
            self.assertEqual(parsed["window_id"], 11121)
            self.assertEqual(parsed["clips"][0]["file"], "clip_001.mov")

    def test_status_missing_project(self):
        """get_status raises FileNotFoundError for nonexistent project."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            with self.assertRaises(FileNotFoundError):
                get_status(missing)

    def test_status_with_recording_and_clips(self):
        """Status shows both existing clips and an active recording."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=42)

            data["clips"] = [
                {"file": "clip_001.mov", "subtitle": "First clip."},
            ]
            save_project(project_path, data)

            # Simulate recording clip_002 in progress
            state = {"pid": 99999, "clip_file": "clip_002.mov"}
            (data_dir(project_path) / ".recording.json").write_text(json.dumps(state))

            info = get_status(project_path)

            self.assertEqual(info["clip_count"], 1)
            self.assertTrue(info["recording_in_progress"])
            self.assertEqual(info["current_clip"], "clip_002.mov")


if __name__ == "__main__":
    unittest.main()
