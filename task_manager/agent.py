"""Minimal bounded agent loop for goal-driven task management.

This module owns control flow: loop steps, stop conditions, model calls, and tool orchestration.
Execution behavior stays in MCP/tool layers, while skill routing only changes prompt content.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from mcp_client import execute_tool_via_mcp
from skill_router import route_skills_with_model
from skills_loader import load_skill_names, load_skills
from tools import TOOL_SCHEMAS

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOGGER = logging.getLogger("task_agent")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

BASE_SYSTEM_POLICY = (
    "You are a careful task assistant. "
    "Use available tools when actions or data access are required. "
    "Be concise and deterministic."
)
SKILLS_DIR = Path("skills")
SKILL_SEPARATOR = "\n\n---\n\n"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ROUTER_MODEL = os.getenv("OPENAI_ROUTER_MODEL", DEFAULT_MODEL)
MAX_TOKEN_CAP = 800
ROUTER_TOKEN_CAP = 120


def _token_parameter_kwargs(model: str, max_token_cap: int) -> dict[str, int]:
    """Use model-compatible token limit parameter names."""
    bounded_cap = min(max_token_cap, MAX_TOKEN_CAP)
    model_name = model.strip().lower()
    if model_name.startswith(("o1", "o3", "o4", "gpt-5")):
        return {"max_completion_tokens": bounded_cap}
    return {"max_tokens": bounded_cap}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_text_file(path: Path) -> str:
    """Read UTF-8 text file; missing files resolve to empty skill text."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _emit_event(
    progress_callback: Callable[[dict[str, Any]], None] | None,
    event_type: str,
    name: str,
    details: str,
    *,
    step: int | None = None,
    max_steps: int | None = None,
) -> None:
    """Emit a normalized progress event for logs and optional UI instrumentation."""
    event: dict[str, Any] = {
        "time": _now_iso(),
        "type": event_type,
        "name": name,
        "details": details,
    }
    if step is not None:
        event["step"] = step
    if max_steps is not None:
        event["max_steps"] = max_steps

    step_fragment = f" step={step}/{max_steps}" if step is not None and max_steps is not None else ""
    LOGGER.info("%s%s %s", name, step_fragment, details)

    if progress_callback is not None:
        progress_callback(event)


def _assistant_message_to_dict(message: Any) -> dict[str, Any]:
    """Translate SDK message object to Chat Completions message dict format."""
    output: dict[str, Any] = {
        "role": "assistant",
        "content": message.content or "",
    }

    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        serialized_calls: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            serialized_calls.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            )
        output["tool_calls"] = serialized_calls

    return output


