"""OpenDemo — AI-powered demo video creator."""

import argparse

import project
import recording
import render
import status
import window


def main():
    parser = argparse.ArgumentParser(
        description="OpenDemo — AI-powered demo video creator",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Output results as JSON for machine parsing",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register subcommands
    window.register_command(subparsers)
    project.register_command(subparsers)
    recording.register_commands(subparsers)
    render.register_command(subparsers)
    status.register_command(subparsers)

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
