"""Minimal agent loop with OpenAI Chat Completions and stubbed tool calls.

Authentication note:
- The OpenAI SDK reads the API key from the `OPENAI_API_KEY` environment variable
  when `OpenAI()` is created without an explicit `api_key` argument.
"""

from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Callable

from openai import OpenAI

from mcp_client import MCPClient
from tools import TOOL_SCHEMAS

# Basic logger used to show progress for each step in the loop.
LOGGER = logging.getLogger(__name__)

# Keep the model configurable via environment variable.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Hard step limit requested for this minimal agent.
DEFAULT_MAX_STEPS = 5

# Per-call completion token cap requested in the prompt.
MAX_COMPLETION_TOKENS_PER_CALL = 800

# Use a low temperature for more deterministic outputs.
TEMPERATURE = 0.2

# Keep agent behavior intentionally simple: execute tools to satisfy the goal, then stop.
SYSTEM_PROMPT = (
    "You are a minimal task agent. "
    "Use tools to do task operations. "
    "Do not plan; do not explain long strategies. "
    "For requests like 'add X and then show tasks', call add_task first, then list_tasks. "
    "Do not edit JSON directly. "
    "Once the goal is satisfied, return a short final answer."
)

# Skill file location used only for prompt construction.
SKILL_FILE = Path(__file__).resolve().parent / "skills" / "task_planning_skill.md"


def load_task_planning_skill() -> str:
    """Load task planning skill text from disk.

    Separation note:
    - This function only prepares prompt content.
    - It does not alter loop flow, tool dispatch, or execution logic.
    """
    try:
        return SKILL_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to load skill file: {SKILL_FILE}") from exc


def build_system_prompt() -> str:
    """Build the final system prompt by injecting skill guidance text.

    Separation note:
    - Prompt construction is isolated here.
    - Agent control logic (steps/stops/tokens/tools) remains unchanged.
    """
    skill_text = load_task_planning_skill()
    return f"{SYSTEM_PROMPT}\n\n[Task Planning Skill]\n{skill_text}"


def _is_unsupported_token_param_error(exc: Exception, param_name: str) -> bool:
    """Return True when API error indicates a specific token parameter is unsupported."""
    message = str(exc)
    return "unsupported_parameter" in message and f"'{param_name}'" in message


def _format_openai_error_message(exc: Exception, model: str) -> str:
    """Convert low-level API exceptions into a human-readable message."""
    message = str(exc)
    return (
        f"OpenAI request failed for model '{model}'. "
        f"Details: {message}. "
        "Please verify model access and API parameter compatibility."
    )


def _emit_event(
    on_event: Callable[[dict], None] | None,
    event_type: str,
    name: str = "",
    details: str = "",
    step: int | None = None,
) -> None:
    """Emit one instrumentation event to observers.

    This function is observability-only. Any callback failure is swallowed so
    agent control flow is never affected by UI/telemetry logic.
    """
    if on_event is None:
        return

    payload = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "type": event_type,
        "name": name,
        "details": details,
    }
    if step is not None:
        payload["step"] = step

    try:
        on_event(payload)
    except Exception as exc:  # pragma: no cover - defensive guard
        LOGGER.debug("Ignoring on_event callback failure: %s", exc)


def _create_chat_completion_with_token_compat(client: OpenAI, model: str, messages: list[dict]):
    """Create chat completion with compatibility fallback for token-limit parameter names.

    Some models accept `max_completion_tokens`; others accept `max_tokens`.
    This wrapper tries both so switching models does not crash the app.
    """
    token_param_candidates = ["max_completion_tokens", "max_tokens"]

    for idx, token_param in enumerate(token_param_candidates):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                # Tool schemas are defined in tools.py so the agent does not own task logic.
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=TEMPERATURE,
                # Token guardrail remains capped at 800 completion tokens per call.
                **{token_param: MAX_COMPLETION_TOKENS_PER_CALL},
            )
        except Exception as exc:
            is_last_attempt = idx == len(token_param_candidates) - 1
            if _is_unsupported_token_param_error(exc, token_param) and not is_last_attempt:
                LOGGER.warning(
                    "Model '%s' rejected token parameter '%s'. Retrying with '%s'.",
                    model,
                    token_param,
                    token_param_candidates[idx + 1],
                )
                continue
            raise RuntimeError(_format_openai_error_message(exc, model)) from exc

    # Defensive fallback; logically unreachable.
    raise RuntimeError(f"OpenAI request failed for model '{model}'.")


