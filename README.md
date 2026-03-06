# OpenDemo

Let your agents demo their web development work for you with video on MacOS. Why
is it called OpenDemo? Because every fuckin AI thing has to have the word "Open"
in it for some reason. Nothing means anything.

## Getting Started

OpenDemo is just a Python CLI. It needs access to 1) your screen, with the macos
accessibility API, and 2) an `ffmpeg` CLI 3) a way for your agent to control a
browser. I recommend
[chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp/).

It exposes all of its functionality as a CLI designed to be interacted with
agents, and includes an example prompt instructing agents to use the CLI. You
can integrate this with your favorite agent harness using whatever tooling you
like: rules files, skills, etc.

**Install**:

Clone the repository, then execute `uv sync` to install depedencies and set up
your local environment.

**Configure Permissions**:

_TODO: include instructions on how to configure permissions for screen recording
on MacOS_

**Integrate with your agent**:

_TODO: include an example workflow for integrating this tool with opencode by
creating a custom command_
