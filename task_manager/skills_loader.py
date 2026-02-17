"""Deterministic multi-skill loader (Appendix A).

This module is prompt-construction logic only.
It does not execute tools and does not change loop control.
"""

from __future__ import annotations

import os
from typing import List


def _read_text_file(path: str) -> str:
    """Read a UTF-8 text file. Return empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except OSError:
        return ""


def _contains_any(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def load_skill_names(goal: str) -> List[str]:
    """Deterministically select skill names based on keyword triggers."""
    selected: List[str] = ["always_on"]

    if _contains_any(goal, ["plan", "organize", "schedule", "today", "this week"]):
        selected.append("task_planning")

    if _contains_any(goal, ["status", "report", "summary", "summarize", "display"]):
        selected.append("status_reporting")

    if _contains_any(goal, ["table", "markdown", "csv", "json", "pretty"]):
        selected.append("output_format")

    return selected


def load_skills(goal: str, skills_dir: str = "skills") -> str:
    """Deterministically select and concatenate skill text blocks."""
    selected_paths: List[str] = []
    for name in load_skill_names(goal):
        selected_paths.append(os.path.join(skills_dir, f"{name}.md"))

    blocks: List[str] = []
    for path in selected_paths:
        text = _read_text_file(path)
        if text:
            blocks.append(text)

    return "\n\n---\n\n".join(blocks)
