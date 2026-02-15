# 🧠 Tutorial: Codex, Agents, MCP & Skills  
# Lesson 3 — Decoupling with a Minimal MCP Server

---

## 🎯 Goal of This Lesson

In Lesson 2, our agent called local Python functions directly via tools.py.

Now we will:

- Move tools behind a minimal MCP-style server
- Keep the agent unchanged
- Prove architectural decoupling
- Understand why MCP exists

This is where abstraction becomes real.

---

## 3.1 What Changes — and What Does Not

What stays the same:

- agent.py loop
- max_steps guardrail
- OpenAI API integration
- storage.py
- tasks.json

What changes:

Instead of:

```
Agent → tools.py → storage.py
```

We will now have:

```
Agent → MCP Client → MCP Server → storage.py
```

The agent will not know the difference.

---

## 3.2 Why MCP Exists

MCP (Model Context Protocol) exists to:

- Decouple tools from agent runtime
- Standardize tool discovery
- Allow tools to live in separate processes
- Enable future remote / enterprise integrations

In our local example, this may feel unnecessary.

That is intentional.

We are learning architecture, not chasing convenience.

---

## 3.3 Minimal MCP Design (Local Version)

We will implement:

- A small Python process acting as MCP server
- Communication over stdin/stdout (JSON messages)
- Tool registry
- Deterministic execution

No networking.
No async complexity.
No enterprise features.

---

## 3.4 New Architecture Diagram

```
main.py
   ↓
agent.py
   ↓
mcp_client.py
   ↓ (JSON over stdio)
mcp_server.py  (separate process)
   ↓
storage.py
   ↓
tasks.json
```

Clear separation.

---

## 3.5 Task 1 — Create MCP Server

Ask Codex:

> Create mcp_server.py.  
> Requirements:  
> - Runs as a standalone Python process  
> - Reads JSON messages from stdin  
> - Writes JSON responses to stdout  
> - Supports:  
>     - add_task  
>     - list_tasks  
>     - complete_task  
> - Calls storage.py internally  
> - Includes detailed comments explaining:  
>     - Message format  
>     - Tool dispatch  
>     - Why this is decoupled from the agent  

Keep it synchronous and simple.

---

## Expected MCP Message Format

Request:

```
{
  "tool": "add_task",
  "arguments": { "text": "Buy milk" }
}
```

Response:

```
{
  "status": "ok",
  "result": "..."
}
```

Keep it deterministic.

---

## 3.6 Task 2 — Create MCP Client

Ask Codex:

> Create mcp_client.py.  
> Requirements:  
> - Starts mcp_server.py as subprocess  
> - Sends JSON requests  
> - Receives JSON responses  
> - Handles errors gracefully  
> - Explains:  
>     - Why subprocess boundary matters  
>     - How this simulates real MCP architecture  

---

## 3.7 Modify Agent to Use MCP

Now ask Codex:

> Modify agent.py so that tool calls go through mcp_client.py instead of calling tools.py directly.  
> Do not modify the agent loop structure.  
> Only replace the execution layer.  
> Add comments explaining why the agent remains unchanged.  

---

## Critical Insight

If done correctly:

You will NOT change:

- Loop logic
- Stop conditions
- Token handling
- Step counter

Only execution plumbing changes.

That is architectural separation.

---

## 3.8 What This Teaches You

You now understand:

- Agent ≠ Tool executor
- MCP server is passive
- Agent owns the loop
- Tools live behind boundaries

This is professional architecture.

---

## 3.9 Enterprise What-If

If we had enterprise features:

- MCP server could be remote
- Auth + policy layer could be enforced
- Multiple agents could share tool registry
- Observability & tracing could be centralized

But the mental model remains identical.

---

## 🎯 Lesson 3 Checkpoint

Answer:

1. Did the agent loop change?  
2. Who executes tools now?  
3. Does the MCP server know about OpenAI?  
4. Can multiple agents reuse the same MCP server?  
5. Is storage aware of agent or MCP?  

If you answer clearly, you now understand decoupling.

---

## 🔜 Next Lesson Preview

Lesson 4 will introduce:

- Skills  
- Structured prompt templates  
- Domain logic injection  
- Separation between reasoning and execution  

You will see how skills differ from tools and MCP.
