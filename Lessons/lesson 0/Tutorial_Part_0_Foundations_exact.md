# 🧠 Tutorial: Codex, Agents, MCP & Skills  
## Part 0 — Foundations & Mental Models

Welcome to the lab.

This tutorial will teach you:

- What Codex actually is
- What an Agent really is
- What a Skill is (and is not)
- What an MCP server is
- How these components interact
- How they **must not** interact

We begin with mental clarity before touching code.

---

# 0.1 The Vocabulary

Let’s define every term carefully.

---

## 1️⃣ Codex Plugin (VS Code Extension)

**What it is:**
An AI-powered coding assistant integrated into VS Code.

**What it does:**
- Reads your workspace
- Writes / edits code
- Runs terminal commands (if allowed)
- Can call tools
- Can follow project instructions (`AGENTS.md`)
- Can use Skills
- Can connect to MCP servers

**What it is NOT:**
- It is not your backend.
- It is not your production runtime.
- It is not your deployed application.
- It is not your agent logic.

It is a *developer assistant agent*.

---

### Conceptual View

image_group{"layout":"carousel","aspect_ratio":"1:1","query":["software architecture layers diagram simple","developer assistant ai architecture diagram","ai coding assistant interacting with codebase diagram","vs code ai assistant architecture conceptual diagram"],"num_per_query":1}

Mental abstraction:

```
You (human)
   ↓
Codex (AI coding assistant)
   ↓
Your project files
   ↓
Your runtime application
```

Codex helps build the system.  
It is not the system.

---

## 2️⃣ Agent

An **Agent** is a system that:

- Has a goal
- Decides what to do next
- Calls tools
- Observes results
- Repeats until finished

This is crucial:

> An agent owns the decision loop.

---

### Agent Loop (Core Concept)

image_group{"layout":"carousel","aspect_ratio":"1:1","query":["agent loop diagram plan act observe decide","ai agent control loop diagram","reinforcement learning loop simple diagram","autonomous agent architecture minimal diagram"],"num_per_query":1}

Minimal structure:

```
Goal
  ↓
Plan
  ↓
Act (call tool)
  ↓
Observe result
  ↓
Decide
  ↓
Repeat or Stop
```

Without this loop, you do not have an agent.

---

## 3️⃣ Skill

A **Skill** is:

- A reusable capability
- A structured instruction bundle
- Domain knowledge
- Templates + rules

It does not:
- Loop
- Decide autonomously
- Execute tools directly

It is passive.

Think:

> A skill is expertise.
> An agent is behavior.

---

### Mental Model

```
Agent → decides when to use → Skill
Skill → provides structured domain logic
```

---

## 4️⃣ MCP Server (Model Context Protocol Server)

An **MCP server** is:

- A tool provider
- A resource provider
- A passive capability host
- A standardized bridge between models and systems

It does not:
- Have goals
- Plan
- Loop
- Make decisions

It waits for requests.

---

### Conceptual Separation

image_group{"layout":"carousel","aspect_ratio":"1:1","query":["microservice tool server architecture diagram simple","plugin server architecture diagram ai tools","model context protocol conceptual diagram","tool provider server architecture simple clean diagram"],"num_per_query":1}

Think of it as:

```
Agent → calls → MCP Server → executes tool → returns result
```

---

# 0.2 The Stack — Who Does What?

Let’s layer everything.

---

## Full Conceptual Stack

image_group{"layout":"carousel","aspect_ratio":"1:1","query":["layered ai architecture diagram agent mcp tools","software stack diagram ai agent tools mcp clean","agent tools skills layered architecture illustration","ai application architecture layered diagram minimal modern"],"num_per_query":1}

Mental stack:

```
Human
  ↓
Codex (development assistant)
  ↓
Your Agent (runtime logic)
  ↓
Skills (domain knowledge)
  ↓
MCP Servers (tool providers)
  ↓
Tools (filesystem, DB, subprocess, APIs)
```

---

# 0.3 Interaction Rules (Very Important)

Let’s formalize what can and cannot happen.

---

## ✔ Allowed Interactions

| Component | Can Interact With |
|------------|------------------|
| Codex | Files, terminal, MCP, skills |
| Agent | Skills, MCP, tools |
| Skill | Used by agent |
| MCP Server | Executes tools |
| Tool | External world |

---

## ❌ Not Allowed / Conceptually Wrong

| Wrong Idea | Why Wrong |
|------------|----------|
| MCP server planning tasks | It is passive |
| Skill executing subprocess | Skills do not run |
| Agent editing source code directly | That is Codex’s role |
| Codex acting as production runtime | Codex is dev assistant |

---

# 0.4 Two Kinds of Agents

This is subtle but critical.

---

## Type A — Development Agent

Codex in VS Code is itself an agent.

It:
- Reads your repo
- Edits files
- Runs commands
- Follows AGENTS.md

This is a **development-time agent**.

---

## Type B — Runtime Agent

An agent you write in your app:

Example:
- A task planner
- A log analyzer
- A regression triage system

This is a **runtime agent**.

---

### Key Insight

Codex builds runtime agents.

Codex ≠ your runtime agent.

---

# 0.5 Minimal Concrete Example

Let’s make it very simple.

Imagine we build a task manager.

---

### Option 1 — No Agent

User types:
```
add task: buy milk
```

System:
- Writes to file
- Done

No decisions. No loop. No agent.

---

### Option 2 — With Agent

User types:
```
Plan my week
```

Agent:
1. Reads current tasks
2. Groups by priority
3. Estimates time
4. Allocates slots
5. Suggests schedule
6. Waits for confirmation
7. Adjusts

Now we have:
- Planning
- Iteration
- Tool calls
- Observations

That is an agent.

---

# 0.6 Where Skills Fit in That Example

Skill might contain:

- Scheduling heuristics
- Time estimation rules
- Task prioritization logic
- Prompt templates

Agent uses skill when needed.

---

# 0.7 Where MCP Fits in That Example

MCP server could provide:

- `task.read_all`
- `task.create`
- `calendar.reserve_slot`
- `timer.start`

Agent calls MCP.
MCP executes.
Returns result.

---

# 0.8 Enterprise Features (What We Won’t Use)

Enterprise environments might allow:

- Remote MCP servers
- Central authentication
- Policy enforcement
- Shared tool registries
- Multi-user agent orchestration

We will not depend on any of that.

We will:
- Build everything locally
- Use OpenAI API
- Stay under $10 usage

---

# 0.9 Summary Diagram

Final mental compression:

```
Codex → builds → Agent
Agent → uses → Skill
Agent → calls → MCP
MCP → executes → Tools
Tools → affect → System
```

If you understand this diagram, everything else becomes mechanical.

---

# 🎯 Checkpoint

Before moving to Lesson 1, answer mentally:

1. Does a Skill ever run a subprocess?
2. Does an MCP server decide when to call tools?
3. Can Codex be your production backend?
4. Who owns the loop in an agent system?

If those answers are clear, you're ready.

---

# Next

Lesson 1 will begin the practical training.

We will:

- Set up a Windows-first environment
- Initialize a minimal project
- Use Codex deliberately
- Force it to write heavily commented code
- Build a non-agent baseline CLI task manager

Only after that will we introduce:
- Agent loop
- MCP server
- Skill structure

We build from stable ground.

---

When you’re ready, say:

> Proceed to Lesson 1.
