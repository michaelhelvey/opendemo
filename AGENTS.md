# opendemo

OpenDemo is a Python CLI tool designed to be used by AI agents to allow them to
easily demo work they've completed using a combination of MacOS screen recording
APIs, chrome devtools MCP, and ffmpeg

## Project Structure

Flat list of python files. No directories (for source code). Keep it simple.
`main.py` is the entrypoint.

## Commands

- **Package Manager**: `uv` is both our package manager and python runtime
  manager. exclusively use `uv`, never raw `python` or `pip`
- **Running the project**: `uv run main.py -- [ARGS]`
- **Running tests**: `uv run python -m unittest`. We use base python unittest
  for tests. We do not use pytest or any other helpers or frameworks.
- **Linting**: `uvx ruff check`. Use `uvx ruff check --fix` to automatically
  apply fixes.
- **Formatting**: `uvx ruff format`

## General Guidance

- always run linting and formatting changes before completing a task. a task is
  not complete if there are linting errors, formatting errors, or failing tests.
