"""Model-assisted skill router with deterministic validation.

This module is intentionally small and pure:
- Standard library only (`json`, `typing`).
- No OpenAI SDK import.
- No side effects.

Safety and debuggability design:
- The model is constrained to a fixed output schema.
- Output is validated with deterministic checks.
- Retries are bounded by `max_attempts`.
- Failures return explicit reasons instead of silent fallback behavior.
"""

from __future__ import annotations

import json
from typing import Callable

# Allowed skills and their routing descriptions.
# Keys are the only valid enum values the model may return.
ALLOWED_SKILLS: dict[str, str] = {
    "always_on": "Baseline rules that apply to all goals.",
    "task_planning": "Use when the goal asks to plan, organize, or sequence work.",
    "task_deletion": "Use when the goal asks to delete, remove, or clean up tasks.",
    "status_reporting": "Use when the goal asks for progress or status updates.",
    "output_format": "Use when the goal asks for a specific response format.",
}


def _build_routing_prompt(goal: str, validation_error: str | None = None) -> str:
    """Build the routing prompt with fixed schema and allowed enum values."""
    skill_lines = []
    for skill_name, skill_description in ALLOWED_SKILLS.items():
        skill_lines.append(f'- "{skill_name}": {skill_description}')
    skills_block = "\n".join(skill_lines)

    retry_block = ""
    if validation_error:
        retry_block = (
            "\nPrevious response failed validation.\n"
            f"Validation error: {validation_error}\n"
            "Return corrected JSON only.\n"
        )

    return (
        "You are a strict skill router.\n"
        "Select the minimal set of skills needed for the goal.\n"
        "Output must be valid JSON only with this exact object shape:\n"
        '{\"skills\": [\"<allowed_skill>\", ...], \"reason\": \"<short reason>\"}\n'
        "Rules:\n"
        "- Do not include keys other than skills and reason.\n"
        "- skills must be an array of unique strings.\n"
        "- Every skills value must be one of the allowed enum values.\n"
        "- Do not return markdown, prose, or code fences.\n"
        "- Keep reason concise.\n"
        "Allowed skill enum values:\n"
        f"{skills_block}\n"
        f"Goal:\n{goal}\n"
        f"{retry_block}"
    )


def _build_intent_prompt(goal: str, validation_error: str | None = None) -> str:
    """Build prompt for add/delete goal-intent classification."""
    retry_block = ""
    if validation_error:
        retry_block = (
            "\nPrevious response failed validation.\n"
            f"Validation error: {validation_error}\n"
            "Return corrected JSON only.\n"
        )

    return (
        "You are a strict goal intent classifier.\n"
        "Classify whether the goal asks to add tasks and/or delete tasks.\n"
        "Output must be valid JSON only with this exact object shape:\n"
        '{"wants_add": true|false, "wants_delete": true|false, "reason": "<short reason>"}\n'
        "Rules:\n"
        "- Do not include keys other than wants_add, wants_delete, and reason.\n"
        "- wants_add must be a boolean.\n"
        "- wants_delete must be a boolean.\n"
        "- reason must be a short string.\n"
        "- Do not return markdown, prose, or code fences.\n"
        f"Goal:\n{goal}\n"
        f"{retry_block}"
    )


def _validate_router_output(raw_output: str) -> tuple[bool, list[str], str]:
    """Validate model output with strict deterministic checks.

    Rejects:
    - non-JSON output
    - wrong keys
    - unknown skills
    - duplicate skills
    """
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return False, [], "Output is not valid JSON."

    if not isinstance(parsed, dict):
        return False, [], "JSON root must be an object."

    allowed_keys = {"skills", "reason"}
    actual_keys = set(parsed.keys())
    if actual_keys != allowed_keys:
        return (
            False,
            [],
            "JSON keys must be exactly ['skills', 'reason'] with no extras.",
        )

    skills = parsed.get("skills")
    reason = parsed.get("reason")

    if not isinstance(skills, list):
        return False, [], "skills must be a JSON array."

    if not all(isinstance(item, str) for item in skills):
        return False, [], "skills must contain only strings."

    if len(skills) != len(set(skills)):
        return False, [], "skills must not contain duplicates."

    unknown = [item for item in skills if item not in ALLOWED_SKILLS]
    if unknown:
        return False, [], f"Unknown skills: {unknown}."

    if not isinstance(reason, str):
        return False, [], "reason must be a string."

    return True, skills, reason


