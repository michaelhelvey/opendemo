# OpenDemo — Core Video Pipeline Plan

## Goal

Build a Python CLI tool that allows AI agents to create demo videos with
burned-in subtitles by recording Chrome windows on macOS. The key insight is
that agents can't watch video, so we provide a structural model: many small
video clips with a 1:1 clip-to-subtitle mapping, stitched together by ffmpeg.

## Research Findings

All critical building blocks have been validated on this machine:

| Capability                    | Approach                                                                                                                                              | Verified |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| **Window discovery**          | `CGWindowListCopyWindowInfo` via inline Swift subprocess to get CGWindowIDs. Can filter by owner name ("Google Chrome") and get window name + bounds. | ✅       |
| **Window-specific recording** | `screencapture -v -x -l <CGWindowID> output.mov`                                                                                                      | ✅       |
| **Start/stop lifecycle**      | Launch `screencapture` as background process, `kill -INT <pid>` to stop gracefully. File is properly finalized.                                       | ✅       |
| **Subtitle burn-in**          | ffmpeg `drawtext` filter: `drawtext=text='...':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=h-th-50:box=1:boxcolor=black@0.7:boxborderw=10`           | ✅       |
| **Clip concatenation**        | ffmpeg concat demuxer with re-encoded H.264 clips                                                                                                     | ✅       |
| **Output format**             | screencapture produces H.264/MOV at 60fps, retina resolution (2x). ffmpeg re-encodes to MP4.                                                          | ✅       |

### Key Technical Details

- **CGWindowID ≠ AppleScript window ID.** AppleScript's `id of window` returns
  a large internal number (e.g., 330216519). `screencapture -l` requires the
  CGWindowID (e.g., 11121). We must use `CGWindowListCopyWindowInfo` to get the
  correct ID.
- **Window names require Screen Recording permission.** Without it,
  `kCGWindowName` returns nil. Bounds are always available.
- **screencapture produces retina-resolution video** (e.g., 3496×3916 for a
  1680×1890 logical window). We may want to scale down in the ffmpeg render step
  for reasonable file sizes.
- **The `kill -INT` approach** works reliably for stopping `screencapture` and
  producing a valid MOV file.

### macOS Permissions Required (document in README)

Users must grant the terminal emulator (e.g., Ghostty, iTerm2, Terminal.app):

1. **Screen Recording** — required for `screencapture` and for
   `CGWindowListCopyWindowInfo` to return window names
2. **Accessibility** — required if using System Events / AppleScript for window
   discovery (we're avoiding this by using CGWindowList directly via Swift, but
   worth noting)

## Architecture

### Project Directory Structure (for a video project)

```
my-demo/
├── metadata.json      # Manifest file
├── clip_001.mov       # Raw recording
├── clip_002.mov
└── clip_003.mov
```

### metadata.json Schema

```json
{
  "version": 1,
  "window_id": 11121,
  "clips": [
    {
      "file": "clip_001.mov",
      "subtitle": "First, let's navigate to the settings page."
    },
    {
      "file": "clip_002.mov",
      "subtitle": "Here we can configure the notification preferences."
    },
    {
      "file": "clip_003.mov",
      "subtitle": "And that's how you set up email alerts!"
    }
  ],
  "render_settings": {
    "output": "demo.mp4",
    "resolution": "1920x1080",
    "font_size": 28,
    "subtitle_position": "bottom"
  }
}
```

### CLI Commands

All via `uv run main.py <command>`:

#### 1. `find-window`

Finds Chrome windows and prints their CGWindowIDs + names.

```bash
uv run main.py find-window
# Output:
# WindowID: 11121  Name: "My App - Dashboard"  Bounds: 1680x1890
# WindowID: 10460  Name: "Google - Search"      Bounds: 1440x900
```

**Implementation:** Shell out to a small inline Swift script that calls
`CGWindowListCopyWindowInfo`, filters for Chrome, and prints results as
JSON. Parse the JSON in Python.

#### 2. `init`

Creates a new video project directory with an empty manifest.

```bash
uv run main.py init ./my-demo --window-id 11121
# Creates ./my-demo/metadata.json
```

#### 3. `record`

Starts recording the window specified in the project manifest. Returns
immediately (background process). Writes PID to a `.recording.pid` file in the
project directory.

```bash
uv run main.py record ./my-demo
# Output: Recording started (PID: 12345). Use 'stop' to finish.
```

**Implementation:** `subprocess.Popen(["screencapture", "-v", "-x", "-l",
str(window_id), clip_path])`. Write PID to `.recording.pid`.

#### 4. `stop`

