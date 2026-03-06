# OpenDemo

AI-powered demo video creator. Create narrated demo videos by recording Chrome
windows with burned-in subtitles.

What's with the name? Well, every AI thing has to have "Open" in the name for
some reason. I don't know why.

## Example

Here's [a demo](./data/demo.mp4) of [http.cat](https://http.cat) created entirely by an AI agent
using OpenDemo.

## How It Works

OpenDemo gives AI agents a structural model for creating demo videos: many small
video clips with a 1:1 clip-to-subtitle mapping, stitched together by ffmpeg.
Since agents can't watch video, each clip maps to exactly one subtitle, making
the process fully controllable.

## Requirements

- macOS (uses native `screencapture`)
- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- ffmpeg (`brew install ffmpeg`)
- Google Chrome

### macOS Permissions

Your terminal emulator must have:

1. **Screen Recording** — required for `screencapture` and window discovery
2. **Accessibility** (optional) — only if using System Events

Grant these in System Settings → Privacy & Security.

## Quick Start

```bash
# Find Chrome windows
uv run main.py find-window

# Initialize a project
uv run main.py init ./my-demo --window-id <ID> --speed 4

# Record clips (one at a time)
uv run main.py record ./my-demo
# ... interact with Chrome ...
uv run main.py stop ./my-demo --subtitle "Here we configure settings."

# Repeat record/stop for each clip

# Render final video
uv run main.py render ./my-demo

# Check project status
uv run main.py status ./my-demo
```

## Commands

### `find-window`

Discover visible Google Chrome windows and their IDs.

```bash
uv run main.py find-window
```

Prints each Chrome window's ID, name, and bounds. Use the window ID with `init`.

### `init`

Initialize a new demo project directory.

```bash
uv run main.py init <path> --window-id <ID> [--speed <N>]
```

- `<path>` — directory to create (parent directories are created automatically)
- `--window-id` — CGWindowID of the Chrome window to record (from `find-window`)
- `--speed` — render speed multiplier, 2-6 (default 4). Higher values produce
  faster playback to compensate for agent inference latency.

Creates a `metadata.json` with default render settings (1920x1080, demo.mp4).

### `record`

Start recording a clip from the project's Chrome window.

```bash
uv run main.py record <path>
```

- `<path>` — path to the project directory

Starts `screencapture` in the background and writes recording state to
`.recording.json`. Only one recording can be active at a time.

### `stop`

Stop the current recording and associate a subtitle.

```bash
uv run main.py stop <path> --subtitle "Description of what happened"
```

- `<path>` — path to the project directory
- `--subtitle` — text to burn into the video for this clip

Sends SIGINT to the screencapture process, verifies the clip file was created,
updates `metadata.json`, and cleans up recording state.

### `render`

Render the final demo video from all recorded clips.

```bash
uv run main.py render <path>
```

- `<path>` — path to the project directory

Generates a 3-second intro card, re-encodes each clip with its burned-in
subtitle, and concatenates everything into the final output file. Intermediate
files are cleaned up automatically.

### `status`

Show a summary of the project's current state.

```bash
uv run main.py status <path>
```

- `<path>` — path to the project directory

Displays the window ID, clip count with subtitles, whether a recording is in
progress, and render settings.

## JSON Output

All commands support `--json` for machine-readable output. The flag is global
and goes before the subcommand:

```bash
uv run main.py --json find-window
uv run main.py --json init ./my-demo --window-id 11121
uv run main.py --json record ./my-demo
uv run main.py --json stop ./my-demo --subtitle "Hello"
uv run main.py --json render ./my-demo
uv run main.py --json status ./my-demo
```

## Agent Command Setup

OpenDemo is designed to be driven by AI agents. The easiest way to use it is to
set up a custom `/demo` command in your coding agent so you can type
`/demo Demo the new search feature` and have the agent handle the entire
recording workflow.

### OpenCode

1. Set the `OPENDEMO_PATH` environment variable to the absolute path where you
   cloned this repository (the prompt uses it to locate the CLI):

   ```bash
   export OPENDEMO_PATH=/path/to/opendemo
   ```

2. Copy the included `demo.md` file into your OpenCode commands directory.
   You can install it globally or per-project:

   ```bash
   # Global (available in all projects)
   cp demo.md ~/.config/opencode/commands/demo.md

   # Per-project (available only in that project)
   mkdir -p .opencode/commands
   cp demo.md .opencode/commands/demo.md
   ```

3. Make sure your agent has access to a Chrome DevTools MCP server (e.g.
   `chrome-devtools`) so it can navigate and interact with Chrome.

4. Use it:

   ```
   /demo Record a walkthrough of the new settings page
   ```

### Claude Code

The same `demo.md` file works as a Claude Code custom slash command. Copy it
into your commands directory:

```bash
# Global
cp demo.md ~/.claude/commands/demo.md

# Per-project
mkdir -p .claude/commands
cp demo.md .claude/commands/demo.md
```

Then use `/demo Record a walkthrough of the new settings page` in Claude Code.

### Other Agents

The `demo.md` file is a self-contained prompt that teaches any agent the full
OpenDemo workflow. You can adapt it for other agent frameworks by extracting
the prompt content and wiring it into your agent's command system.

## Development

```bash
uv run python -m unittest      # Run tests
uvx ruff check                  # Lint
uvx ruff format                 # Format
```
