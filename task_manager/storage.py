"""Persistence boundary for the task manager.

This module owns JSON read/write responsibilities only.
Command flow decisions and user interaction stay in main.py or higher layers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DB_PATH = Path("tasks_db.json")


class StorageError(RuntimeError):
    """Raised when persistent task data cannot be safely loaded or saved."""


def _ensure_db_exists() -> None:
    """Create an empty JSON list file if the task database does not exist."""
    if not DB_PATH.exists():
        DB_PATH.write_text("[]\n", encoding="utf-8")


def load_tasks() -> list[dict[str, Any]]:
    """Load task records from JSON storage, validating the top-level structure."""
    _ensure_db_exists()
    try:
        # utf-8-sig keeps Windows-generated UTF-8 BOM files readable.
        data = json.loads(DB_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise StorageError(f"Task DB is not valid JSON: {DB_PATH}") from exc
    except OSError as exc:
        raise StorageError(f"Failed reading task DB: {DB_PATH}") from exc

    if not isinstance(data, list):
        raise StorageError("Task DB must contain a JSON list.")

    # Keep deterministic ascending ID order regardless of manual file edits.
    tasks = [item for item in data if isinstance(item, dict)]
    tasks.sort(key=lambda task: int(task.get("id", 0)))
    return tasks


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    """Persist tasks as pretty JSON for predictable diffs and debugging."""
    try:
        DB_PATH.write_text(json.dumps(tasks, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise StorageError(f"Failed writing task DB: {DB_PATH}") from exc


def _next_task_id(tasks: list[dict[str, Any]]) -> int:
    """Return the next unique integer ID for newly created tasks."""
    max_id = 0
    for task in tasks:
        task_id = task.get("id")
        if isinstance(task_id, int) and task_id > max_id:
            max_id = task_id
    return max_id + 1


def add_task(text: str) -> dict[str, Any]:
    """Create a new task record and persist it."""
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("Task text cannot be empty.")

    tasks = load_tasks()
    new_task = {
        "id": _next_task_id(tasks),
        "text": cleaned_text,
        "completed": False,
    }
    tasks.append(new_task)
    save_tasks(tasks)
    return new_task


def list_tasks() -> list[dict[str, Any]]:
    """Return all stored tasks in deterministic ID order."""
    return load_tasks()


def complete_task(task_id: int) -> tuple[bool, str]:
    """Mark a task complete by ID. Returns (success, message)."""
    tasks = load_tasks()
    for task in tasks:
        if task.get("id") == task_id:
            if task.get("completed") is True:
                return False, f"Task {task_id} is already completed."
            task["completed"] = True
            save_tasks(tasks)
            return True, f"Task {task_id} marked as completed."
    return False, f"Task {task_id} was not found."


def delete_tasks(task_ids: list[int]) -> tuple[list[int], list[int]]:
    """Delete one or more task IDs. Returns (deleted_ids, missing_ids)."""
    if not task_ids:
        return [], []

    requested = list(dict.fromkeys(task_ids))
    tasks = load_tasks()
    existing_ids = {task.get("id") for task in tasks if isinstance(task.get("id"), int)}
    keep_ids = set(existing_ids) - set(requested)
    new_tasks = [task for task in tasks if task.get("id") in keep_ids]

    deleted_ids = sorted(existing_ids.intersection(requested))
    missing_ids = sorted(set(requested) - existing_ids)

    if deleted_ids:
        save_tasks(new_tasks)

    return deleted_ids, missing_ids
