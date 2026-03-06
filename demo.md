---
description: Record a demo video of your recent work
---

You are going to create a demo video using the OpenDemo CLI tool. The video will
consist of short screen recordings of a Chrome window, each annotated with a
subtitle, stitched together into a single MP4.

## Your task

$ARGUMENTS

## How OpenDemo works

OpenDemo provides a structural model for creating demo videos: many small video
clips with a 1:1 clip-to-subtitle mapping, stitched together by ffmpeg. Since
you can't watch video, each clip maps to exactly one subtitle, making the
process fully controllable.

The CLI is located at the path shown below. All commands are run via
`uv run main.py` from the OpenDemo project directory.

**OpenDemo path:** !`echo $OPENDEMO_PATH`

If `$OPENDEMO_PATH` is empty, look for an `OPENDEMO_PATH` environment variable
or ask the user where OpenDemo is installed.

## Step-by-step workflow

### 1. Plan the demo

Before recording anything, write a script. Remember, this is a demo, not an e2e
test. Your target audience is other developers or product managers who
want to see what you've accomplished.

Your script should be focused on a sequence of clips that guide the user through
the happy path(s) of what you've built. Each clip should demonstrate one action
or concept and have a short subtitle (under 80 characters). Write your plan out
as a todo list so the user can see it.

### 2. Find the Chrome window

```bash
uv run main.py find-window
```

This lists all visible Chrome windows with their CGWindowIDs. Pick the one
showing the page you want to demo. If no Chrome window is open, ask the user to
open Chrome and navigate to the relevant page.

### 3. Initialize a project

Before initializing, **ask the user** what render speed they'd like. The speed
controls how much the final video is sped up (to compensate for agent inference
latency). Offer a range of 2-6x, defaulting to 4x. Lower values produce
slower, more readable videos; higher values keep the demo snappy.

```bash
uv run main.py init ./demo --window-id <ID> --speed <SPEED>
```

Use a descriptive directory name. The `--window-id` comes from the previous
step. The `--speed` flag is optional and defaults to 4.

### 4. Record clips one at a time

For each clip in your plan:

1. **Navigate Chrome** to the right state using chrome devtools MCP tools
   (navigate_page, click, fill, etc.). Do all navigation BEFORE starting the
   recording.

2. **Start recording:**

   ```bash
   uv run main.py record ./demo
   ```

3. **Perform the action** you want to capture. Keep it focused: one action per
   clip. Do not sleep between clips -- you are slow enough on your own due to
   inference speed to let the page settle.

4. **Stop recording with a subtitle:**
   ```bash
   uv run main.py stop ./demo --subtitle "Brief description of what just happened."
   ```

Repeat for all clips.

**Important rules:**

- Never switch Chrome tabs between `record` and `stop` -- it will record the
  wrong content. Do all tab switching before you start recording.
- Keep subtitles concise. They are burned into the video at the bottom of the
  frame.
- Don't use `select_page` with `bringToFront` while a recording is active.
- If a recording fails, you can just `record` and `stop` again -- clips are
  appended sequentially.

### 5. Render the final video

```bash
uv run main.py render ./demo
```

This generates a 3-second intro card, burns subtitles into each clip, speeds
them up (at the speed configured during `init`, default 4x), and
concatenates everything into a single MP4 inside the project's `.data/`
directory.

### 6. Report the result

Tell the user where the output file is and how many clips were included. Use
the `status` command if you need to check:

```bash
uv run main.py status ./demo
```

## Tips

- All commands support `--json` for machine-readable output. The flag goes
  before the subcommand: `uv run main.py --json find-window`
- The default render speed is 4x. This is set via `--speed` during `init` and
  stored in `metadata.json` under `render_settings.speed`. It can also be
  edited directly in that file after initialization.
- The output resolution defaults to 1920x1080. Tall/narrow Chrome windows are
  automatically pillarboxed (black bars on the sides), not stretched.
- If you need to re-record a clip, there is no delete command. Edit the
  `metadata.json` file directly to remove a clip entry, then record a
  replacement.
