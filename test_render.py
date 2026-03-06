"""Tests for video rendering — command generation, escaping, and orchestration."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from project import init_project, save_project, data_dir
from render import (
    build_clip_render_command,
    build_concat_command,
    build_intro_command,
    escape_subtitle,
    render_project,
)


class TestEscapeSubtitle(unittest.TestCase):
    """Tests for escape_subtitle."""

    def test_normal_text_unchanged(self):
        """Normal text without special characters passes through unchanged."""
        self.assertEqual(escape_subtitle("Hello world"), "Hello world")

    def test_colons_unchanged(self):
        """Colons are safe inside single-quoted drawtext text."""
        self.assertEqual(escape_subtitle("key: value"), "key: value")

    def test_escapes_single_quotes(self):
        """Single quotes use end-quote, escaped-quote, start-quote pattern."""
        self.assertEqual(escape_subtitle("it's done"), "it'\\''s done")

    def test_escapes_backslashes(self):
        """Backslashes are escaped for drawtext filter."""
        self.assertEqual(escape_subtitle("path\\file"), "path\\\\file")

    def test_escapes_percent_signs(self):
        """Percent signs are escaped for drawtext filter."""
        self.assertEqual(escape_subtitle("100% done"), "100%% done")

    def test_escapes_combined_special_chars(self):
        """Multiple special characters in one string are all escaped."""
        result = escape_subtitle("it's 100%: done\\ok")
        self.assertEqual(result, "it'\\''s 100%%: done\\\\ok")


class TestBuildIntroCommand(unittest.TestCase):
    """Tests for build_intro_command."""

    def test_generates_correct_command(self):
        """build_intro_command produces the correct ffmpeg command list."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)
            cmd = build_intro_command(project_path, 1920, 1080)

            self.assertEqual(cmd[0], "ffmpeg")
            self.assertIn("-f", cmd)
            self.assertIn("lavfi", cmd)

            # Check color source with correct resolution
            color_arg = cmd[cmd.index("-i") + 1]
            self.assertIn("1920x1080", color_arg)
            self.assertIn("d=3", color_arg)

            # Check drawtext filter is present
            vf_arg = cmd[cmd.index("-vf") + 1]
            self.assertIn("drawtext", vf_arg)
            self.assertIn("Generated with OpenDemo", vf_arg)

            # Check output codec
            self.assertIn("libx264", cmd)
            self.assertIn("yuv420p", cmd)

            # Check output path
            self.assertEqual(cmd[-1], str(project_path / "intro.mp4"))

    def test_uses_custom_resolution(self):
        """build_intro_command uses the provided width and height."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp)
            cmd = build_intro_command(project_path, 1280, 720)

            color_arg = cmd[cmd.index("-i") + 1]
            self.assertIn("1280x720", color_arg)


class TestBuildClipRenderCommand(unittest.TestCase):
    """Tests for build_clip_render_command."""

    def test_generates_correct_command(self):
        """build_clip_render_command produces the correct ffmpeg command."""
        clip_path = Path("/project/clip_001.mov")
        rendered_path = Path("/project/clip_001_rendered.mp4")

        cmd = build_clip_render_command(
            clip_path, rendered_path, "Hello world", 1920, 1080, 28
        )

        self.assertEqual(cmd[0], "ffmpeg")
        self.assertEqual(cmd[cmd.index("-i") + 1], str(clip_path))

        vf_arg = cmd[cmd.index("-vf") + 1]
        self.assertIn("scale=1920:1080:force_original_aspect_ratio=decrease", vf_arg)
        self.assertIn("pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black", vf_arg)
        self.assertIn("drawtext=text='Hello world'", vf_arg)
        self.assertIn("fontsize=28", vf_arg)
        self.assertIn("fontcolor=white", vf_arg)
        self.assertIn("boxcolor=black@0.7", vf_arg)
        # No setpts when speed is default 1.0
        self.assertNotIn("setpts", vf_arg)

        self.assertIn("libx264", cmd)
        self.assertEqual(cmd[-1], str(rendered_path))

    def test_applies_speed_multiplier(self):
        """build_clip_render_command adds setpts filter when speed > 1."""
        clip_path = Path("/project/clip_001.mov")
        rendered_path = Path("/project/clip_001_rendered.mp4")

        cmd = build_clip_render_command(
            clip_path, rendered_path, "Hello", 1920, 1080, 28, speed=3.0
        )

        vf_arg = cmd[cmd.index("-vf") + 1]
        self.assertIn("setpts=PTS/3.0", vf_arg)

    def test_no_setpts_at_speed_1(self):
        """build_clip_render_command omits setpts when speed is 1."""
        clip_path = Path("/project/clip_001.mov")
        rendered_path = Path("/project/clip_001_rendered.mp4")

        cmd = build_clip_render_command(
            clip_path, rendered_path, "Hello", 1920, 1080, 28, speed=1.0
        )

        vf_arg = cmd[cmd.index("-vf") + 1]
        self.assertNotIn("setpts", vf_arg)

    def test_uses_escaped_subtitle(self):
        """build_clip_render_command properly escapes subtitle text."""
        clip_path = Path("/project/clip_001.mov")
        rendered_path = Path("/project/clip_001_rendered.mp4")

        cmd = build_clip_render_command(
            clip_path, rendered_path, "it's 100%: done", 1920, 1080, 36
        )

        vf_arg = cmd[cmd.index("-vf") + 1]
        # Single quotes use the end-quote + escaped-quote + start-quote pattern
        self.assertIn("it'\\''s 100%%: done", vf_arg)


class TestBuildConcatCommand(unittest.TestCase):
    """Tests for build_concat_command."""

    def test_generates_correct_command(self):
        """build_concat_command produces the correct ffmpeg concat command."""
        concat_list = Path("/project/concat_list.txt")
        output = Path("/project/demo.mp4")

        cmd = build_concat_command(concat_list, output)

        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-f", cmd)
        self.assertIn("concat", cmd)
        self.assertIn("-safe", cmd)
        self.assertIn("0", cmd)
        self.assertEqual(cmd[cmd.index("-i") + 1], str(concat_list))
        self.assertIn("-c", cmd)
        self.assertIn("copy", cmd)
        self.assertEqual(cmd[-1], str(output))


class TestRenderProject(unittest.TestCase):
    """Tests for render_project orchestration."""

    def test_raises_error_when_no_clips(self):
        """render_project raises RuntimeError when project has no clips."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            init_project(project_path, window_id=11121)

            with self.assertRaises(RuntimeError) as ctx:
                render_project(project_path)

            self.assertIn("no clips", str(ctx.exception))

    @patch("render.subprocess.run")
    def test_orchestrates_full_pipeline(self, mock_run):
        """render_project calls ffmpeg correctly and cleans up intermediate files."""
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "my-demo"
            data = init_project(project_path, window_id=11121)
            dd = data_dir(project_path)

            # Add two clips to metadata
            data["clips"] = [
                {"file": "clip_001.mov", "subtitle": "First clip narration."},
                {"file": "clip_002.mov", "subtitle": "Second clip narration."},
            ]
            save_project(project_path, data)

            # Create fake clip files
            (dd / "clip_001.mov").touch()
            (dd / "clip_002.mov").touch()

            # Mock subprocess.run to create the output file when concat runs
            def side_effect(cmd, **kwargs):
                # Create output file when the concat command runs
                if "-f" in cmd and "concat" in cmd:
                    output_file = Path(cmd[-1])
                    output_file.write_bytes(b"fake video data " * 100)

            mock_run.side_effect = side_effect

            result = render_project(project_path)

            # Verify subprocess.run was called 4 times:
            # 1: intro, 2: clip_001 render, 3: clip_002 render, 4: concat
            self.assertEqual(mock_run.call_count, 4)

            # Verify call order by inspecting commands
            calls = mock_run.call_args_list

            # Call 1: intro card generation
            intro_cmd = calls[0][0][0]
            self.assertEqual(intro_cmd[0], "ffmpeg")
            self.assertIn("lavfi", intro_cmd)

            # Call 2: first clip render
            clip1_cmd = calls[1][0][0]
            self.assertIn(str(dd / "clip_001.mov"), clip1_cmd)
            self.assertIn(str(dd / "clip_001_rendered.mp4"), clip1_cmd)

            # Call 3: second clip render
            clip2_cmd = calls[2][0][0]
            self.assertIn(str(dd / "clip_002.mov"), clip2_cmd)
            self.assertIn(str(dd / "clip_002_rendered.mp4"), clip2_cmd)

            # Call 4: concatenation
            concat_cmd = calls[3][0][0]
            self.assertIn("concat", concat_cmd)

            # All calls used check=True and capture_output=True
            for c in calls:
                self.assertTrue(c[1].get("check", False))
                self.assertTrue(c[1].get("capture_output", False))

            # Verify output path
            self.assertEqual(result, dd / "demo.mp4")

            # Verify intermediate files were cleaned up
            self.assertFalse((dd / "intro.mp4").exists())
            self.assertFalse((dd / "clip_001_rendered.mp4").exists())
            self.assertFalse((dd / "clip_002_rendered.mp4").exists())
            self.assertFalse((dd / "concat_list.txt").exists())

            # Verify original clip files still exist
            self.assertTrue((dd / "clip_001.mov").exists())
            self.assertTrue((dd / "clip_002.mov").exists())


if __name__ == "__main__":
    unittest.main()
