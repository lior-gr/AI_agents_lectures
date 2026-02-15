"""Minimal synchronous MCP-style server over stdin/stdout.

This process reads one JSON request per input line from stdin and writes one JSON
response per line to stdout.

Request format:
{
  "tool": "add_task" | "list_tasks" | "complete_task" | "delete_task" | "delete_tasks",
  "arguments": { ... }
}

Response format:
{
  "status": "ok",
  "result": "..."
}

On errors, this server returns:
{
  "status": "error",
  "error": "..."
}
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout

from storage import add_task, delete_task, delete_tasks, list_tasks, mark_done


def _capture_storage_output(func, *args) -> str:
    """Run a storage function and capture any printed output as a result string."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        func(*args)
    return buffer.getvalue().strip() or "OK"


def _dispatch_tool(tool: str, arguments: dict) -> str:
    """Dispatch tool requests to storage.py functions.

    Tool dispatch is centralized here to keep behavior deterministic and explicit.
    """
    if tool == "add_task":
        text = arguments.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("'add_task' requires a non-empty string argument: text")
        return _capture_storage_output(add_task, text)

    if tool == "list_tasks":
        if arguments:
            raise ValueError("'list_tasks' does not accept arguments")
        return _capture_storage_output(list_tasks)

    if tool == "complete_task":
        task_id = arguments.get("task_id")
        if not isinstance(task_id, int):
            raise ValueError("'complete_task' requires integer argument: task_id")
        return _capture_storage_output(mark_done, task_id)

    if tool == "delete_task":
        task_id = arguments.get("task_id")
        if not isinstance(task_id, int):
            raise ValueError("'delete_task' requires integer argument: task_id")
        return _capture_storage_output(delete_task, task_id)

    if tool == "delete_tasks":
        task_ids = arguments.get("task_ids")
        if not isinstance(task_ids, list) or not task_ids:
            raise ValueError("'delete_tasks' requires non-empty array argument: task_ids")
        if not all(isinstance(task_id, int) for task_id in task_ids):
            raise ValueError("'delete_tasks' requires all task_ids to be integers")
        return _capture_storage_output(delete_tasks, task_ids)

    raise ValueError(f"Unsupported tool: {tool}")


def handle_request(raw_line: str) -> dict:
    """Parse one request line and return a deterministic response dictionary.

    Keeping this logic separate from I/O makes behavior easier to test.
    """
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        return {"status": "error", "error": f"Invalid JSON: {exc.msg}"}

    if not isinstance(payload, dict):
        return {"status": "error", "error": "Request must be a JSON object"}

    tool = payload.get("tool")
    arguments = payload.get("arguments", {})

    if not isinstance(tool, str) or not tool:
        return {"status": "error", "error": "Missing or invalid 'tool' field"}

    if not isinstance(arguments, dict):
        return {"status": "error", "error": "'arguments' must be a JSON object"}

    try:
        result = _dispatch_tool(tool, arguments)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    return {"status": "ok", "result": result}


def main() -> None:
    """Run the server loop.

    Why decoupled from the agent:
    - The agent decides *when* to call tools.
    - This server defines *how* tools are executed over a transport protocol.
    - storage.py owns the task business logic and JSON persistence.
    This separation keeps each layer simpler and independently reusable.
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            # Ignore empty lines to keep line-oriented protocol simple.
            continue

        response = handle_request(line)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