def _validate_intent_output(raw_output: str) -> tuple[bool, dict[str, bool], str]:
    """Validate model output for add/delete intent classification."""
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return False, {}, "Output is not valid JSON."

    if not isinstance(parsed, dict):
        return False, {}, "JSON root must be an object."

    allowed_keys = {"wants_add", "wants_delete", "reason"}
    actual_keys = set(parsed.keys())
    if actual_keys != allowed_keys:
        return (
            False,
            {},
            "JSON keys must be exactly ['wants_add', 'wants_delete', 'reason'] with no extras.",
        )

    wants_add = parsed.get("wants_add")
    wants_delete = parsed.get("wants_delete")
    reason = parsed.get("reason")

    if not isinstance(wants_add, bool):
        return False, {}, "wants_add must be a boolean."

    if not isinstance(wants_delete, bool):
        return False, {}, "wants_delete must be a boolean."

    if not isinstance(reason, str):
        return False, {}, "reason must be a string."

    return True, {"wants_add": wants_add, "wants_delete": wants_delete}, reason


def route_skills_with_model(
    goal: str,
    call_model_fn: Callable[[str], str],
    max_attempts: int,
) -> tuple[bool, list[str], str]:
    """Route skills with bounded retries and deterministic validation.

    Parameters:
    - goal: user goal text to route.
    - call_model_fn: function that takes a prompt string and returns model text.
    - max_attempts: hard retry cap.

    Returns:
    - (True, skills, reason) on success.
    - (False, [], failure_reason) when attempts are exhausted.
    """
    if not isinstance(goal, str) or not goal.strip():
        return False, [], "Goal must be a non-empty string."
    if max_attempts < 1:
        return False, [], "max_attempts must be at least 1."

    last_error = "No attempts were made."
    for _ in range(max_attempts):
        prompt = _build_routing_prompt(goal=goal, validation_error=last_error)
        try:
            raw_output = call_model_fn(prompt)
        except Exception as exc:  # pragma: no cover - defensive guard
            last_error = f"Model call failed: {exc}"
            continue

        ok, skills, reason = _validate_router_output(raw_output)
        if ok:
            return True, skills, reason

        last_error = reason

    return False, [], f"Routing failed after {max_attempts} attempt(s): {last_error}"


def route_goal_intent_with_model(
    goal: str,
    call_model_fn: Callable[[str], str],
    max_attempts: int,
) -> tuple[bool, dict[str, bool], str]:
    """Route add/delete intent with bounded retries and deterministic validation."""
    if not isinstance(goal, str) or not goal.strip():
        return False, {}, "Goal must be a non-empty string."
    if max_attempts < 1:
        return False, {}, "max_attempts must be at least 1."

    last_error = "No attempts were made."
    for _ in range(max_attempts):
        prompt = _build_intent_prompt(goal=goal, validation_error=last_error)
        try:
            raw_output = call_model_fn(prompt)
        except Exception as exc:  # pragma: no cover - defensive guard
            last_error = f"Model call failed: {exc}"
            continue

        ok, intent, reason = _validate_intent_output(raw_output)
        if ok:
            return True, intent, reason

        last_error = reason

    return False, {}, f"Intent routing failed after {max_attempts} attempt(s): {last_error}"


__all__ = ["ALLOWED_SKILLS", "route_goal_intent_with_model", "route_skills_with_model"]
