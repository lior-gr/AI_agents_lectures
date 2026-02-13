"""Tool definitions and tool execution for the task manager agent.

Separation of concerns:
- `agent.py` decides *when* to call tools and manages conversation flow.
- `tools.py` defines *what* tools exist and executes requested tools.
- `storage.py` contains the actual task persistence/business operations.

Important principle:
- The agent never edits JSON directly.
- The agent only calls tool functions defined here.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

from storage import add_task as storage_add_task
from storage import list_tasks as storage_list_tasks
from storage import mark_done as storage_mark_done

# Tool schemas exposed to the model.
# These describe callable functions and argument shapes; execution is handled below.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Create a new task from plain text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Task text to add.",
                    }
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
            "description": "List all existing tasks.",
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
            "description": "Mark one task as complete by id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Numeric task id.",
                    }
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
]


def _capture_storage_output(func, *args) -> str:
    """Capture printed output from storage functions and return it as text.

    Storage functions already implement behavior and print user-facing results.
    The tool layer reuses that behavior without duplicating business logic.
    """
    # Create an in-memory text buffer to collect stdout output.
    buffer = io.StringIO()
    # Redirect all `print(...)` output inside this block into `buffer`.
    with redirect_stdout(buffer):
        # Execute the storage function with forwarded positional arguments.
        func(*args)
    # Return captured text; if nothing was printed, return a default success marker.
    return buffer.getvalue().strip() or "OK"


def _parse_tool_args(raw_arguments: str) -> dict:
    """Parse model-provided JSON arguments into a dictionary."""
    if not raw_arguments:
        return {}
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON arguments: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Tool arguments must decode to a JSON object.")
    return parsed


def run_tool_call(tool_name: str, raw_arguments: str) -> str:
    """Dispatch one tool call by name and return tool output text.

    This is the only entry point used by the agent for tool execution.
    """
    args = _parse_tool_args(raw_arguments)

    if tool_name == "add_task":
        text = args.get("text")
        if not isinstance(text, str) or not text.strip():
            return "Error: 'text' is required and must be a non-empty string."
        return _capture_storage_output(storage_add_task, text)

    if tool_name == "list_tasks":
        if args:
            return "Error: 'list_tasks' does not accept arguments."
        return _capture_storage_output(storage_list_tasks)

    if tool_name == "complete_task":
        task_id = args.get("task_id")
        if not isinstance(task_id, int):
            return "Error: 'task_id' is required and must be an integer."
        return _capture_storage_output(storage_mark_done, task_id)

    return f"Error: unknown tool '{tool_name}'."
