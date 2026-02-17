"""Tool contract and execution layer for the task manager.

schema = interface contract, implementation = behavior.
The schema defines what the model is allowed to call.
The execution functions define what actually happens in deterministic code.
"""

from __future__ import annotations

from typing import Any

import storage

# Contract only: names, descriptions, and argument shape for model tool-calling.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a new task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Task text to create."}
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List all tasks in deterministic order.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task complete by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID from list output."}
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_tasks",
            "description": "Delete one or more tasks by IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 1,
                        "description": "One or more task IDs from list output.",
                    }
                },
                "required": ["task_ids"],
                "additionalProperties": False,
            },
        },
    },
]


def add_task(text: str) -> dict[str, Any]:
    """Execution behavior for add_task tool."""
    task = storage.add_task(text)
    return {"status": "ok", "task": task}


def list_tasks() -> dict[str, Any]:
    """Execution behavior for list_tasks tool."""
    tasks = storage.list_tasks()
    return {"status": "ok", "tasks": tasks}


def complete_task(task_id: int) -> dict[str, Any]:
    """Execution behavior for complete_task tool."""
    success, message = storage.complete_task(task_id)
    if not success:
        return {"status": "error", "message": message}
    return {"status": "ok", "message": message}


def delete_tasks(task_ids: list[int]) -> dict[str, Any]:
    """Execution behavior for delete_tasks tool with multi-ID support."""
    deleted_ids, missing_ids = storage.delete_tasks(task_ids)
    status = "ok" if deleted_ids else "error"
    return {
        "status": status,
        "deleted_ids": deleted_ids,
        "missing_ids": missing_ids,
        "message": (
            "Deleted requested tasks."
            if deleted_ids
            else "No requested task IDs were found."
        ),
    }


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a validated tool call to deterministic execution behavior."""
    try:
        if tool_name == "add_task":
            text = str(arguments.get("text", ""))
            return add_task(text)

        if tool_name == "list_tasks":
            return list_tasks()

        if tool_name == "complete_task":
            task_id = int(arguments.get("task_id"))
            return complete_task(task_id)

        if tool_name == "delete_tasks":
            raw_ids = arguments.get("task_ids", [])
            task_ids = [int(item) for item in raw_ids]
            return delete_tasks(task_ids)

        return {"status": "error", "message": f"Unknown tool: {tool_name}"}
    except (TypeError, ValueError) as exc:
        return {"status": "error", "message": f"Invalid arguments for {tool_name}: {exc}"}
    except storage.StorageError as exc:
        return {"status": "error", "message": str(exc)}
