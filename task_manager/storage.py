"""Task persistence and basic operations using a local JSON file."""

from __future__ import annotations

import json
from pathlib import Path

# Store tasks in tasks.json next to this module for simple cross-platform behavior.
TASKS_FILE = Path(__file__).with_name("tasks.json")


# Read tasks from disk, tolerating a missing or empty file.
def load_tasks() -> list[dict]:
    """Load tasks from tasks.json; return an empty list if file is missing or empty."""
    if not TASKS_FILE.exists():
        return []

    # Use utf-8-sig so files with a UTF-8 BOM still parse correctly on Windows.
    with TASKS_FILE.open("r", encoding="utf-8-sig") as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)


# Write all tasks to disk as formatted JSON.
def save_tasks(tasks: list[dict]) -> None:
    """Persist tasks to tasks.json with readable indentation."""
    with TASKS_FILE.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


# Compute the next task id based on existing records.
def next_id(tasks: list[dict]) -> int:
    """Get the next numeric task id."""
    if not tasks:
        return 1
    return max(task["id"] for task in tasks) + 1


# Create and persist a new incomplete task.
def add_task(title: str) -> None:
    """Add a new task with done=False and save it."""
    tasks = load_tasks()
    task = {"id": next_id(tasks), "title": title, "done": False}
    tasks.append(task)
    save_tasks(tasks)
    print(f"Added task #{task['id']}: {task['title']}")


# Display tasks in a simple numbered checklist format.
def list_tasks() -> None:
    """Print all tasks in a simple format."""
    tasks = load_tasks()
    if not tasks:
        print("No tasks yet.")
        return

    for task in tasks:
        status = "[x]" if task["done"] else "[ ]"
        print(f"{task['id']}. {status} {task['title']}")


# Mark a task as complete by its numeric id.
def mark_done(task_id: int) -> None:
    """Mark one task as done by id."""
    tasks = load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            save_tasks(tasks)
            print(f"Marked task #{task_id} as done.")
            return

    print(f"Task #{task_id} not found.")


# Delete one task by its numeric id.
def delete_task(task_id: int) -> None:
    """Delete one task by id."""
    tasks = load_tasks()
    for idx, task in enumerate(tasks):
        if task["id"] == task_id:
            deleted_title = task["title"]
            del tasks[idx]
            save_tasks(tasks)
            print(f"Deleted task #{task_id}: {deleted_title}")
            return

    print(f"Task #{task_id} not found.")


# Delete multiple tasks by their numeric ids in one deterministic operation.
def delete_tasks(task_ids: list[int]) -> None:
    """Delete all tasks whose ids are included in task_ids."""
    # Keep first-seen order while removing duplicates.
    unique_ids = list(dict.fromkeys(task_ids))
    if not unique_ids:
        print("No tasks deleted.")
        return

    tasks = load_tasks()
    id_set = set(unique_ids)
    deleted = [task for task in tasks if task["id"] in id_set]
    if not deleted:
        print("No tasks deleted.")
        return

    deleted_ids = [task["id"] for task in deleted]
    remaining = [task for task in tasks if task["id"] not in id_set]
    save_tasks(remaining)
    ids_text = ", ".join(str(task_id) for task_id in deleted_ids)
    print(f"Deleted {len(deleted_ids)} task(s): {ids_text}")
