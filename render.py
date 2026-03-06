"""Video rendering — stitch clips with subtitles and intro card via ffmpeg."""

import json
import subprocess
from pathlib import Path

import project


def escape_subtitle(text: str) -> str:
    """Escape text for ffmpeg's drawtext filter.

    When the text is placed inside single quotes in the drawtext filter
    (e.g., text='...'), the following characters must be escaped:

    - Backslash: \\ -> \\\\  (literal backslash needs escaping)
    - Single quote: ' -> '\\'' (end quote, escaped quote, start quote)
    - Colon and semicolon are safe inside single quotes
    - Percent: % -> %%  (drawtext text expansion)
    """
    # Order matters: escape backslashes first
    text = text.replace("\\", "\\\\")
    # For single quotes inside single-quoted text, use the shell-style
    # end-quote + escaped-quote + start-quote pattern
    text = text.replace("'", "'\\''")
    text = text.replace("%", "%%")
    return text


def build_intro_command(data_path: Path, width: int, height: int) -> list[str]:
    """Return the ffmpeg command for generating a 3-second intro card."""
    output = data_path / "intro.mp4"
    return [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={width}x{height}:d=3",
        "-vf",
        "drawtext=text='Generated with OpenDemo\nhttps\\://github.com/michaelhelvey/opendemo':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]


def build_clip_render_command(
    clip_path: Path,
    rendered_path: Path,
    subtitle: str,
    width: int,
    height: int,
    font_size: int,
    speed: float = 1.0,
) -> list[str]:
    """Return the ffmpeg command for rendering a clip with burned-in subtitle."""
    escaped = escape_subtitle(subtitle)
    # Scale to fit within the target resolution while preserving aspect ratio,
    # then pad to the exact target resolution with a black background.
    # This avoids stretching tall/narrow or short/wide source windows.
    filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
    ]

    # Speed up the clip if speed > 1. setpts=PTS/N makes the video play N times
    # faster by dividing each frame's presentation timestamp.
    if speed != 1.0:
        filters.append(f"setpts=PTS/{speed}")

    filters.append(
        f"drawtext=text='{escaped}':"
        f"fontsize={font_size}:fontcolor=white:"
        f"x=(w-text_w)/2:y=h-th-50:"
        f"box=1:boxcolor=black@0.7:boxborderw=10"
    )

    vf = ",".join(filters)
    return [
        "ffmpeg",
        "-i",
        str(clip_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(rendered_path),
    ]


def build_concat_command(concat_list_path: Path, output_path: Path) -> list[str]:
    """Return the ffmpeg command for concatenating clips."""
    return [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list_path),
        "-c",
        "copy",
        str(output_path),
    ]


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run an ffmpeg command, handling errors gracefully."""
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg and ensure it is on your PATH."
        )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        raise RuntimeError(f"ffmpeg command failed: {' '.join(cmd)}\n{stderr}") from e


def render_project(project_path: str | Path) -> Path:
    """Render the full demo video from a project directory.

    Orchestrates the multi-step ffmpeg pipeline: intro card, clip re-encoding
    with subtitles, concatenation, and cleanup.

    Returns the path to the final output file.
    Raises RuntimeError if the project has no clips or ffmpeg fails.
    """
    project_path = Path(project_path)
    metadata = project.load_project(project_path)
    dd = project.data_dir(project_path)

    # Step 1: Validate
    if not metadata["clips"]:
        raise RuntimeError("Project has no clips. Record at least one clip first.")

    rs = metadata["render_settings"]
    resolution = rs["resolution"]
    width_str, height_str = resolution.split("x")
    width = int(width_str)
    height = int(height_str)
    font_size = rs.get("font_size", 28)
    speed = rs.get("speed", 1)
    output_filename = rs["output"]

    intermediate_files: list[Path] = []

    try:
        # Step 2: Generate intro card
        intro_path = dd / "intro.mp4"
        intro_cmd = build_intro_command(dd, width, height)
        _run_ffmpeg(intro_cmd)
        intermediate_files.append(intro_path)

        # Step 3: Re-encode each clip with subtitles
        rendered_paths: list[Path] = []
        for clip in metadata["clips"]:
            clip_path = dd / clip["file"]
            stem = Path(clip["file"]).stem
            rendered_name = f"{stem}_rendered.mp4"
            rendered_path = dd / rendered_name

            clip_cmd = build_clip_render_command(
                clip_path,
                rendered_path,
                clip["subtitle"],
                width,
                height,
                font_size,
                speed,
            )
            _run_ffmpeg(clip_cmd)
            rendered_paths.append(rendered_path)
            intermediate_files.append(rendered_path)

        # Step 4: Create concat list
        concat_list_path = dd / "concat_list.txt"
        intermediate_files.append(concat_list_path)

        lines = [f"file '{intro_path.name}'"]
        for rp in rendered_paths:
            lines.append(f"file '{rp.name}'")
        concat_list_path.write_text("\n".join(lines) + "\n")

        # Step 5: Concatenate
        output_path = dd / output_filename
        concat_cmd = build_concat_command(concat_list_path, output_path)
        _run_ffmpeg(concat_cmd)

    finally:
        # Step 6: Clean up intermediate files
        for f in intermediate_files:
            if f.exists():
                f.unlink()

    # Step 7: Return the output path
    return output_path


def _handle_render(args):
    """CLI handler for the render subcommand."""
    output_path = render_project(args.path)
    size_bytes = output_path.stat().st_size
    relative_output = str(Path(project.DATA_DIR) / output_path.name)

    if args.json_output:
        print(json.dumps({"output": relative_output, "size_bytes": size_bytes}))
        return

    if size_bytes >= 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        size_str = f"{size_bytes / 1024:.1f} KB"
    print(f"Rendered {relative_output} ({size_str})")


def register_command(subparsers):
    """Register the render subcommand with the argument parser."""
    parser = subparsers.add_parser(
        "render",
        help="Render the final demo video from all recorded clips",
    )
    parser.add_argument("path", help="Path to the project directory")
    parser.set_defaults(handler=_handle_render)
