# 🧠 Tutorial: Codex, Agents, MCP & Skills  
# Lesson 5 — Adding a UI Without Breaking Architecture

---

## 🎯 Goal of This Lesson

So far we have:

- A deterministic system (Lesson 1)
- A real agent loop (Lesson 2)
- MCP decoupling (Lesson 3)
- Skills (Lesson 4)

Now we will:

- Add a minimal GUI layer
- Keep architecture unchanged
- Prove UI is just another boundary
- Reinforce separation principles

This lesson is about discipline.

---

## 5.1 Core Principle

UI must not:

- Contain agent logic
- Call OpenAI directly
- Execute tools
- Modify storage directly

UI is only:

- Input collector
- Output renderer

Nothing more.

---

## 5.2 New Architecture Diagram

```
User
  ↓
GUI (ui.py)
  ↓
Application Layer (main.py)
  ↓
Agent
  ↓
MCP
  ↓
Storage
```

The UI sits above everything.

It does not know how anything works internally.

---

## 5.3 Choosing the GUI Toolkit

Windows-first constraint.

Options:

- Tkinter (built-in, simple)
- PySide6 / Qt6 (more professional, slightly heavier)

For learning clarity, start with Tkinter.
You may upgrade to Qt later.

---

## 5.4 Task 1 — Create Minimal UI

Ask Codex:

> Create ui.py.
> Requirements:
> - Simple window with:
>     - Text input field
>     - "Submit" button
>     - Output display area
> - When user clicks Submit:
>     - It calls existing main application function
> - Do NOT import OpenAI here.
> - Do NOT implement agent logic here.
> - Add comments explaining separation of concerns.

---

## 5.5 Modify main.py

Ask Codex:

> Modify main.py so that:
> - It can be launched in GUI mode using --gui flag
> - GUI calls the same functions the CLI uses
> - No duplicate logic
> - Add comments explaining why CLI and GUI share the same backend

---

## 5.6 What Must Remain True

The following files should remain untouched logically:

- agent.py
- mcp_server.py
- mcp_client.py
- storage.py
- skills/

If adding UI required modifying those — architecture leaked.

---

## 5.7 Test Scenario

1. Launch CLI:
   python main.py --goal "Add buy milk"

2. Launch GUI:
   python main.py --gui

3. Enter:
   Plan my tasks

Both paths must go through the same agent.

If they don’t — refactor.

---

## 5.8 Why This Matters

Most AI systems fail architecturally because:

- UI mixes reasoning
- Tools mix with agent logic
- Storage imports model code

We are proving:

You can change surface (CLI → GUI)
Without touching core intelligence.

That is professional layering.

---

## 5.9 Optional Extension — Qt6 Upgrade

If you want more realism:

Ask Codex:

> Replace Tkinter UI with PySide6 version.
> Keep identical backend interface.
> Do not modify agent, MCP, or storage.

If backend changes were required — design is flawed.

---

## 5.10 What This Teaches

You now understand:

- UI is a boundary
- Agent is a control system
- MCP is an execution boundary
- Skill is reasoning injection
- Storage is persistence

Each layer has one responsibility.

---

## 🎯 Lesson 5 Checkpoint

Answer:

1. Does GUI know about OpenAI?
2. Does GUI know about MCP?
3. Can we replace UI entirely without touching agent?
4. Is CLI now just another UI?
5. Did adding GUI increase system intelligence?

If answers are clear, you understand clean layering.

---

## 🔜 Next Phase Preview

Next, we will:

- Compile all lessons into a Cookbook
- Refactor project structure
- Add logging & observability
- Discuss production-hardening steps
- Provide roadmap for maturing this into a real product

You now understand the architecture.
