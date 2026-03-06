"""Window discovery via macOS CGWindowList API."""

import json
import subprocess

SWIFT_FIND_CHROME_WINDOWS = """\
import CoreGraphics
import Foundation

let windowList = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]] ?? []

var results: [[String: Any]] = []
for window in windowList {
    guard let ownerName = window[kCGWindowOwnerName as String] as? String,
          ownerName == "Google Chrome" else {
        continue
    }

    let windowID = window[kCGWindowNumber as String] as? Int ?? 0
    let windowName = window[kCGWindowName as String] as? String

    var entry: [String: Any] = [
        "window_id": windowID
    ]

    if let name = windowName {
        entry["name"] = name
    } else {
        entry["name"] = NSNull()
    }

    if let bounds = window[kCGWindowBounds as String] as? [String: Any],
       let width = bounds["Width"] as? Int,
       let height = bounds["Height"] as? Int {
        entry["width"] = width
        entry["height"] = height
    } else {
        entry["width"] = 0
        entry["height"] = 0
    }

    results.append(entry)
}

let jsonData = try! JSONSerialization.data(withJSONObject: results, options: [])
print(String(data: jsonData, encoding: .utf8)!)
"""


def find_chrome_windows() -> list[dict]:
    """Find all visible Google Chrome windows using macOS CGWindowList API.

    Returns a list of dicts with keys: window_id (int), name (str or None),
    width (int), height (int).

    Raises RuntimeError if the Swift subprocess fails.
    """
    result = subprocess.run(
        ["swift", "-"],
        input=SWIFT_FIND_CHROME_WINDOWS,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Swift window discovery script failed (exit code {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    windows = json.loads(result.stdout)

    return [
        {
            "window_id": int(w["window_id"]),
            "name": w.get("name"),
            "width": int(w.get("width", 0)),
            "height": int(w.get("height", 0)),
        }
        for w in windows
    ]


def _handle_find_window(args):
    """CLI handler for the find-window subcommand."""
    windows = find_chrome_windows()

    if args.json_output:
        print(json.dumps({"windows": windows}))
        return

    if not windows:
        print("No Google Chrome windows found.")
        print("Make sure Chrome is running and has at least one visible window.")
        return

    for w in windows:
        name_display = (
            f'"{w["name"]}"'
            if w["name"]
            else "(no name — grant Screen Recording permission)"
        )
        print(
            f"WindowID: {w['window_id']}  "
            f"Name: {name_display}  "
            f"Bounds: {w['width']}x{w['height']}"
        )


def register_command(subparsers):
    """Register the find-window subcommand with the argument parser."""
    parser = subparsers.add_parser(
        "find-window",
        help="Discover visible Google Chrome windows",
    )
    parser.set_defaults(handler=_handle_find_window)
