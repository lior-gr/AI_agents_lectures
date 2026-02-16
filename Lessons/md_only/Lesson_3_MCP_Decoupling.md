# Tutorial: Codex, Agents, MCP and Skills
# Lesson 3 - Decoupling with a Minimal MCP Server

---

## Goal of This Lesson

In Lesson 2, our agent called local execution directly.

Now we will:

- Move tools behind a minimal MCP-style server
- Keep the agent loop unchanged
- Prove architectural decoupling
- Understand why MCP exists

This is where execution abstraction becomes concrete.

---

## 3.1 What You Will Learn

By the end of this lesson, you should be clear on:

- Why MCP separates execution from reasoning and loop control
- How to build a deterministic local MCP server over stdin/stdout
- How to add an MCP client and rewire only execution plumbing
- How to verify loop logic and control guards remain unchanged
- How this local pattern maps to future remote/enterprise setups

---

## 3.2 What Changes - and What Does Not

What stays the same:

- `agent.py` loop ownership
- step counter and stop conditions
- OpenAI call path and token controls
- `storage.py` and `tasks_db.json`

What changes:

Instead of:

```text
agent.py -> tools.py -> storage.py
```

We now have:

```text
agent.py -> mcp_client.py -> mcp_server.py -> storage.py
```

Simple example:

- User asks to list tasks
- Agent still decides to call `list_tasks`
- Only execution path changes (local call vs MCP message)

---

## 3.3 Why MCP Exists

MCP exists to:

- Decouple execution from agent runtime logic
- Allow tools to live in separate processes
- Support shared execution infrastructure across multiple agents
- Provide a standard boundary for policy and observability later

In this local lesson, MCP may feel heavier than direct calls.
That is intentional: we are learning architecture discipline.

---

## 3.4 Minimal MCP Design (Local Version)

We implement:

- A standalone Python MCP server process
- JSON request/response communication over stdin/stdout
- Deterministic tool dispatch to storage-backed functions

No networking.
No async framework.
No enterprise infrastructure.

---

## 3.5 Runtime Architecture and Message Format

Runtime flow:

```text
main.py
  -> agent.py
  -> mcp_client.py
  -> mcp_server.py  (JSON over stdio)
  -> storage.py
  -> tasks_db.json
```

Expected message format:

Request:

```json
{
  "tool": "add_task",
  "arguments": { "text": "Buy milk" }
}
```

Response:

```json
{
  "status": "ok",
  "result": "..."
}
```

---

## 3.6 Task 1 - Create MCP Server

Prompt to Codex:

> Create `mcp_server.py`.
> Requirements:
> - Runs as a standalone Python process.
> - Reads JSON messages from stdin.
> - Writes JSON responses to stdout.
> - Supports: `add_task`, `list_tasks`, `complete_task`, `delete_tasks`.
> - Calls `storage.py` internally.
> - Keep it synchronous and deterministic.
>
> Add comments explaining:
> - message format,
> - tool dispatch,
> - why this is decoupled from the agent.
>
> Explanation placement:
> - In code comments: explain request parsing, dispatch, and deterministic errors.
> - In Codex chat response: summarize process model and test steps.
> - In both: explain why server has no loop/planning responsibility.

Expected output after this stage:

- `mcp_server.py` exists as a standalone process entry point.
- Tool dispatch routes to storage-backed behavior only.
- Message format is deterministic and documented.

Student task after generation:

1. Verify stdin request parsing and stdout response serialization are explicit.
2. Verify unknown tools return deterministic error responses.
3. Verify no OpenAI calls exist in `mcp_server.py`.

---

## 3.7 Task 2 - Create MCP Client

Prompt to Codex:

> Create `mcp_client.py`.
> Requirements:
> - Starts `mcp_server.py` as subprocess.
> - Sends JSON requests.
> - Receives JSON responses.
> - Handles startup and request errors gracefully.
>
> Add comments explaining:
> - why subprocess boundary matters,
> - how this simulates real MCP architecture.
>
> Explanation placement:
> - In code comments: explain subprocess lifecycle and I/O handling.
> - In Codex chat response: summarize error paths and verification steps.
> - In both: explain why client does not decide agent behavior.

Expected output after this stage:

- `mcp_client.py` exists and can send/receive deterministic JSON messages.
- Server lifecycle is managed by client code.
- No loop logic is introduced in client/server files.

Student task after generation:

1. Verify server process starts from client side only.
2. Verify malformed or failed responses are handled clearly.
3. Verify client API remains simple for agent integration.

---

## 3.8 Task 3 - Rewire Agent Execution to MCP

Prompt to Codex:

> Modify `agent.py` so tool calls go through `mcp_client.py` instead of `tools.py`.
> Do not modify:
> - loop logic,
> - stop conditions,
> - step counter,
> - token handling.
> Only replace the execution layer.
>
> Add comments explaining why the agent remains unchanged.
>
> Explanation placement:
> - In code comments: explain where execution plumbing changed.
> - In Codex chat response: list unchanged loop/control behaviors.
> - In both: explain reasoning-path vs execution-path separation.

Expected output after this stage:

- Agent uses `mcp_client.py` for execution calls.
- All control-flow guardrails remain intact.
- Architecture boundaries are explicit and testable.

Student task after generation:

1. Run one goal and verify tool calls go through MCP path in logs.
2. Confirm loop structure is unchanged by diff.
3. Confirm MCP failures do not transfer loop ownership away from agent.

---

## 3.9 Critical Insight

If done correctly, you will NOT change:

- Loop logic
- Stop conditions
- Step counter
- Token handling strategy

Only execution plumbing changes.

That is architectural separation.

---

## 3.10 What This Teaches You + Scope Note

You now understand:

- Agent does planning/control; MCP executes tools
- Execution can move out-of-process without changing reasoning flow
- Storage remains unaware of agent and MCP orchestration

Enterprise features we are not using in this course:

- Remote MCP servers: tools run on separate hosts/services
- Auth and policy gates: enforce identity and permissions
- Shared tool registries: many agents reuse one execution layer
- Centralized observability: collect logs/traces/metrics consistently

We exclude these now to focus on core decoupling mental model.

---

## 3.11 Lesson 3 Checkpoint

Answer clearly:

1. Did the agent loop change in this lesson?
2. Who executes tools now?
3. Does the MCP server know about OpenAI?
4. Can multiple agents reuse the same MCP server design?
5. Is storage aware of agent or MCP?

---

## Next Lesson Preview

Lesson 4 introduces:

- Skills
- Structured prompt templates
- Domain-logic injection
- Separation between reasoning and execution

You will see how skills differ from tools and MCP.
