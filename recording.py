"""Recording lifecycle — start and stop screen capture clips."""

import json
import os
import signal
import subprocess
import time
from pathlib import Path

import project


def _recording_state_path(project_path: Path) -> Path:
    """Return the path to the .recording.json state file."""
    return project.data_dir(project_path) / ".recording.json"


def _next_clip_filename(metadata: dict) -> str:
    """Generate the next sequential clip filename (clip_NNN.mov).

    Looks at existing clips in metadata and returns the next number.
    """
    existing = len(metadata["clips"])
    number = existing + 1
    return f"clip_{number:03d}.mov"


def start_recording(project_path: str | Path) -> tuple[int, str]:
    """Start a screen recording for the project.

    Loads the project metadata, verifies no recording is in progress,
    starts screencapture as a background process, and writes recording
    state to .recording.json.

    Returns a tuple of (PID, clip_filename).

    Raises RuntimeError if a recording is already in progress.
    """
    project_path = Path(project_path)
    metadata = project.load_project(project_path)

    state_path = _recording_state_path(project_path)
    if state_path.exists():
        raise RuntimeError(
            "A recording is already in progress. Use 'stop' to finish it first."
        )

    clip_filename = _next_clip_filename(metadata)
    clip_path = project.data_dir(project_path) / clip_filename

    window_id = metadata["window_id"]
    proc = subprocess.Popen(
        ["screencapture", "-v", "-x", "-l", str(window_id), str(clip_path)]
    )

    state = {"pid": proc.pid, "clip_file": clip_filename}
    state_path.write_text(json.dumps(state, indent=2) + "\n")

    return proc.pid, clip_filename


def stop_recording(project_path: str | Path, subtitle: str) -> str:
    """Stop an in-progress screen recording.

    Reads recording state from .recording.json, sends SIGINT to the
    screencapture process, waits for it to exit, verifies the clip file
    was created, updates metadata.json, and cleans up state.

    Returns the clip filename.

    Raises RuntimeError if no recording is in progress, the process
    won't stop, or the clip file wasn't created.
    """
    project_path = Path(project_path)
    metadata = project.load_project(project_path)

    state_path = _recording_state_path(project_path)
    if not state_path.exists():
        raise RuntimeError("No recording in progress.")

    state = json.loads(state_path.read_text())
    pid = state["pid"]
    clip_filename = state["clip_file"]

    # Send SIGINT to stop screencapture
    os.kill(pid, signal.SIGINT)

    # Wait for the process to exit (up to 10 seconds)
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            # Process has exited
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(
            f"Recording process (PID: {pid}) did not stop within 10 seconds."
        )

    # Verify the clip file was created
    clip_path = project.data_dir(project_path) / clip_filename
    if not clip_path.is_file():
        raise RuntimeError(
            f"Clip file {clip_filename} was not created. The recording may have failed."
        )

    # Update metadata with the new clip
    metadata["clips"].append({"file": clip_filename, "subtitle": subtitle})
    project.save_project(project_path, metadata)

    # Clean up state file
    state_path.unlink()

    return clip_filename


def _handle_record(args):
    """CLI handler for the record subcommand."""
    pid, clip_file = start_recording(args.path)

    if args.json_output:
        print(json.dumps({"pid": pid, "clip_file": clip_file}))
        return

    print(f"Recording started (PID: {pid}). Use 'stop' to finish.")


def _handle_stop(args):
    """CLI handler for the stop subcommand."""
    clip_file = stop_recording(args.path, args.subtitle)

    if args.json_output:
        print(json.dumps({"clip_file": clip_file, "subtitle": args.subtitle}))
        return

    print(f"Saved {clip_file} with subtitle.")


def register_commands(subparsers):
    """Register the record and stop subcommands with the argument parser."""
    record_parser = subparsers.add_parser(
        "record",
        help="Start recording a clip",
    )
    record_parser.add_argument("path", help="Path to the project directory")
    record_parser.set_defaults(handler=_handle_record)

    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop recording and save the clip",
    )
    stop_parser.add_argument("path", help="Path to the project directory")
    stop_parser.add_argument(
        "--subtitle",
        required=True,
        help="Subtitle text for the recorded clip",
    )
    stop_parser.set_defaults(handler=_handle_stop)
