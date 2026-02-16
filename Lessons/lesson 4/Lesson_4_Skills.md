# Tutorial: Codex, Agents, MCP and Skills
# Lesson 4 - Skills: Structured Intelligence Without Execution

---

## Goal of This Lesson

So far we have:

- A deterministic system (Lesson 1)
- A real agent loop (Lesson 2)
- Tool decoupling via MCP (Lesson 3)

Now we introduce:

- Skills
- Structured prompt templates
- Domain-logic injection
- Separation between reasoning and execution

This is the final conceptual pillar before UI integration.

---

## 4.1 What You Will Learn

By the end of this lesson, you should be clear on:

- What a skill is and what it is not
- How skills differ from tools and MCP boundaries
- How to add a skill file with reasoning rules only
- How to inject skill text into prompt construction without changing control flow
- How to verify reasoning quality changes while execution architecture stays stable

---

## 4.2 What Is a Skill?

A skill is:

- Structured domain knowledge
- A reasoning template
- A reusable prompt block
- Passive intelligence

A skill is NOT:

- A loop
- A tool executor
- A subprocess
- A storage layer

A skill modifies how the model reasons, not how execution happens.

Skill text format in practice:

- A skill can be written in any plain text format because the agent injects text into the prompt.
- In practice, teams use `.md` files (Markdown) as the standard.
- Markdown is easy to read and review.
- Headings and bullet lists make reasoning rules explicit.
- Diffs are cleaner in Git, so changes are easier to audit.
- It stays text-only, so the skill remains guidance, not executable behavior.

---

## 4.3 Skill vs Tool vs MCP

Separate responsibilities clearly:

- Skill: shapes reasoning and output discipline
- Tool: executes deterministic function behavior
- MCP: hosts and dispatches tools behind a boundary
- Agent: owns loop control and decides when to use skills/tools

---

## 4.4 Reasoning and Execution Flow

```text
User
  -> Agent loop
  -> Skill text injected into prompt
  -> Model reasoning
  -> Tool request
  -> MCP boundary
  -> Storage
```

Skill affects reasoning layer only.

Task-planner example:

- Skill says "group by urgency and do not invent tasks"
- Agent still calls real tools through MCP to inspect/update tasks

---

## 4.5 Task 1 - Create a Skill File

Prompt to Codex:

> Create a new folder called `skills`.
> Inside it create `task_planning_skill.md`.
> The file should:
> - Define when this skill should be used.
> - Provide structured reasoning rules for task planning.
> - Define constraints (no hallucinated tasks).
> - Explain how tasks should be prioritized.
> - Not include execution logic.
> - Include comments explaining why this is not a tool.
>
> This file is pure text. No Python.
> Do not connect this skill to the agent loop yet.
>
> Explanation placement:
> - In file comments/text: explain intent, constraints, and boundaries.
> - In Codex chat response: summarize what was added and why.
> - In both: explain why skill is reasoning-only.

Expected output after this stage:

- `skills/task_planning_skill.md` exists.
- Reasoning rules and constraints are explicit.
- No runtime execution logic is added.

Good and bad rule examples:

| Rule | Judgment | Reason |
| --- | --- | --- |
| `Prioritize tasks by deadline first, then urgency, then effort.` | Good | Explicit ordering and easy to verify in output. |
| `Only plan using tasks already present in the current task list.` | Good | Prevents hallucinations and is testable with empty/non-empty lists. |
| `Be smart and helpful.` | Bad | Too vague; no concrete pass/fail check. |
| `Call list_tasks then complete_task for old items.` | Bad | Hard-codes tool behavior; skill should stay reasoning-level, not execution-level. |

Student task after generation:

1. Verify skill content is actionable but tool-agnostic.
2. Verify constraints are explicit and testable.
3. Verify no execution behavior is described as if it were code.

---

## 4.6 Example Skill Content Structure

The skill might contain:

- Goal analysis rules
- Task grouping heuristics
- Time estimation assumptions
- Output discipline instructions
- Constraints against hallucination

Simple example:

When user asks to "plan" or "organize":
- First inspect existing tasks.
- Group by urgency and time constraints.
- Estimate effort realistically.
- Never invent tasks that are not present.

Notice:

It tells the agent how to think, not how to execute.

---

## 4.7 Task 2 - Integrate Skill into Agent

Prompt to Codex:

> Modify `agent.py` so that before sending messages to OpenAI,
> it loads `task_planning_skill.md` and injects it into the system prompt.
>
> The skill integration must:
> - Not modify loop logic.
> - Not modify tool execution logic.
> - Not modify MCP communication.
> - Only affect prompt construction.
>
> Add comments explaining the separation.
>
> Explanation placement:
> - In code comments: explain where and how skill text is injected.
> - In Codex chat response: summarize exactly what remained unchanged.
> - In both: explain reasoning-path vs execution-path separation.

Expected output after this stage:

- Agent includes skill text in system prompt construction.
- Execution stack stays untouched.
- Reasoning constraints are now explicit at runtime.

Student task after generation:

1. Diff should show prompt-construction changes only.
2. Loop, tool path, and MCP path should remain unchanged.
3. Verify skills are loaded before model call construction.

---

## 4.8 What Should NOT Change

- Agent loop structure
- Tool calling mechanism
- MCP server and client behavior
- Storage schema and persistence behavior

Only reasoning changes.

---

## 4.9 Test Case

Run:

```bash
python main.py --goal "Plan my tasks for today"
```

Observe:

- Without skill: response may be loose.
- With skill: should inspect existing tasks, prioritize clearly, and avoid inventing tasks.

Skill increases reasoning discipline.

---

## 4.10 What This Teaches + Scope Note

You now understand:

- Skills live in prompt space
- Tools live in execution space
- MCP lives in boundary space
- Agent lives in control space

Enterprise features we are not using in this course:

- Central skill registries with version management
- Policy-enforced skill selection per team/environment
- Skill audit trails and governance workflows
- Dynamic runtime skill loading from external services

We exclude these now to focus on core skill reasoning boundaries.

---

## 4.11 Lesson 4 Checkpoint

Answer clearly:

1. Does a skill execute code?
2. Does a skill own the loop?
3. Does MCP know about skills?
4. Where is a skill injected?
5. Can multiple agents share one skill file?

---

## Next Lesson Preview

Lesson 5 will:

- Add a minimal GUI
- Show architecture unchanged
- Demonstrate UI as another boundary
- Reinforce separation principles
