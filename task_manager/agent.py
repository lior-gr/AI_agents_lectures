"""Minimal agent loop with OpenAI Chat Completions and stubbed tool calls.

Authentication note:
- The OpenAI SDK reads the API key from the `OPENAI_API_KEY` environment variable
  when `OpenAI()` is created without an explicit `api_key` argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import partial
import logging
import os
from pathlib import Path
import re
from typing import Callable

from openai import OpenAI

from mcp_client import MCPClient
from skill_router import ALLOWED_SKILLS, route_goal_intent_with_model, route_skills_with_model
from tools import TOOL_SCHEMAS

# Basic logger used to show progress for each step in the loop.
LOGGER = logging.getLogger(__name__)

# Keep the model configurable via environment variable.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Hard step limit requested for this minimal agent.
DEFAULT_MAX_STEPS = 15

# Per-call completion token cap requested in the prompt.
MAX_COMPLETION_TOKENS_PER_CALL = 800

# Use a low temperature for more deterministic outputs.
TEMPERATURE = 0.2

# Router path uses an even lower temperature and smaller token cap to stay cheap.
ROUTER_TEMPERATURE = 0.0
ROUTER_MAX_COMPLETION_TOKENS = 120
ROUTER_MAX_ATTEMPTS = 3

# Keep agent behavior intentionally simple: execute tools to satisfy the goal, then stop.
SYSTEM_PROMPT = (
    "You are a minimal task agent. "
    "Use tools to do task operations. "
    "Do not plan; do not explain long strategies. "
    "For requests like 'add X and then show tasks', call add_task first, then list_tasks. "
    "For delete-by-criteria requests, call list_tasks, then delete matched ids (prefer delete_tasks for multiple ids), then call list_tasks to verify. "
    "Do not edit JSON directly. "
    "Once the goal is satisfied, return a short final answer."
)

# Skill files are prompt-only guidance and live under this directory.
SKILLS_DIR = Path(__file__).resolve().parent / "skills"
SKILL_FILES: dict[str, Path] = {
    "always_on": SKILLS_DIR / "always_on.md",
    # Keep task_planning mapped to the richer planning guidance file.
    "task_planning": SKILLS_DIR / "task_planning.md",
    "task_deletion": SKILLS_DIR / "task_deletion.md",
    "status_reporting": SKILLS_DIR / "status_reporting.md",
    "output_format": SKILLS_DIR / "output_format.md",
}


def _read_skill_file(path: Path) -> str:
    """Read one skill file from disk and return normalized text."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to load skill file: {path}") from exc


def _create_router_completion_with_token_compat(client: OpenAI, model: str, messages: list[dict]):
    """Create router completion with token-parameter compatibility fallback."""
    token_param_candidates = ["max_completion_tokens", "max_tokens"]

    for idx, token_param in enumerate(token_param_candidates):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=ROUTER_TEMPERATURE,
                **{token_param: ROUTER_MAX_COMPLETION_TOKENS},
            )
        except Exception as exc:
            is_last_attempt = idx == len(token_param_candidates) - 1
            if _is_unsupported_token_param_error(exc, token_param) and not is_last_attempt:
                LOGGER.warning(
                    "Router model '%s' rejected token parameter '%s'. Retrying with '%s'.",
                    model,
                    token_param,
                    token_param_candidates[idx + 1],
                )
                continue
            raise RuntimeError(_format_openai_error_message(exc, model)) from exc

    raise RuntimeError(f"OpenAI request failed for router model '{model}'.")