def run_agent(
    goal: str,
    *,
    model: str | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    on_event: Callable[[dict], None] | None = None,
) -> str:
    """Run a minimal agent loop for the given user goal."""
    if not goal.strip():
        raise ValueError("goal must be a non-empty string")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # API key source: this client uses OPENAI_API_KEY from environment by default.
    client = OpenAI()
    chosen_model = model or DEFAULT_MODEL
    mcp_client = MCPClient()
    mcp_client.start()
    system_prompt = build_system_prompt()
    _emit_event(on_event, "agent_start", "run_agent", f"model={chosen_model}")
    _emit_event(
        on_event,
        "skill_used",
        "task_planning_skill",
        "Injected into system prompt.",
    )

    # Message history list: this is the full conversation state sent on every model call.
    messages: list[dict] = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {"role": "user", "content": goal},
    ]

    # AGENT LOOP:
    # This loop is unchanged: same step control, history updates, and stopping conditions.
    # Only the tool execution transport changed (direct call -> MCP client request).
    try:
        for step in range(1, max_steps + 1):
            LOGGER.info("Step %s/%s: requesting model response", step, max_steps)
            _emit_event(on_event, "step_start", f"step_{step}", f"{step}/{max_steps}", step=step)

            try:
                response = _create_chat_completion_with_token_compat(
                    client=client,
                    model=chosen_model,
                    messages=messages,
                )
            except RuntimeError as exc:
                # Human-readable failure path: return clean message instead of raw traceback.
                LOGGER.error("%s", exc)
                _emit_event(on_event, "error", "openai_request", str(exc), step=step)
                return str(exc)

            assistant_message = response.choices[0].message
            tool_calls = assistant_message.tool_calls or []
            assistant_text = assistant_message.content or ""

            # Keep the assistant message in history exactly as returned so the next step has full context.
            messages.append(assistant_message.model_dump(exclude_none=True))

            # TOOL CALL PROCESSING:
            # If the assistant asks for tools, we execute stub handlers and append tool outputs.
            if tool_calls:
                LOGGER.info("Step %s: processing %s tool call(s)", step, len(tool_calls))
                for call in tool_calls:
                    tool_name = call.function.name
                    tool_args = call.function.arguments or ""
                    LOGGER.info("Tool call id=%s name=%s", call.id, tool_name)
                    _emit_event(on_event, "tool_called", tool_name, tool_args, step=step)

                    # Execution layer only: send tool calls through MCP transport.
                    # The agent remains unchanged as an orchestrator (loop/history/stop logic).
                    try:
                        # Argument parsing/normalization is handled inside MCPClient,
                        # so agent code stays focused on loop orchestration only.
                        tool_response = mcp_client.request(tool_name, tool_args)
                        if tool_response.get("status") == "ok":
                            tool_result = str(tool_response.get("result", "OK"))
                            _emit_event(on_event, "tool_result", tool_name, tool_result, step=step)
                        else:
                            tool_result = str(tool_response.get("error", "Unknown tool error"))
                            _emit_event(on_event, "tool_result", tool_name, tool_result, step=step)
                    except Exception as exc:  # pragma: no cover - defensive guard for runtime tool errors
                        tool_result = f"Error executing tool '{tool_name}': {exc}"
                        _emit_event(on_event, "tool_result", tool_name, tool_result, step=step)

                    messages.append(
                        {
                            # This marks the message as tool output.
                            "role": "tool",
                            # Must match the tool call id generated by the model.
                            "tool_call_id": call.id,
                            # Tool name for readability/debugging.
                            "name": tool_name,
                            # The actual tool result sent back to the model.
                            "content": tool_result,
                        }
                    )
                continue

            # STOPPING CONDITIONS:
            # Condition 1: assistant returned a normal answer with no tool calls, so we can stop early.
            if assistant_text.strip():
                LOGGER.info("Stopping at step %s: final answer received", step)
                _emit_event(on_event, "stop", "final_answer", "Final answer produced.", step=step)
                return assistant_text

            # Condition 2: no tool calls and empty output; stop to avoid useless iterations.
            LOGGER.info("Stopping at step %s: empty response with no tool calls", step)
            _emit_event(on_event, "stop", "empty_response", "No tool calls and empty assistant output.", step=step)
            return "No final answer produced."

        # Condition 3: hard cap reached (max_steps=5 by default).
        LOGGER.info("Stopping: reached max_steps=%s", max_steps)
        _emit_event(on_event, "stop", "max_steps", f"Reached max_steps={max_steps}.", step=max_steps)
        return f"Stopped after reaching max_steps={max_steps}."
    finally:
        mcp_client.close()
