"""Minimal MCP client that talks to mcp_server.py via subprocess stdio.

The client owns process lifecycle and message I/O only.
It does not decide loop behavior or planning strategy.
"""

from __future__ import annotations

import atexit
import json
import subprocess
import sys
from pathlib import Path
from threading import Lock
from typing import Any

SERVER_SCRIPT = Path(__file__).with_name("mcp_server.py")


class MCPClient:
    """Manage one local MCP server subprocess and deterministic request/response calls."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen[str] | None = None
        self._lock = Lock()

    def _is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _start_if_needed(self) -> None:
        if self._is_running():
            return

        self._proc = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    def call_tool(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send one tool request and return one parsed JSON response."""
        with self._lock:
            self._start_if_needed()
            assert self._proc is not None
            assert self._proc.stdin is not None
            assert self._proc.stdout is not None

            request = {"tool": tool, "arguments": arguments}
            self._proc.stdin.write(json.dumps(request, ensure_ascii=True) + "\n")
            self._proc.stdin.flush()

            raw_response = self._proc.stdout.readline()
            if not raw_response:
                raise RuntimeError("MCP server returned no response.")

            try:
                parsed = json.loads(raw_response)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Malformed MCP response: {raw_response!r}") from exc

            if not isinstance(parsed, dict):
                raise RuntimeError("MCP response must be a JSON object.")
            return parsed

    def close(self) -> None:
        """Terminate the server process cleanly."""
        with self._lock:
            if self._proc is None:
                return
            if self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None


_CLIENT = MCPClient()
atexit.register(_CLIENT.close)


def execute_tool_via_mcp(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Simple functional API for agent integration."""
    return _CLIENT.call_tool(tool_name, arguments)


def shutdown_mcp_client() -> None:
    """Allow explicit cleanup in tests or shutdown paths."""
    _CLIENT.close()
