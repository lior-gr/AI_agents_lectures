# Appendix B — Concrete Multi-Skill Router Example (load_skills)

---

## B.1 Goal

In Appendix A we described multiple skills and deterministic selection.

This appendix makes it concrete with:

- A recommended `skills/` folder layout
- A small deterministic router: `load_skills(goal: str) -> str`
- Ordering rules
- A tiny test matrix you can run manually

This is intentionally simple and debug-friendly.

---

## B.2 Recommended `skills/` layout

```
skills/
  always_on.md
  task_planning.md
  status_reporting.md
  output_format.md
```

Notes:

- Each file is plain text.
- No code execution.
- Each file should start with a short header comment like:
  "This is a skill, not a tool."

---

## B.3 Deterministic routing rules

Use explicit keyword triggers so behavior is predictable.

Example keyword sets:

- task_planning:  "plan", "organize", "schedule", "today", "this week"
- status_reporting: "status", "report", "summary", "summarize"
- output_format: "table", "markdown", "csv", "json", "pretty"

You can refine these later, but start small.

---

## B.4 Ordering rules (important)

When combining multiple skills into a single injected block, order matters.

Recommended ordering:

1) `always_on.md` (global policy)
2) Domain skill (task_planning or status_reporting)
3) Output formatting (output_format)

Reason:

- Global constraints should apply to everything.
- Domain rules should shape what the model decides to do.
- Output format should shape presentation last.

---

## B.5 Example code: `load_skills(goal: str) -> str`

This is a concrete implementation you can ask Codex to add to `agent.py`.

It does not change the agent loop.
It only affects prompt construction.

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
    """Deterministically select skills based on the goal text.

    Ordering:
      1) always_on
      2) domain skill(s)
      3) output_format

    Returns:
      A single concatenated string to inject into the system prompt.
    """

    selected_paths: List[str] = []

    # 1) Always-on global policy skill
    selected_paths.append(os.path.join(skills_dir, "always_on.md"))

    # 2) Domain skills
    if _contains_any(goal, ["plan", "organize", "schedule", "today", "this week"]):
        selected_paths.append(os.path.join(skills_dir, "task_planning.md"))

    if _contains_any(goal, ["status", "report", "summary", "summarize"]):
        selected_paths.append(os.path.join(skills_dir, "status_reporting.md"))

    # 3) Output format skill (presentation rules)
    if _contains_any(goal, ["table", "markdown", "csv", "json", "pretty"]):
        selected_paths.append(os.path.join(skills_dir, "output_format.md"))

    # Read and concatenate, skipping missing/empty files
    blocks: List[str] = []
    for p in selected_paths:
        txt = _read_text_file(p)
        if txt:
            blocks.append(txt)

    # Separator is plain ASCII to avoid terminal and toolchain surprises
    return "\n\n---\n\n".join(blocks)
```

Integration hint (high level):

- Call `skills_text = load_skills(goal)`
- Put `skills_text` inside the system message, after your base system policy, before the user goal

---

## B.6 Tiny manual test matrix

Create a few goals and verify which skills are selected.

| Goal | Expected skills |
|---|---|
| "Plan my tasks for today" | always_on + task_planning |
| "Give me a status report of my tasks" | always_on + status_reporting |
| "Plan my tasks for today in a markdown table" | always_on + task_planning + output_format |
| "Summarize my tasks in JSON" | always_on + status_reporting + output_format |
| "List tasks" | always_on (and likely no domain skill) |

How to validate quickly:

- Add a debug print in agent.py (temporarily) to print selected skill file names.
- Remove the debug print after validation.

---

## B.7 Common mistakes

1) Letting the model decide which skills to load  
   - That makes behavior hard to debug.

2) Putting tool instructions inside skills  
   - Skills should describe reasoning and constraints, not execution details.

3) Mixing skill logic into MCP server  
   - MCP should not know prompt content.

4) Changing the agent loop when adding skills  
   - Skills are reasoning injection only.

---

## B.8 Checkpoint

Answer:

1) Is `load_skills` deterministic or model-driven?  
2) Does `load_skills` execute tools?  
3) Does MCP server need to know about skills?  
4) If you remove output_format.md, does planning still work?

If you can answer clearly, you have multi-skill routing nailed.
