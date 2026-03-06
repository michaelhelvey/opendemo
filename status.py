"""Project status — show summary of a demo project."""

import json
from pathlib import Path

import project


def get_status(project_path: str | Path) -> dict:
    """Load project metadata and recording state, returning a status dict.

    Returns a dict with keys: project_path, window_id, clip_count, clips,
    recording_in_progress, current_clip (if recording), and render_settings.

    Raises FileNotFoundError if the project directory or metadata.json
    doesn't exist.
    """
    project_path = Path(project_path)
    metadata = project.load_project(project_path)

    recording_state_path = project.data_dir(project_path) / ".recording.json"
    recording_in_progress = recording_state_path.exists()
    current_clip = None

    if recording_in_progress:
        state = json.loads(recording_state_path.read_text())
        current_clip = state.get("clip_file")

    return {
        "project_path": str(project_path),
        "window_id": metadata["window_id"],
        "clip_count": len(metadata["clips"]),
        "clips": metadata["clips"],
        "recording_in_progress": recording_in_progress,
        "current_clip": current_clip,
        "render_settings": metadata["render_settings"],
    }


def _handle_status(args):
    """CLI handler for the status subcommand."""
    info = get_status(args.path)

    if args.json_output:
        print(json.dumps(info))
        return

    print(f"Project: {info['project_path']}")
    print(f"Window ID: {info['window_id']}")
    print(f"Clips: {info['clip_count']}")
    for i, clip in enumerate(info["clips"], 1):
        print(f'  {i}. {clip["file"]} \u2014 "{clip["subtitle"]}"')

    if info["recording_in_progress"]:
        print(f"Recording in progress: Yes ({info['current_clip']})")
    else:
        print("Recording in progress: No")

    rs = info["render_settings"]
    print(f"Output: {rs['output']} ({rs['resolution']})")


def register_command(subparsers):
    """Register the status subcommand with the argument parser."""
    parser = subparsers.add_parser(
        "status",
        help="Show project status and summary",
    )
    parser.add_argument("path", help="Path to the project directory")
    parser.set_defaults(handler=_handle_status)
