"""Command-line entry point for the minimal task manager."""

from __future__ import annotations

import argparse
from typing import Callable

from storage import add_task, list_tasks, mark_done


# Build the command-line interface structure and arguments.
def build_parser() -> argparse.ArgumentParser:
    """Define CLI arguments and subcommands."""
    parser = argparse.ArgumentParser(description="Minimal task manager CLI")
    # Optional GUI mode: launches the desktop UI while reusing backend functions in this module.
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch desktop UI mode",
    )
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


def run_goal(goal: str, on_event: Callable[[dict], None] | None = None) -> str:
    """Run goal mode and return text output for callers like CLI or UI.

    Separation of concerns:
    - UI code should call this function and display returned text.
    - OpenAI/agent logic stays in `agent.py`, not in the UI layer.
    - Optional `on_event` is instrumentation-only and does not affect execution flow.
    """
    if not goal.strip():
        return "Please enter a non-empty goal."

    try:
        # Lazy import keeps deterministic commands working without OpenAI dependencies.
        from agent import run_agent
    except ModuleNotFoundError as exc:
        return f"Agent mode unavailable: missing dependency ({exc})."

    try:
        result = run_agent(goal, on_event=on_event)
    except Exception as exc:
        return f"Agent execution failed: {exc}"

    return result or "No result returned."


def launch_gui() -> None:
    """Launch GUI mode.

    CLI and GUI share the same backend (`run_goal`) so behavior stays consistent
    and logic is not duplicated across interfaces.
    """
    # Lazy import avoids GUI dependency loading unless user explicitly asks for it.
    from ui import create_window

    # Inject shared backend function so UI does not import this module directly.
    app = create_window(run_goal)
    app.mainloop()


# Parse command input and call the requested task operation.
def main() -> None:
    """Parse command-line args and dispatch to storage actions."""
    parser = build_parser()
    args = parser.parse_args()

    if args.gui and args.goal:
        parser.error("Use either --gui or --goal, not both.")

    if args.gui and args.command:
        parser.error("Use either --gui or a subcommand (add/list/done), not both.")

    if args.goal and args.command:
        parser.error("Use either --goal or a subcommand (add/list/done), not both.")

    if args.gui:
        launch_gui()
        return

    if args.goal:
        result = run_goal(args.goal)
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
        parser.error("Provide --gui, --goal, or one subcommand: add, list, done.")


if __name__ == "__main__":
    main()
