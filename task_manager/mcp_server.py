"""Minimal deterministic MCP server over stdin/stdout.

This process is execution-only. It parses JSON tool requests, dispatches to storage,
and writes deterministic JSON responses. It has no model loop or planning behavior.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import storage


def _ok(result: Any) -> dict[str, Any]:
    return {"status": "ok", "result": result}


def _error(message: str) -> dict[str, Any]:
    return {"status": "error", "error": message}


def _dispatch(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one tool call to deterministic storage-backed behavior."""
    try:
        if tool == "add_task":
            text = str(arguments.get("text", ""))
            task = storage.add_task(text)
            return _ok({"task": task})

        if tool == "list_tasks":
            return _ok({"tasks": storage.list_tasks()})

        if tool == "complete_task":
            task_id = int(arguments.get("task_id"))
            success, message = storage.complete_task(task_id)
            if not success:
                return _error(message)
            return _ok({"message": message})

        if tool == "delete_tasks":
            raw_ids = arguments.get("task_ids", [])
            task_ids = [int(item) for item in raw_ids]
            deleted_ids, missing_ids = storage.delete_tasks(task_ids)
            if not deleted_ids:
                return _error(f"No requested IDs deleted. Missing IDs: {missing_ids}")
            return _ok({"deleted_ids": deleted_ids, "missing_ids": missing_ids})

        return _error(f"Unknown tool: {tool}")
    except (ValueError, TypeError) as exc:
        return _error(f"Invalid arguments for {tool}: {exc}")
    except storage.StorageError as exc:
        return _error(str(exc))


def handle_request(raw_line: str) -> dict[str, Any]:
    """Parse one request line and return one deterministic response object."""
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError:
        return _error("Request is not valid JSON.")

    if not isinstance(payload, dict):
        return _error("Request must be a JSON object.")

    tool = payload.get("tool")
    arguments = payload.get("arguments", {})

    if not isinstance(tool, str) or not tool:
        return _error("Request field 'tool' must be a non-empty string.")
    if not isinstance(arguments, dict):
        return _error("Request field 'arguments' must be an object.")

    return _dispatch(tool, arguments)


def serve_forever() -> None:
    """Read stdin line-by-line and write one JSON response per request line."""
    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        response = handle_request(raw)
        sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    serve_forever()
