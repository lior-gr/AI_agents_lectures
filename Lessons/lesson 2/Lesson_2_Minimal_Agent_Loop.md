# 🧠 Tutorial: Codex, Agents, MCP & Skills  
# Lesson 2 — Introducing a Real Minimal Agent Loop

---

## 🎯 Goal of This Lesson

We now transform the deterministic CLI system into something that contains:

- A real agent loop
- OpenAI API integration
- Controlled iteration
- Cost awareness
- Strict guardrails

We will not break the baseline system.

We will wrap it.

---

## 2.1 What We Are Adding

Current system:

```
User → CLI → Storage → JSON
```

New system:

```
User
  ↓
Agent Loop
  ↓
Tool Call (local function)
  ↓
Storage → JSON
```

Important:

The agent does NOT replace storage.  
It sits above it.

---

## 2.2 What Is an Agent in This Context?

Minimal definition for this lesson:

An agent is:

1. A loop
2. With a goal
3. That can call tools
4. That decides when to stop

We will implement:

- Max 5 steps
- No recursive self-prompting
- Deterministic tool whitelist
- Strict token budget awareness

---

## 2.3 Budget Awareness

You allowed up to $10 total.

We will:
- Use a small model
- Limit max tokens
- Log usage
- Avoid multi-turn reasoning explosions

Expected cost for this lesson:
Well under $1.

---

## 2.4 New Architecture Diagram

```
main.py
   ↓
agent.py
   ↓
tools.py
   ↓
storage.py
   ↓
tasks.json
```

Clear layering.

No shortcuts.

---

## 2.5 Task 1 — Ask Codex to Create Agent Skeleton

Open your project.

Ask Codex:

> Create a new file agent.py.  
> Implement a minimal agent loop that:  
> - Accepts a user goal string  
> - Calls OpenAI chat completion API  
> - Supports tool calling  
> - Has max_steps=5  
> - Logs each step  
> - Does not exceed 800 tokens per call  
> - Includes detailed comments explaining:  
>     - Where the loop is  
>     - Where tool calls are processed  
>     - Where stopping conditions are enforced  
> Do not implement tools yet.  
> Just stub them.

---

## Expected Output

Codex should create:

```
agent.py
```

Containing:

- A function like `run_agent(goal: str)`
- A loop
- A message history list
- Tool call detection logic
- Stop condition

---

## 2.6 What You Must Inspect Carefully

Look for:

1. Where is the loop?
2. Where are steps counted?
3. Where does it stop?
4. Is the OpenAI key read from environment variable?
5. Is temperature low?
6. Are tool schemas defined?

If any of these are sloppy — fix them.

---

## 2.7 Add Tool Layer (Local Only)

Now ask Codex:

> Create tools.py.  
> Define tool schemas for:  
> - add_task(text: str)  
> - list_tasks()  
> - complete_task(task_id: int)  
> These must call existing storage.py functions.  
> Do not put business logic inside the agent.  
> Add detailed comments explaining separation of concerns.

Important principle:

The agent never edits JSON.

It only calls tools.

---

## 2.8 Connect Agent to CLI

Modify `main.py`:

Add a new command:

```
python main.py --goal "Plan my tasks for today"
```

Instead of calling storage directly, this should:

```
agent.run_agent(goal)
```

But:

Keep old deterministic commands working.

We are adding a layer, not replacing it.

---

## 2.9 What the Agent Should Be Able to Do

Example interaction:

User:

```
python main.py --goal "Add buy milk and then show me all tasks"
```

Agent:

1. Decides to call add_task  
2. Decides to call list_tasks  
3. Stops

That’s it.

No planning intelligence yet.

Just loop + tool execution.

---

## 2.10 Agent Loop Diagram

```
goal = user input

for step in range(max_steps):
    call model
    if model requests tool:
        execute tool
        append tool result
    else:
        break

return final answer
```

If your code does not look like this —  
you do not have a real agent.

---

## 2.11 Guardrails

You must ensure:

- max_steps hard limited  
- No while True loops  
- No recursive self calls  
- Tool whitelist  
- Graceful failure if tool unknown  

This prevents runaway costs.

---

## 2.12 Where Codex Ends and Runtime Begins

Codex:
- Writes agent.py

Runtime:
- Executes agent.py

This separation is critical.

Codex is not in the execution loop.

---

## 🎯 Lesson 2 Checkpoint

Answer clearly:

1. Who owns the loop?  
2. Who executes tools?  
3. Where does token usage occur?  
4. Can MCP server replace tools.py?  
5. Does storage know that an agent exists?  

If these are clear,  
you understand the difference between:

- Deterministic app  
- Agent-wrapped app  

---

## 🔜 Next Lesson Preview

Lesson 3 will:

- Replace local tools with a minimal MCP server  
- Keep agent unchanged  
- Demonstrate decoupling  
- Show why MCP exists  

You will see architecture separation become real.
