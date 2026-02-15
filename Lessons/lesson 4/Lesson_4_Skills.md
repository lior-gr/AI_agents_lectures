# 🧠 Tutorial: Codex, Agents, MCP & Skills  
# Lesson 4 — Skills: Structured Intelligence Without Execution

---

## 🎯 Goal of This Lesson

So far we have:

- A deterministic system (Lesson 1)
- A real agent loop (Lesson 2)
- Tool decoupling via MCP (Lesson 3)

Now we introduce:

- Skills
- Structured prompt templates
- Domain logic injection
- Separation between reasoning and execution

This is the final conceptual pillar.

---

## 4.1 What Is a Skill?

A Skill is:

- Structured domain knowledge
- A reasoning template
- A reusable prompt block
- Passive intelligence

It is NOT:

- A loop
- A tool executor
- A subprocess
- A storage layer

A Skill modifies HOW the agent thinks — not HOW it executes.

---

## 4.2 Skill vs Tool vs MCP

Let’s separate clearly:

Skill:
- Shapes reasoning
- Influences model output
- Lives inside agent context

Tool:
- Executes deterministic function

MCP:
- Hosts tools behind boundary

Agent:
- Decides when to use Skill or Tool

---

## 4.3 New Architecture Diagram

```
User
  ↓
Agent Loop
  ↓
Skill (prompt injection)
  ↓
Model reasoning
  ↓
Tool request
  ↓
MCP
  ↓
Storage
```

Skill affects reasoning layer only.

---

## 4.4 Task 1 — Create a Skill File

Ask Codex:

> Create a new folder called skills.
> Inside it create task_planning_skill.md.
> The file should:
> - Define when this skill should be used
> - Provide structured reasoning rules for task planning
> - Define constraints (no hallucinated tasks)
> - Explain how tasks should be prioritized
> - Not include execution logic
> - Include comments explaining why this is not a tool

This file is pure text.

No Python.

---

## 4.5 Example Skill Content Structure

The skill might contain:

- Goal analysis rules
- Task grouping heuristics
- Time estimation assumptions
- Output formatting instructions
- Constraints against hallucination

Example snippet:

```
When user asks to "plan" or "organize":
- First list existing tasks using tool
- Group by priority
- Estimate time realistically
- Never invent tasks
```

Notice:

It tells the agent HOW TO THINK — not HOW TO EXECUTE.

---

## 4.6 Integrate Skill into Agent

Ask Codex:

> Modify agent.py so that before sending messages to OpenAI,
> it loads task_planning_skill.md and injects it into the system prompt.
> The skill must:
> - Not modify loop logic
> - Not modify tool logic
> - Only affect prompt construction
> Add detailed comments explaining separation.

---

## 4.7 What Should NOT Change

- Agent loop structure
- Tool calling mechanism
- MCP server
- Storage

Only reasoning changes.

---

## 4.8 Test Case

Run:

```
python main.py --goal "Plan my tasks for today"
```

Observe:

Without skill:
- Agent may respond loosely.

With skill:
- Agent should:
  - Call list_tasks first
  - Group tasks
  - Avoid inventing new tasks
  - Stay within constraints

Skill increases reasoning discipline.

---

## 4.9 What This Teaches

You now understand:

- Skills live in prompt space
- Tools live in execution space
- MCP lives in boundary space
- Agent lives in control space

These are different dimensions.

---

## 4.10 Enterprise Context

In enterprise environments:

- Skills could be centrally versioned
- Skills could be enforced per team
- Skills could be audited
- Skills could be dynamically loaded

But conceptually:

Skill is still prompt logic — not execution.

---

## 🎯 Lesson 4 Checkpoint

Answer:

1. Does a Skill execute code?
2. Does a Skill own the loop?
3. Does MCP know about Skills?
4. Where is a Skill injected?
5. Can multiple agents share a Skill?

If you answer correctly, you now understand the full stack.

---

## 🔜 Next Lesson Preview

Lesson 5 will:

- Add a minimal GUI (Qt or lightweight alternative)
- Show architecture unchanged
- Demonstrate that UI is another boundary
- Reinforce separation principles

We are approaching full integration.
