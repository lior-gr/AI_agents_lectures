# Appendix A — Multiple Skills and Skill Selection

---

## A.1 Why multiple skills?

Real agents rarely run with a single skill.

Instead, you typically have:

- One or more domain skills (task planning, time estimation)
- One or more formatting skills (output templates)
- One or more safety/constraints skills (no hallucinated facts, cost limits)
- One or more workflow skills (always list tasks before planning, always ask for confirmation)

The goal is not "more prompt".
The goal is: **separation of instruction concerns**, like code modules.

---

## A.2 Skill patterns

### Pattern 1: Always-on skills

These are always injected:

- "Do not invent tasks"
- "Prefer tools over guesses"
- "Keep answers concise"
- "Respect max_steps and budget"

Think of them as global policies.

### Pattern 2: Conditional skills

Injected only when the user intent matches:

- Planning skill when user says "plan", "organize", "schedule"
- Reporting skill when user says "summarize", "status"
- Troubleshooting skill when user says "debug", "why is it failing"

### Pattern 3: Layered skills

You stack skills in a specific order:

1. Global policy skill
2. Domain skill
3. Output format skill

Order matters because later instructions can override earlier ones.

---

## A.3 Minimal "Skill Router" design (deterministic)

We will keep this simple and predictable.

Create:

- `skills/always_on.md`
- `skills/task_planning.md`
- `skills/status_reporting.md`
- `skills/output_format.md`

Then implement a function:

- Reads always-on skill every time
- Selects optional skills by keyword rules
- Concatenates selected skill texts into the system prompt

Example selection rules:

- If goal contains any of: "plan", "organize", "schedule" -> include task_planning
- If goal contains any of: "status", "summary", "report" -> include status_reporting
- If goal contains any of: "pretty", "table", "markdown" -> include output_format

This is not "AI deciding which skills to use".
This is deterministic routing. Easy to debug.

---

## A.4 Task — Add multiple skills to the project

Ask Codex:

> Create these files under skills/:
> - always_on.md
> - task_planning.md
> - status_reporting.md
> - output_format.md
> Each file should clearly state:
> - When it applies
> - What it changes about reasoning
> - What it must never do (no execution)
> Use concise bullet rules.
> Add a short comment block at the top: "This is a skill, not a tool."

Then ask Codex:

> In agent.py, implement a function load_skills(goal: str) -> str that:
> - Always loads skills/always_on.md
> - Conditionally loads other skills using deterministic keyword rules
> - Returns a single concatenated string to inject into the system prompt
> Requirements:
> - Do not change the agent loop
> - Do not change tool execution
> - Add comments explaining ordering and why routing is deterministic

---

## A.5 Expected behavior test

1) Add tasks first (CLI or GUI).

2) Run:

```
python main.py --goal "Give me a status report of my tasks"
```

Expected:

- Agent calls list_tasks
- Agent produces a structured summary (status_reporting skill)
- No invented tasks

3) Run:

```
python main.py --goal "Plan my tasks for today in a markdown table"
```

Expected:

- Agent calls list_tasks
- Agent proposes a plan (task_planning skill)
- Output in table style (output_format skill)
- Still no invented tasks (always_on skill)

---

## A.6 Checkpoint

Answer:

1. Are skills executed or injected?
2. Is the skill router deterministic or model-driven?
3. Does MCP server know which skills were used?
4. If output_format skill is removed, does planning still work?

If yes, you now understand multi-skill composition.
