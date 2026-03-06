"""Tests for project management — init, load, save, and validation."""

import json
import tempfile
import unittest
from pathlib import Path

from project import (
    init_project,
    load_project,
    save_project,
    DATA_DIR,
    DEFAULT_SPEED,
    MIN_SPEED,
    MAX_SPEED,
)


def _valid_metadata(window_id=11121):
    """Return a valid metadata dict for testing."""
    return {
        "version": 1,
        "window_id": window_id,
        "clips": [],
        "render_settings": {
            "output": "demo.mp4",
            "resolution": "1920x1080",
            "font_size": 28,
            "subtitle_position": "bottom",
        },
    }


class TestInitProject(unittest.TestCase):
    """Tests for init_project."""

    def test_creates_directory_and_metadata(self):
        """init_project creates the project directory, .data dir, and a valid metadata.json."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=11121)

            self.assertTrue(project_path.is_dir())
            self.assertTrue((project_path / DATA_DIR).is_dir())
            metadata_path = project_path / "metadata.json"
            self.assertTrue(metadata_path.is_file())

            written = json.loads(metadata_path.read_text())
            self.assertEqual(written["version"], 1)
            self.assertEqual(written["window_id"], 11121)
            self.assertEqual(written["clips"], [])
            self.assertIn("output", written["render_settings"])
            self.assertIn("resolution", written["render_settings"])

            # Return value matches what was written
            self.assertEqual(data, written)

    def test_creates_nested_directories(self):
        """init_project creates parent directories as needed."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "a" / "b" / "c"
            init_project(project_path, window_id=42)
            self.assertTrue((project_path / "metadata.json").is_file())

    def test_fails_if_metadata_already_exists(self):
        """init_project raises FileExistsError if metadata.json already exists."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            with self.assertRaises(FileExistsError):
                init_project(project_path, window_id=99999)

    def test_default_speed(self):
        """init_project uses DEFAULT_SPEED when speed is not specified."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "speed-demo"
            data = init_project(project_path, window_id=11121)
            self.assertEqual(data["render_settings"]["speed"], DEFAULT_SPEED)

    def test_custom_speed(self):
        """init_project respects a custom speed within the valid range."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "speed-demo"
            data = init_project(project_path, window_id=11121, speed=2)
            self.assertEqual(data["render_settings"]["speed"], 2)

    def test_speed_at_boundaries(self):
        """init_project accepts speed at both MIN_SPEED and MAX_SPEED."""
        for speed in (MIN_SPEED, MAX_SPEED):
            with tempfile.TemporaryDirectory() as tmp:
                project_path = Path(tmp) / "speed-demo"
                data = init_project(project_path, window_id=11121, speed=speed)
                self.assertEqual(data["render_settings"]["speed"], speed)

    def test_speed_below_minimum_raises(self):
        """init_project raises ValueError when speed is below MIN_SPEED."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "speed-demo"
            with self.assertRaises(ValueError) as ctx:
                init_project(project_path, window_id=11121, speed=MIN_SPEED - 1)
            self.assertIn("Speed must be between", str(ctx.exception))

    def test_speed_above_maximum_raises(self):
        """init_project raises ValueError when speed is above MAX_SPEED."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "speed-demo"
            with self.assertRaises(ValueError) as ctx:
                init_project(project_path, window_id=11121, speed=MAX_SPEED + 1)
            self.assertIn("Speed must be between", str(ctx.exception))


class TestLoadProject(unittest.TestCase):
    """Tests for load_project."""

    def test_loads_valid_metadata(self):
        """load_project returns correct dict for valid metadata.json."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "proj"
            project_path.mkdir()
            metadata = _valid_metadata()
            (project_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

            loaded = load_project(project_path)
            self.assertEqual(loaded, metadata)

    def test_raises_file_not_found_for_missing_directory(self):
        """load_project raises FileNotFoundError for a nonexistent directory."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            with self.assertRaises(FileNotFoundError):
                load_project(missing)

    def test_raises_file_not_found_for_missing_metadata(self):
        """load_project raises FileNotFoundError when directory exists but metadata.json doesn't."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_project(tmp)

    def test_raises_value_error_for_invalid_json(self):
        """load_project raises ValueError for malformed JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "metadata.json").write_text("{not valid json")
            with self.assertRaises(ValueError):
                load_project(tmp)

    def test_raises_value_error_for_missing_version(self):
        """load_project raises ValueError when 'version' key is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            del data["version"]
            (Path(tmp) / "metadata.json").write_text(json.dumps(data))

            with self.assertRaises(ValueError) as ctx:
                load_project(tmp)
            self.assertIn("version", str(ctx.exception))

    def test_raises_value_error_for_missing_window_id(self):
        """load_project raises ValueError when 'window_id' key is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            del data["window_id"]
            (Path(tmp) / "metadata.json").write_text(json.dumps(data))

            with self.assertRaises(ValueError) as ctx:
                load_project(tmp)
            self.assertIn("window_id", str(ctx.exception))

    def test_raises_value_error_for_missing_clips(self):
        """load_project raises ValueError when 'clips' key is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            del data["clips"]
            (Path(tmp) / "metadata.json").write_text(json.dumps(data))

            with self.assertRaises(ValueError) as ctx:
                load_project(tmp)
            self.assertIn("clips", str(ctx.exception))

    def test_raises_value_error_for_missing_render_settings(self):
        """load_project raises ValueError when 'render_settings' key is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            del data["render_settings"]
            (Path(tmp) / "metadata.json").write_text(json.dumps(data))

            with self.assertRaises(ValueError) as ctx:
                load_project(tmp)
            self.assertIn("render_settings", str(ctx.exception))

    def test_raises_value_error_for_missing_render_settings_output(self):
        """load_project raises ValueError when render_settings lacks 'output'."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            del data["render_settings"]["output"]
            (Path(tmp) / "metadata.json").write_text(json.dumps(data))

            with self.assertRaises(ValueError) as ctx:
                load_project(tmp)
            self.assertIn("output", str(ctx.exception))

    def test_raises_value_error_for_wrong_version(self):
        """load_project raises ValueError when version is not 1."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            data["version"] = 99
            (Path(tmp) / "metadata.json").write_text(json.dumps(data))

            with self.assertRaises(ValueError) as ctx:
                load_project(tmp)
            self.assertIn("version", str(ctx.exception).lower())

    def test_raises_value_error_for_non_int_window_id(self):
        """load_project raises ValueError when window_id is not an int."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            data["window_id"] = "not-an-int"
            (Path(tmp) / "metadata.json").write_text(json.dumps(data))

            with self.assertRaises(ValueError) as ctx:
                load_project(tmp)
            self.assertIn("window_id", str(ctx.exception))


class TestSaveProject(unittest.TestCase):
    """Tests for save_project."""

    def test_writes_valid_json_roundtrip(self):
        """save_project writes JSON that load_project can read back identically."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata(window_id=42)
            save_project(tmp, data)

            loaded = load_project(tmp)
            self.assertEqual(loaded, data)

    def test_writes_with_indent(self):
        """save_project writes human-readable indented JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            data = _valid_metadata()
            save_project(tmp, data)

            raw = (Path(tmp) / "metadata.json").read_text()
            # Indented JSON has newlines and spaces
            self.assertIn("\n", raw)
            self.assertIn("  ", raw)

    def test_rejects_invalid_data(self):
        """save_project raises ValueError for data missing required keys."""
        with tempfile.TemporaryDirectory() as tmp:
            bad_data = {"version": 1}  # missing window_id, clips, render_settings
            with self.assertRaises(ValueError):
                save_project(tmp, bad_data)

            # metadata.json should NOT have been written
            self.assertFalse((Path(tmp) / "metadata.json").exists())

    def test_rejects_non_dict(self):
        """save_project raises ValueError when data is not a dict."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                save_project(tmp, "not a dict")


if __name__ == "__main__":
    unittest.main()
