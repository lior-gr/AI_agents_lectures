"""Bounded model-assisted skill routing (Appendix B).

This router limits model flexibility to a fixed allowed enum and deterministic validation.
No keyword fallback is used in this module.
"""

from __future__ import annotations

import json
from typing import Callable, Iterable, Sequence

ALLOWED_SKILLS: tuple[str, ...] = (
    "task_planning",
    "status_reporting",
    "output_format",
)

_SKILL_DESCRIPTIONS = {
    "task_planning": "Use for planning, prioritization, and scheduling style requests.",
    "status_reporting": "Use for status summaries, reports, and current-state explanations.",
    "output_format": "Use when user asks for explicit output style like JSON/table/markdown/csv.",
}


def _build_router_messages(goal: str) -> list[dict[str, str]]:
    enum_text = ", ".join(ALLOWED_SKILLS)
    descriptions = "\n".join(f"- {name}: {_SKILL_DESCRIPTIONS[name]}" for name in ALLOWED_SKILLS)
    system_text = (
        "You are a strict skill router. "
        "Return JSON only with keys skills, confidence, notes. "
        "Use only allowed skills and never include always_on.\n\n"
        f"Allowed skills: {enum_text}\n"
        f"Skill descriptions:\n{descriptions}\n"
        "Rules:\n"
        "- skills: array of unique allowed skill names\n"
        "- confidence: number in [0,1]\n"
        "- notes: short string under 160 chars\n"
        "- no markdown, no commentary outside JSON"
    )
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": f"Goal: {goal.strip()}"},
    ]


def _validate_payload(payload: object) -> tuple[bool, list[str], str]:
    if not isinstance(payload, dict):
        return False, [], "Payload is not a JSON object."

    expected_keys = {"skills", "confidence", "notes"}
    if set(payload.keys()) != expected_keys:
        return False, [], "Payload keys must be exactly skills/confidence/notes."

    skills = payload.get("skills")
    confidence = payload.get("confidence")
    notes = payload.get("notes")

    if not isinstance(skills, list):
        return False, [], "skills must be a list."

    normalized: list[str] = []
    for item in skills:
        if not isinstance(item, str):
            return False, [], "skills list must contain strings only."
        if item not in ALLOWED_SKILLS:
            return False, [], f"Unknown skill: {item}"
        normalized.append(item)

    if len(set(normalized)) != len(normalized):
        return False, [], "skills must not contain duplicates."

    if not isinstance(confidence, (int, float)):
        return False, [], "confidence must be numeric."
    if confidence < 0 or confidence > 1:
        return False, [], "confidence must be in [0,1]."

    if not isinstance(notes, str):
        return False, [], "notes must be a string."
    if len(notes) > 160:
        return False, [], "notes must be short (<=160 chars)."

    return True, normalized, notes


def route_skills_with_model(
    goal: str,
    call_model_fn: Callable[[Sequence[dict[str, str]]], str],
    max_attempts: int,
) -> tuple[bool, list[str], str]:
    """Route optional skills with strict validation and bounded retries.

    Returns (ok, skills, reason). On failure, ok=False and skills is empty.
    """
    if max_attempts <= 0:
        return False, [], "max_attempts must be positive."

    messages = _build_router_messages(goal)
    failure_reasons: list[str] = []

    for attempt in range(1, max_attempts + 1):
        try:
            raw = call_model_fn(messages)
        except Exception as exc:  # deterministic fail path; no fallback to keyword router
            failure_reasons.append(f"attempt {attempt}: model call error: {exc}")
            continue

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            failure_reasons.append(f"attempt {attempt}: invalid JSON: {exc}")
            continue

        ok, skills, reason = _validate_payload(payload)
        if ok:
            return True, skills, f"attempt {attempt}: {reason}"
        failure_reasons.append(f"attempt {attempt}: {reason}")

    summary = " | ".join(failure_reasons) if failure_reasons else "routing failed"
    return False, [], summary