def call_router_model(
    prompt_or_messages: str | list[dict],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> str:
    """Return raw router text output only.

    Router calls must stay cheap because routing is control-plane work, not
    final user-facing reasoning work.
    """
    active_client = client or OpenAI()
    active_model = model or DEFAULT_MODEL
    if isinstance(prompt_or_messages, str):
        messages = [
            {"role": "system", "content": "You are a strict JSON router. Return JSON only."},
            {"role": "user", "content": prompt_or_messages},
        ]
    else:
        messages = prompt_or_messages
    response = _create_router_completion_with_token_compat(active_client, active_model, messages)
    return response.choices[0].message.content or ""


def _route_skill_names(goal: str, *, client: OpenAI, model: str) -> tuple[list[str], str]:
    """Route skills with bounded model retries and deterministic validation.

    Routing affects reasoning style only; it does not change loop/tool behavior.
    """
    # Bind client/model once so route_skills_with_model can call a single-arg router function.
    routed_call = partial(call_router_model, client=client, model=model)
    ok, routed_skills, reason = route_skills_with_model(goal, routed_call, max_attempts=3)

    # Always load baseline guardrails even if router fails.
    always_on_only = ["always_on"]
    if not ok:
        return always_on_only, f"router_fail_fallback: {reason}"

    # Router output controls optional reasoning skills only.
    optional_skills = [skill for skill in routed_skills if skill != "always_on"]
    allowed_order = list(ALLOWED_SKILLS.keys())
    ordered_optional = [skill for skill in allowed_order if skill in optional_skills]
    return always_on_only + ordered_optional, reason


def load_skills(goal: str, *, client: OpenAI, model: str) -> tuple[str, list[str], str]:
    """Load routed skills and return concatenated text plus route metadata."""
    selected_skills, route_reason = _route_skill_names(goal, client=client, model=model)
    sections: list[str] = []
    for skill_name in selected_skills:
        skill_path = SKILL_FILES.get(skill_name)
        if skill_path is None:
            raise RuntimeError(f"Missing skill file mapping for '{skill_name}'.")
        skill_text = _read_skill_file(skill_path)
        sections.append(f"[Skill: {skill_name}]\n{skill_text}")
    return "\n\n---\n\n".join(sections), selected_skills, route_reason


def build_system_prompt(goal: str, *, client: OpenAI, model: str) -> tuple[str, list[str], str]:
    """Build final system prompt by injecting routed skill text.

    Separation note:
    - This function only constructs prompt text.
    - Skill routing changes reasoning guidance only.
    - Agent loop, stop conditions, token handling, and tool execution stay unchanged.
    """
    skill_text, selected_skills, route_reason = load_skills(goal, client=client, model=model)
    return f"{SYSTEM_PROMPT}\n\n[Loaded Skills]\n{skill_text}", selected_skills, route_reason


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


@dataclass
class GoalValidationState:
    """Track deterministic evidence used by goal-completion validator."""

    wants_add: bool
    wants_delete: bool
    initial_count: int | None = None
    latest_count: int | None = None
    add_success_count: int = 0
    delete_success_count: int = 0
    saw_mutation: bool = False
    saw_post_mutation_list: bool = False


_TASK_LINE_PATTERN = re.compile(r"^\s*\d+\.\s+\[[ xX]\]\s+", re.MULTILINE)
_ADD_SUCCESS_PATTERN = re.compile(r"Added task #\d+:")
_DELETE_SUCCESS_PATTERN = re.compile(r"Deleted task #\d+:")
_DELETE_BULK_SUCCESS_PATTERN = re.compile(r"Deleted\s+(\d+)\s+task\(s\):")


def _detect_goal_intents_keyword(goal: str) -> tuple[bool, bool]:
    """Keyword-only fallback for add/delete goal intent detection."""
    text = goal.lower()
    add_markers = (" add ", " create ", " new task", " insert ")
    delete_markers = (" delete ", " remove ", " purge ", " clean up ")
    wants_add = any(marker in f" {text} " for marker in add_markers)
    wants_delete = any(marker in f" {text} " for marker in delete_markers)
    return wants_add, wants_delete


def _detect_goal_intents_hybrid(goal: str, *, client: OpenAI, model: str) -> tuple[bool, bool, str]:
    """Detect add/delete intent with model router first and keyword fallback second.

    Hybrid policy:
    - Model router handles paraphrases and richer language.
    - Deterministic fallback ensures behavior if router output is invalid.
    """
    routed_call = partial(call_router_model, client=client, model=model)
    ok, intent, reason = route_goal_intent_with_model(
        goal=goal,
        call_model_fn=routed_call,
        max_attempts=ROUTER_MAX_ATTEMPTS,
    )
    if ok:
        return bool(intent["wants_add"]), bool(intent["wants_delete"]), f"model_router: {reason}"

    wants_add, wants_delete = _detect_goal_intents_keyword(goal)
    fallback_reason = (
        f"keyword_fallback: {reason}; "
        f"wants_add={wants_add}, wants_delete={wants_delete}"
    )
    return wants_add, wants_delete, fallback_reason


def _parse_list_count(tool_result: str) -> int | None:
    """Parse task count from list output text."""
    if "No tasks yet." in tool_result:
        return 0
    matches = _TASK_LINE_PATTERN.findall(tool_result)
    if matches:
        return len(matches)
    return None


def _update_validation_state(state: GoalValidationState, tool_name: str, tool_result: str) -> None:
    """Update validator evidence from one executed tool result."""
    if tool_name == "list_tasks":
        count = _parse_list_count(tool_result)
        if count is None:
            return
        if state.initial_count is None:
            state.initial_count = count
        state.latest_count = count
        if state.saw_mutation:
            state.saw_post_mutation_list = True
        return

    if tool_name == "add_task" and _ADD_SUCCESS_PATTERN.search(tool_result):
        state.add_success_count += 1
        state.saw_mutation = True
        return

    if tool_name == "delete_task" and _DELETE_SUCCESS_PATTERN.search(tool_result):
        state.delete_success_count += 1
        state.saw_mutation = True
        return

    if tool_name == "delete_tasks":
        match = _DELETE_BULK_SUCCESS_PATTERN.search(tool_result)
        if not match:
            return
        deleted_count = int(match.group(1))
        if deleted_count > 0:
            state.delete_success_count += deleted_count
            state.saw_mutation = True
        return


def _validate_goal_completion(state: GoalValidationState) -> tuple[bool, str]:
    """Validate completion for add/delete goals using deterministic rules."""
    if not state.wants_add and not state.wants_delete:
        return True, "No add/delete validation required."

    if state.wants_add and state.add_success_count < 1:
        return False, "Goal requests add, but no successful add operation was observed."

    if state.wants_delete and state.delete_success_count < 1:
        return False, "Goal requests delete, but no successful delete operation was observed."

    if state.initial_count is None or state.latest_count is None:
        return False, "Need list output to compare task counts before and after operations."

    if state.saw_mutation and not state.saw_post_mutation_list:
        return False, "Need a final list verification after add/delete operations."

    if state.wants_add and not state.wants_delete:
        if state.latest_count <= state.initial_count:
            return False, "Add goal not satisfied: final task count did not increase."

    if state.wants_delete and not state.wants_add:
        if state.latest_count >= state.initial_count:
            return False, "Delete goal not satisfied: final task count did not decrease."

    if state.wants_add and state.wants_delete:
        # Mixed goal: net count can be unchanged. Validate both operation types happened.
        expected_count = state.initial_count + state.add_success_count - state.delete_success_count
        if state.latest_count != expected_count:
            return False, "Mixed add/delete validation mismatch: final count does not match operations."

    return True, "Validation passed."


def _build_validation_feedback(state: GoalValidationState, reason: str) -> str:
    """Build deterministic corrective guidance for the next model turn."""
    if state.wants_delete and state.delete_success_count < 1:
        return (
            "Validation gate not satisfied. "
            f"{reason} "
            "Required next action: use the latest task list and delete matched ids "
            "(prefer delete_tasks for multiple ids), then call list_tasks to verify."
        )

    if state.wants_delete and state.delete_success_count > 0 and not state.saw_post_mutation_list:
        return (
            "Validation gate not satisfied. "
            f"{reason} "
            "Required next action: call list_tasks now to verify the post-delete state."
        )

    if state.wants_add and state.add_success_count < 1:
        return (
            "Validation gate not satisfied. "
            f"{reason} "
            "Required next action: call add_task for the requested items, then call list_tasks to verify."
        )

    return (
        "Validation gate not satisfied. "
        f"{reason} "
        "Continue with required operations before final answer."
    )


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
    try:
        system_prompt, selected_skills, route_reason = build_system_prompt(
            goal,
            client=client,
            model=chosen_model,
        )
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        _emit_event(on_event, "error", "skill_routing", str(exc))
        return str(exc)

    mcp_client = MCPClient()
    mcp_client.start()
    _emit_event(on_event, "agent_start", "run_agent", f"model={chosen_model}")
    _emit_event(on_event, "skill_route", "model_router", route_reason)
    for skill_name in selected_skills:
        _emit_event(on_event, "skill_used", skill_name, "Injected into system prompt.")

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
        # If the model later returns empty output, we can still return useful data
        # from the most recent successful tool execution.
        wants_add, wants_delete, intent_reason = _detect_goal_intents_hybrid(
            goal,
            client=client,
            model=chosen_model,
        )
        _emit_event(on_event, "intent_route", "goal_intent_router", intent_reason)
        validation_state = GoalValidationState(wants_add=wants_add, wants_delete=wants_delete)
        last_tool_result: str | None = None
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

                    if tool_result.strip():
                        last_tool_result = tool_result

                    _update_validation_state(validation_state, tool_name, tool_result)

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
                is_valid, validation_reason = _validate_goal_completion(validation_state)
                if not is_valid:
                    _emit_event(on_event, "validation", "not_done", validation_reason, step=step)
                    messages.append(
                        {
                            "role": "system",
                            "content": _build_validation_feedback(validation_state, validation_reason),
                        }
                    )
                    continue

                LOGGER.info("Stopping at step %s: final answer received", step)
                _emit_event(on_event, "stop", "final_answer", "Final answer produced.", step=step)
                return assistant_text

            # Condition 2: no tool calls and empty output; stop to avoid useless iterations.
            LOGGER.info("Stopping at step %s: empty response with no tool calls", step)
            is_valid, validation_reason = _validate_goal_completion(validation_state)
            if not is_valid:
                _emit_event(on_event, "validation", "not_done", validation_reason, step=step)
                messages.append(
                    {
                        "role": "system",
                        "content": _build_validation_feedback(validation_state, validation_reason),
                    }
                )
                continue

            if last_tool_result is not None:
                _emit_event(
                    on_event,
                    "stop",
                    "empty_response_with_tool_fallback",
                    "No tool calls and empty assistant output; returning last tool result.",
                    step=step,
                )
                return last_tool_result

            _emit_event(on_event, "stop", "empty_response", "No tool calls and empty assistant output.", step=step)
            return "No final answer produced."

        # Condition 3: hard cap reached (max_steps=5 by default).
        LOGGER.info("Stopping: reached max_steps=%s", max_steps)
        _emit_event(on_event, "stop", "max_steps", f"Reached max_steps={max_steps}.", step=max_steps)
        return f"Stopped after reaching max_steps={max_steps}."
    finally:
        mcp_client.close()