def _call_chat_completions(
    messages: Sequence[dict[str, Any]],
    *,
    model: str,
    tools: list[dict[str, Any]] | None,
    temperature: float,
    token_cap: int,
) -> Any:
    """Shared OpenAI Chat Completions wrapper with model-compatible token args."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    # Local import keeps deterministic CLI commands runnable without openai installed.
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": list(messages),
        "temperature": temperature,
    }
    if tools is not None:
        kwargs["tools"] = tools
    kwargs.update(_token_parameter_kwargs(model, token_cap))

    try:
        return client.chat.completions.create(**kwargs)
    except Exception as exc:
        # Compatibility fallback for models that use max_tokens instead of max_completion_tokens.
        if "max_completion_tokens" in kwargs:
            fallback_kwargs = dict(kwargs)
            value = fallback_kwargs.pop("max_completion_tokens")
            fallback_kwargs["max_tokens"] = value
            return client.chat.completions.create(**fallback_kwargs)
        raise exc


def _call_main_model(messages: list[dict[str, Any]], model: str) -> Any:
    """Main generation path (unchanged by skill routing changes)."""
    return _call_chat_completions(
        messages,
        model=model,
        tools=TOOL_SCHEMAS,
        temperature=0,
        token_cap=MAX_TOKEN_CAP,
    )


def call_router_model(messages: Sequence[dict[str, str]]) -> str:
    """Low-cost router classifier call that returns raw text only."""
    response = _call_chat_completions(
        list(messages),
        model=ROUTER_MODEL,
        tools=None,
        temperature=0,
        token_cap=ROUTER_TOKEN_CAP,
    )
    content = response.choices[0].message.content or ""
    return content.strip()


def _build_system_prompt(goal: str, progress_callback: Callable[[dict[str, Any]], None] | None) -> str:
    """Assemble system prompt with always_on and optional routed skills.

    Routing affects reasoning input only. Loop control and MCP tool execution are unchanged.
    """
    routing_mode = os.getenv("SKILL_ROUTING_MODE", "bounded").strip().lower()

    if routing_mode == "deterministic":
        skill_names = load_skill_names(goal)
        _emit_event(
            progress_callback,
            "skill_route",
            "skill_route",
            f"Deterministic routing selected skills={skill_names}",
        )
        for name in skill_names:
            _emit_event(
                progress_callback,
                "skill",
                "skill_used",
                f"Skill selected: {name}",
            )

        skills_text = load_skills(goal, skills_dir=str(SKILLS_DIR))
        if not skills_text:
            return BASE_SYSTEM_POLICY
        return f"{BASE_SYSTEM_POLICY}\n\nSkill guidance:\n{skills_text}"

    always_on_text = _read_text_file(SKILLS_DIR / "always_on.md")
    if always_on_text:
        _emit_event(
            progress_callback,
            "skill",
            "skill_used",
            "Skill selected: always_on",
        )

    ok, selected, reason = route_skills_with_model(goal, call_router_model, max_attempts=3)
    _emit_event(
        progress_callback,
        "skill_route",
        "skill_route",
        f"Router ok={ok} selected={selected} reason={reason}",
    )

    optional_blocks: list[str] = []
    if ok:
        for name in selected:
            text = _read_text_file(SKILLS_DIR / f"{name}.md")
            if text:
                optional_blocks.append(text)
                _emit_event(
                    progress_callback,
                    "skill",
                    "skill_used",
                    f"Skill selected: {name}",
                )
    else:
        _emit_event(
            progress_callback,
            "validation",
            "validation",
            "Skill routing failed; using always_on only.",
        )

    blocks: list[str] = []
    if always_on_text:
        blocks.append(always_on_text)
    blocks.extend(optional_blocks)

    if not blocks:
        return BASE_SYSTEM_POLICY

    return f"{BASE_SYSTEM_POLICY}\n\nSkill guidance:\n{SKILL_SEPARATOR.join(blocks)}"


def run_agent(
    goal: str,
    *,
    max_steps: int = 5,
    model: str = DEFAULT_MODEL,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> str:
    """Run a bounded agent loop for one goal and return final assistant text."""
    goal_text = goal.strip()
    if not goal_text:
        raise ValueError("Goal cannot be empty.")

    system_prompt = _build_system_prompt(goal_text, progress_callback)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": goal_text},
    ]

    _emit_event(
        progress_callback,
        "lifecycle",
        "agent_start",
        f"Starting run for goal: {goal_text}",
    )

    for step in range(1, max_steps + 1):
        _emit_event(
            progress_callback,
            "step",
            "step_start",
            "Agent step started.",
            step=step,
            max_steps=max_steps,
        )

        try:
            response = _call_main_model(messages, model)
            assistant_message = response.choices[0].message
        except Exception as exc:
            _emit_event(
                progress_callback,
                "error",
                "error",
                f"Model call failed: {exc}",
                step=step,
                max_steps=max_steps,
            )
            raise

        messages.append(_assistant_message_to_dict(assistant_message))

        tool_calls = getattr(assistant_message, "tool_calls", None) or []
        if not tool_calls:
            final_text = (assistant_message.content or "").strip()
            if not final_text:
                final_text = "Completed without a textual response."
            _emit_event(
                progress_callback,
                "stop",
                "stop",
                "Stop reason=assistant_message_without_tool_calls",
                step=step,
                max_steps=max_steps,
            )
            return final_text

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments or "{}"
            try:
                tool_arguments = json.loads(raw_arguments)
                if not isinstance(tool_arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object.")
            except Exception as exc:
                tool_arguments = {}
                _emit_event(
                    progress_callback,
                    "validation",
                    "validation",
                    f"Invalid tool arguments for {tool_name}: {exc}",
                    step=step,
                    max_steps=max_steps,
                )

            _emit_event(
                progress_callback,
                "tool",
                "tool_called",
                f"Calling tool={tool_name} with args={tool_arguments}",
                step=step,
                max_steps=max_steps,
            )
            tool_result = execute_tool_via_mcp(tool_name, tool_arguments)
            _emit_event(
                progress_callback,
                "tool",
                "tool_result",
                f"Result from tool={tool_name}: {tool_result}",
                step=step,
                max_steps=max_steps,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=True),
                }
            )

    _emit_event(
        progress_callback,
        "stop",
        "stop",
        "Stop reason=max_steps_reached",
        step=max_steps,
        max_steps=max_steps,
    )
    return "Stopped after reaching max_steps without final response."
