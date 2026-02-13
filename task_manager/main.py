"""Command-line entry point for the minimal task manager."""

from __future__ import annotations

import argparse

from storage import add_task, list_tasks, mark_done


# Build the command-line interface structure and arguments.
def build_parser() -> argparse.ArgumentParser:
    """Define CLI arguments and subcommands."""
    parser = argparse.ArgumentParser(description="Minimal task manager CLI")
    # Optional goal mode: routes execution to the agent layer.
    parser.add_argument(
        "--goal",
        help='Natural-language goal for agent mode, e.g. --goal "Plan my tasks for today"',
    )

    # Deterministic task commands remain available as subcommands.
    subparsers = parser.add_subparsers(dest="command")

    # `add` creates a new task from a title string.
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Task title")

    # `list` prints all tasks.
    subparsers.add_parser("list", help="List all tasks")

    # `done` marks one task complete by numeric id.
    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("id", type=int, help="Task id")

    return parser


# Parse command input and call the requested task operation.
def main() -> None:
    """Parse command-line args and dispatch to storage actions."""
    parser = build_parser()
    args = parser.parse_args()

    if args.goal and args.command:
        parser.error("Use either --goal or a subcommand (add/list/done), not both.")

    if args.goal:
        try:
            # Lazy import keeps deterministic commands working without OpenAI dependencies.
            from agent import run_agent
        except ModuleNotFoundError as exc:
            print(f"Agent mode unavailable: missing dependency ({exc}).")
            return

        result = run_agent(args.goal)
        if result:
            print(result)
        return

    if args.command == "add":
        add_task(args.title)
    elif args.command == "list":
        list_tasks()
    elif args.command == "done":
        mark_done(args.id)
    else:
        parser.error("Provide either --goal or one subcommand: add, list, done.")


if __name__ == "__main__":
    main()
