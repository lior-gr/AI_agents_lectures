"""Minimal MCP client that talks to mcp_server.py over stdin/stdout.

Why the subprocess boundary matters:
- The client and server run in separate processes, so each side can evolve independently.
- The protocol between them is explicit JSON messages, not shared in-memory calls.
- Crashes or restarts can be isolated to one side, which is closer to real distributed systems.

How this simulates real MCP architecture:
- Real MCP deployments often have a host/client process and a separate tool server process.
- Even though both files are local here, we still use a transport boundary (stdin/stdout JSON).
- This keeps integration behavior realistic while staying simple and synchronous.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


class MCPClient:
    """Synchronous client for line-delimited JSON MCP requests/responses."""

    def __init__(self, server_script: str = "mcp_server.py") -> None:
        # Resolve server path relative to this file for predictable local behavior.
        self._server_path = Path(__file__).with_name(server_script)
        self._proc: subprocess.Popen[str] | None = None

    def start(self) -> None:
        """Start the MCP server subprocess if not already running."""
        if self._proc is not None and self._proc.poll() is None:
            return

        if not self._server_path.exists():
            raise RuntimeError(f"Server script not found: {self._server_path}")

        try:
            self._proc = subprocess.Popen(
                [sys.executable, str(self._server_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise RuntimeError(f"Failed to start MCP server: {exc}") from exc

    def request(self, tool: str, arguments: dict | None = None) -> dict:
        """Send one tool request and return one response dictionary.

        Error handling strategy:
        - On protocol/process errors, return `{"status": "error", "error": "..."}`
          instead of throwing, so callers can handle failures consistently.
        """
        if not isinstance(tool, str) or not tool:
            return {"status": "error", "error": "'tool' must be a non-empty string"}

        if arguments is None:
            arguments = {}

        if not isinstance(arguments, dict):
            return {"status": "error", "error": "'arguments' must be a dictionary"}

        if self._proc is None or self._proc.poll() is not None:
            return {"status": "error", "error": "Server is not running. Call start() first."}

        request_payload = {"tool": tool, "arguments": arguments}
        try:
            request_line = json.dumps(request_payload)
        except TypeError as exc:
            return {"status": "error", "error": f"Request is not JSON-serializable: {exc}"}

        assert self._proc.stdin is not None
        assert self._proc.stdout is not None

        try:
            self._proc.stdin.write(request_line + "\n")
            self._proc.stdin.flush()
        except OSError as exc:
            return {"status": "error", "error": f"Failed to write to server stdin: {exc}"}

        response_line = self._proc.stdout.readline()
        if not response_line:
            stderr_text = ""
            if self._proc.stderr is not None:
                stderr_text = self._proc.stderr.read().strip()
            detail = stderr_text or "No response from server."
            return {"status": "error", "error": f"Server disconnected: {detail}"}

        try:
            response_payload = json.loads(response_line)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "error": "Server returned invalid JSON response",
                "raw_response": response_line.strip(),
            }

        if not isinstance(response_payload, dict):
            return {"status": "error", "error": "Server response must be a JSON object"}

        if "status" not in response_payload:
            return {
                "status": "error",
                "error": "Server response missing required field: status",
                "raw_response": response_payload,
            }

        return response_payload

    def close(self) -> None:
        """Stop the server subprocess gracefully."""
        if self._proc is None:
            return

        try:
            if self._proc.stdin is not None:
                self._proc.stdin.close()
        except OSError:
            pass

        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=2)

        self._proc = None

    def __enter__(self) -> MCPClient:
        """Context-manager entry: start server automatically."""
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Context-manager exit: always stop server."""
        self.close()


if __name__ == "__main__":
    # Minimal demonstration call for manual local testing.
    with MCPClient() as client:
        print(client.request("list_tasks", {}))