Stops the current recording and associates a subtitle with the clip.

```bash
uv run main.py stop ./my-demo --subtitle "Here we configure the settings."
# Output: Saved clip_002.mov (3.2s) with subtitle.
```

**Implementation:** Read PID from `.recording.pid`, `os.kill(pid,
signal.SIGINT)`, wait for process, update `metadata.json` with the new clip
entry.

#### 5. `render`

Stitches all clips together with burned-in subtitles and produces the final
video.

```bash
uv run main.py render ./my-demo
# Output: Rendered demo.mp4 (1920x1080, 45.2s, 12.3MB)
```

**Implementation (multi-step ffmpeg pipeline):**

1. Generate an intro card (static frame, ~3 seconds):
   ```
   ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=3 \
     -vf "drawtext=text='Generated with OpenDemo\nhttps\://github.com/michaelhelvey/opendemo':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
     -c:v libx264 -pix_fmt yuv420p intro.mp4
   ```
2. For each clip, re-encode with subtitle burned in and scaled to target
   resolution:
   ```
   ffmpeg -i clip_001.mov -vf "scale=1920:1080,drawtext=text='...':..." clip_001_rendered.mp4
   ```
3. Generate a concat list file (intro first, then clips in order)
4. Concatenate all rendered clips:
   ```
   ffmpeg -f concat -safe 0 -i concat_list.txt -c copy output.mp4
   ```
5. Clean up intermediate rendered clips

## Implementation Plan

### Phase 1: Foundation & Window Discovery

**Files:** `main.py`, `window.py`

1. Set up argparse with subcommands in `main.py`
2. Implement `find-window` command in `window.py`:
   - Shell out to inline Swift script via `subprocess`
   - Parse JSON output
   - Print formatted results
3. Write tests for JSON parsing logic

### Phase 2: Project Management

**Files:** `project.py`

1. Implement `init` command:
   - Create project directory
   - Create `metadata.json` with schema version and window ID
   - Validate window ID exists (optional: call find-window to verify)
2. Implement project loading/saving helpers:
   - `load_project(path) -> dict`
   - `save_project(path, data)`
   - Validation of metadata.json schema
3. Write tests for project CRUD operations

### Phase 3: Recording Lifecycle

**Files:** `recording.py`

1. Implement `record` command:
   - Validate project exists and no recording is in progress
   - Generate next clip filename (`clip_NNN.mov`)
   - Start `screencapture` as background process
   - Write PID + clip filename to `.recording.pid`
2. Implement `stop` command:
   - Read PID from `.recording.pid`
   - Send `SIGINT` to process
   - Wait for process to exit
   - Verify output file exists and is valid
   - Update `metadata.json` with new clip entry + subtitle
   - Clean up `.recording.pid`
3. Write tests (mocking subprocess calls)

### Phase 4: Video Rendering

**Files:** `render.py`

1. Implement `render` command:
   - Load project metadata
   - Generate intro card (black background, "Generated with OpenDemo" +
     GitHub URL, centered, 3 seconds)
   - For each clip: re-encode with subtitle overlay + scale to target resolution
   - Generate concat file list (intro + clips in order)
   - Concatenate all clips
   - Clean up intermediate files
   - Print summary (duration, file size)
2. Handle edge cases:
   - Empty project (no clips) — error with helpful message
   - Single clip (still needs intro card, so concat is always used)
   - Special characters in subtitle text (ffmpeg escaping)
3. Write tests for ffmpeg command generation (not actual encoding)

### Phase 5: Polish & Agent Experience

1. Add `--json` output flag to all commands for easier agent parsing
2. Helpful error messages when permissions are missing
3. Add a `status` command to show current project state
4. README documentation including macOS permission setup

## Resolved Decisions

1. **Audio:** No audio support. Subtitle-only demos.
2. **Intro card:** Yes — every rendered video gets a prepended intro card that
   reads: `Generated with OpenDemo\nhttps://github.com/michaelhelvey/opendemo`.
   Generated as a static frame held for ~3 seconds via ffmpeg (no recording
   needed).
3. **Subtitle styling:** Uniform for the whole video via `render_settings`. No
   per-clip overrides.
4. **Commands:** `find-window`, `init`, `record`, `stop`, `render`, `status` —
   confirmed as complete set.

## Dependencies

- **Runtime:** Python 3.14+ (already configured)
- **System:** `screencapture` (built-in macOS), `ffmpeg` (homebrew), `swift`
  (Xcode CLT)
- **Python packages:** None needed for core functionality (stdlib only:
  `argparse`, `subprocess`, `json`, `os`, `signal`, `pathlib`)
