"""Project management — directory creation and metadata.json handling."""

import json
from pathlib import Path

DATA_DIR = ".data"

DEFAULT_SPEED = 4
MIN_SPEED = 2
MAX_SPEED = 6

DEFAULT_RENDER_SETTINGS = {
    "output": "demo.mp4",
    "resolution": "1920x1080",
    "font_size": 28,
    "subtitle_position": "bottom",
    "speed": DEFAULT_SPEED,
}


def data_dir(project_path: str | Path) -> Path:
    """Return the .data directory path for a project."""
    return Path(project_path) / DATA_DIR


def _validate_metadata(data: dict) -> None:
    """Validate that metadata has all required keys with correct types.

    Raises ValueError if validation fails.
    """
    if not isinstance(data, dict):
        raise ValueError("Metadata must be a dict")

    if "version" not in data:
        raise ValueError("Metadata missing required key: 'version'")
    if data["version"] != 1:
        raise ValueError(
            f"Unsupported metadata version: {data['version']} (expected 1)"
        )

    if "window_id" not in data:
        raise ValueError("Metadata missing required key: 'window_id'")
    if not isinstance(data["window_id"], int):
        raise ValueError("'window_id' must be an int")

    if "clips" not in data:
        raise ValueError("Metadata missing required key: 'clips'")
    if not isinstance(data["clips"], list):
        raise ValueError("'clips' must be a list")

    if "render_settings" not in data:
        raise ValueError("Metadata missing required key: 'render_settings'")
    if not isinstance(data["render_settings"], dict):
        raise ValueError("'render_settings' must be a dict")

    rs = data["render_settings"]
    for key in ("output", "resolution"):
        if key not in rs:
            raise ValueError(f"'render_settings' missing required key: '{key}'")


def load_project(path: str | Path) -> dict:
    """Load and validate metadata.json from a project directory.

    Raises FileNotFoundError if the directory or metadata.json doesn't exist.
    Raises ValueError if the JSON is invalid or missing required keys.
    """
    project_dir = Path(path)
    if not project_dir.is_dir():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    metadata_path = project_dir / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"metadata.json not found in {project_dir}")

    try:
        data = json.loads(metadata_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in metadata.json: {e}") from e

    _validate_metadata(data)
    return data


def save_project(path: str | Path, data: dict) -> None:
    """Write metadata.json to the project directory.

    Validates data before writing. Raises ValueError if data is invalid.
    """
    _validate_metadata(data)

    project_dir = Path(path)
    metadata_path = project_dir / "metadata.json"
    metadata_path.write_text(json.dumps(data, indent=2) + "\n")


def init_project(path: str | Path, window_id: int, speed: int | None = None) -> dict:
    """Create a new project directory with default metadata.json.

    Creates the directory (and parents) if needed. Raises FileExistsError if
    metadata.json already exists in the directory.

    Args:
        path: Directory to create for the project.
        window_id: CGWindowID of the Chrome window to record.
        speed: Render speed multiplier (2-6). Defaults to DEFAULT_SPEED.

    Returns the created metadata dict.
    """
    if speed is None:
        speed = DEFAULT_SPEED
    if not (MIN_SPEED <= speed <= MAX_SPEED):
        raise ValueError(
            f"Speed must be between {MIN_SPEED} and {MAX_SPEED}, got {speed}"
        )

    project_dir = Path(path)
    metadata_path = project_dir / "metadata.json"

    if metadata_path.exists():
        raise FileExistsError(f"metadata.json already exists in {project_dir}")

    project_dir.mkdir(parents=True, exist_ok=True)
    data_dir(project_dir).mkdir(exist_ok=True)

    render_settings = dict(DEFAULT_RENDER_SETTINGS)
    render_settings["speed"] = speed

    data = {
        "version": 1,
        "window_id": window_id,
        "clips": [],
        "render_settings": render_settings,
    }

    save_project(project_dir, data)
    return data


def _handle_init(args):
    """CLI handler for the init subcommand."""
    data = init_project(args.path, args.window_id, speed=args.speed)

    if args.json_output:
        print(json.dumps({"project_path": args.path, "window_id": data["window_id"]}))
        return

    print(f"Initialized new project at {args.path} with window ID {data['window_id']}")


def register_command(subparsers):
    """Register the init subcommand with the argument parser."""
    parser = subparsers.add_parser(
        "init",
        help="Initialize a new demo project directory",
    )
    parser.add_argument("path", help="Path to the project directory")
    parser.add_argument(
        "--window-id",
        type=int,
        required=True,
        help="CGWindowID of the Chrome window to record",
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=None,
        help=f"Render speed multiplier ({MIN_SPEED}-{MAX_SPEED}, default {DEFAULT_SPEED})",
    )
    parser.set_defaults(handler=_handle_init)
