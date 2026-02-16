# Appendix A - Deterministic Multi-Skill Routing (Concept + Code)

---

## A.1 Goal and scope

This appendix combines the old Appendix A and Appendix B.

Use it for one complete flow:

- Understand why multiple skills are needed.
- Define deterministic routing rules.
- Implement `load_skills(goal)`.
- Validate behavior with a small test matrix.

Out of scope:

- Model-driven skill selection.
- Runtime loop or tool execution changes.

---

## A.2 Why multiple skills?

Real agents usually need separate instruction layers:

- Domain behavior (task planning, status reporting)
- Formatting behavior (markdown table, JSON)
- Safety and policy behavior (no invented tasks, concise output)

Goal: separate concerns in prompt design, similar to code modules.

---

## A.3 Deterministic router contract

A deterministic router means explicit rules choose skills.

Contract:

1) Input: `goal` text and available skill files.
2) Output: one ordered, concatenated skill text block.
3) Invariants:
   - Always include `always_on.md` first.
   - Add optional domain skills only when triggers match.
   - Add output formatting skill last.
4) Non-goals:
   - letting the model decide selected skills
   - executing skills as tools
   - changing MCP behavior or loop control

---

## A.4 Recommended layout and trigger sets

```text
skills/
  always_on.md
  task_planning.md
  status_reporting.md
  output_format.md
```

Example keyword triggers:

- `task_planning`: plan, organize, schedule, today, this week
- `status_reporting`: status, report, summary, summarize
- `output_format`: table, markdown, csv, json, pretty

---

## A.5 Reference code: `load_skills(goal: str) -> str`

```python
import os
from typing import List


def _read_text_file(path: str) -> str:
    """Read a UTF-8 text file. Return empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def load_skills(goal: str, skills_dir: str = "skills") -> str:
    """Deterministically select skills based on goal text.

    Ordering:
      1) always_on
      2) domain skill(s)
      3) output_format

    Returns:
      A single concatenated string for system prompt injection.
    """

    selected_paths: List[str] = []

    # 1) Always-on policy skill
    selected_paths.append(os.path.join(skills_dir, "always_on.md"))

    # 2) Domain skills
    if _contains_any(goal, ["plan", "organize", "schedule", "today", "this week"]):
        selected_paths.append(os.path.join(skills_dir, "task_planning.md"))

    if _contains_any(goal, ["status", "report", "summary", "summarize"]):
        selected_paths.append(os.path.join(skills_dir, "status_reporting.md"))

    # 3) Output format skill
    if _contains_any(goal, ["table", "markdown", "csv", "json", "pretty"]):
        selected_paths.append(os.path.join(skills_dir, "output_format.md"))

    blocks: List[str] = []
    for p in selected_paths:
        txt = _read_text_file(p)
        if txt:
            blocks.append(txt)

    return "\n\n---\n\n".join(blocks)
```

---

## A.6 Integration steps

1) Call `skills_text = load_skills(goal)`.
2) Inject `skills_text` into the system prompt after base policy and before user goal.
3) Do not modify:
   - the agent loop
   - tool execution path
   - MCP server responsibilities

---

## A.7 Manual test matrix

| Goal | Expected skills |
|---|---|
| "Plan my tasks for today" | always_on + task_planning |
| "Give me a status report of my tasks" | always_on + status_reporting |
| "Plan my tasks for today in a markdown table" | always_on + task_planning + output_format |
| "Summarize my tasks in JSON" | always_on + status_reporting + output_format |
| "List tasks" | always_on only (typically no domain skill) |

Quick validation:

- Temporarily print selected file names.
- Run the goals above.
- Remove debug print after validation.

---

## A.8 Common mistakes

1) Letting the model choose skills in a deterministic router.
2) Putting tool execution instructions inside skill files.
3) Moving skill logic into MCP server code.
4) Changing loop execution while adding prompt routing.

---

## A.9 Checkpoint

Answer:

1) Are skills executed or injected?
2) Is `load_skills` deterministic or model-driven?
3) Does MCP need to know which skills were loaded?
4) If `output_format.md` is removed, can planning still work?

If yes, the merged appendix is complete.
