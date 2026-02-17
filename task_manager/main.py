"""Command-line entry point for deterministic task manager commands.

This module owns argument parsing and user-facing command dispatch.
Persistent data handling remains in storage.py.
"""

from __future__ import annotations

import argparse
from typing import Sequence

import agent
import storage


def _validate_positive_id(value: int, label: str) -> int:
    """Validate IDs from CLI flags so downstream logic can stay simple."""
    if value <= 0:
        raise ValueError(f"{label} must be a positive integer.")
    return value


def handle_add(task_text: str) -> None:
    """Create a task and print deterministic feedback."""
    task = storage.add_task(task_text)
    print(f"Added task {task['id']}: {task['text']}")


def handle_list() -> None:
    """Render tasks in stable ID order with completion status markers."""
    tasks = storage.list_tasks()
    if not tasks:
        print("No tasks found.")
        return

    for task in tasks:
        status = "x" if task.get("completed") else " "
        task_id = task.get("id")
        text = task.get("text", "")
        print(f"[{task_id}] [{status}] {text}")


def handle_complete(task_id: int) -> None:
    """Complete one task by ID and print outcome."""
    checked_id = _validate_positive_id(task_id, "task_id")
    success, message = storage.complete_task(checked_id)
    print(message)
    if not success:
        raise SystemExit(1)


def handle_delete(task_ids: list[int]) -> None:
    """Delete one or more task IDs with clear invalid-ID feedback."""
    validated_ids = [_validate_positive_id(task_id, "task_id") for task_id in task_ids]
    deleted_ids, missing_ids = storage.delete_tasks(validated_ids)

    if deleted_ids:
        print(f"Deleted task IDs: {', '.join(str(task_id) for task_id in deleted_ids)}")
    if missing_ids:
        print(f"Task IDs not found: {', '.join(str(task_id) for task_id in missing_ids)}")

    # Missing-only requests should fail fast so automation can detect no-op deletions.
    if not deleted_ids:
        raise SystemExit(1)


def run_goal(goal: str, progress_callback=None) -> str:
    """Shared backend entry point for CLI and GUI goal execution."""
    # Both interfaces call this function so runtime behavior stays identical.
    return agent.run_agent(goal, progress_callback=progress_callback)


def handle_goal(goal: str) -> None:
    """Run goal mode through the agent layer and print final response."""
    response = run_goal(goal)
    print(response)


def launch_gui() -> int:
    """Launch Qt UI while reusing the same backend goal entry point."""
    # Import is local so CLI usage does not require PySide6 at import time.
    import ui

    return ui.run_gui(run_goal)


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser for the deterministic task manager commands."""
    parser = argparse.ArgumentParser(description="Task manager (deterministic CLI baseline)")
    parser.add_argument("--add", type=str, help="Add a task with text")
    parser.add_argument("--list", action="store_true", help="List all tasks")
    parser.add_argument("--complete", type=int, help="Mark a task complete by task ID")
    parser.add_argument("--goal", type=str, help="Run an agent goal, e.g. \"Plan my tasks for today\"")
    parser.add_argument("--gui", action="store_true", help="Launch the PySide6 desktop UI")
    parser.add_argument(
        "--delete",
        type=int,
        nargs="+",
        help="Delete one or more task IDs from --list output",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and dispatch deterministically to one command path."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.add is not None:
            handle_add(args.add)
            return 0
        if args.gui:
            try:
                return launch_gui()
            except Exception as exc:
                print(f"GUI failed: {exc}")
                return 1
        if args.list:
            handle_list()
            return 0
        if args.goal is not None:
            try:
                handle_goal(args.goal)
                return 0
            except Exception as exc:
                print(f"Goal execution failed: {exc}")
                return 1
        if args.complete is not None:
            handle_complete(args.complete)
            return 0
        if args.delete is not None:
            handle_delete(args.delete)
            return 0
    except (ValueError, storage.StorageError) as exc:
        print(f"Command failed: {exc}")
        return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
