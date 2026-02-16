# ðŸ§  Tutorial: Codex, Agents, MCP & Skills  
# Lesson 5 â€” Adding a UI Without Breaking Architecture

---

## ðŸŽ¯ Goal of This Lesson

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
  â†“
GUI (ui.py)
  â†“
Application Layer (main.py)
  â†“
Agent
  â†“
MCP
  â†“
Storage
```

The UI sits above everything.

It does not know how anything works internally.

---

## 5.3 Qt6 Background (Short)

- Qt6 is a mature cross-platform desktop UI framework.
- PySide6 is the official Python binding for Qt6.
- It uses an event-driven model (signals/slots), which fits app-style interfaces well.
- It is heavier than Tkinter, but scales better for richer UIs.

---

## 5.4 Task 1 â€” Create Minimal UI

Ask Codex:

> Create ui.py using PySide6 (Qt6).
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

Student task after generation (behavior only):

1. Run `python main.py --gui` and confirm the window opens correctly.
2. Enter a sample goal, click Submit, and confirm output appears in the UI.
3. Submit twice with different goals and confirm the UI remains responsive and updates output each time.

---

## 5.5 Modify main.py

Ask Codex:

> Modify main.py so that:
> - It can be launched in GUI mode using --gui flag
> - GUI calls the same functions the CLI uses
> - No duplicate logic
> - Add comments explaining why CLI and GUI share the same backend

---

## 5.6 Add Progress Sidebar with Selectable Views

Primary reason: make agent execution flow visible so debugging is fast and reliable.

This section exists to help you debug the agent execution flow step by step.
The sidebar surfaces runtime progress events and lets you inspect them in table and tree views,
without changing backend ownership.

Ask Codex:

> Extend the PySide6 UI to include an "Agent Progress" sidebar panel.
>
> Requirements:
> - Keep backend interface unchanged (main.py, agent loop, MCP, storage responsibilities stay the same).
> - The sidebar must support selectable view modes:
>   1) Table view
>   2) Tree view
> - Add a clear mode selector (tabs, segmented buttons, or combo box).
>
> Table view requirements:
> - Render one row per progress event.
> - Include columns: Time, Type, Name, Details.
> - Apply color classification by event type (for example: step_start, tool_called, tool_result, skill_route, skill_used, validation, stop, error).
> - Keep text readable and aligned.
>
> Tree view requirements:
> - Show hierarchical structure (for example: run -> step -> events).
> - Support expand/collapse per node.
> - Add Expand all and Collapse all controls.
>
> Behavior requirements:
> - Live updates while the agent is running.
> - Switching view mode must not lose data.
> - No OpenAI logic in UI.
> - No tool execution logic in UI.
> - No direct storage writes in UI.
>
> Add comments explaining separation of concerns and why this is UI instrumentation only.

Student task after generation (behavior only):

1. Run `python main.py --gui` and submit a goal that triggers multiple events.
2. Open the Agent Progress sidebar and confirm events appear live while the run is in progress.
3. Switch to Table view and confirm rows are color-classified by event type.
4. Switch to Tree view and confirm nodes can be expanded and collapsed.
5. Use Expand all / Collapse all and confirm both controls work correctly.
6. Switch between Table and Tree several times and confirm no events disappear.

Expected output after this stage:

- GUI includes a right-side Agent Progress panel.
- The same event stream is viewable as Table and Tree.
- Color classification improves scan speed in table mode.
- Tree mode supports collapse/expand for fast structural understanding.

---

## 5.7 What Must Remain True

The following files should remain untouched logically:

- agent.py
- mcp_server.py
- mcp_client.py
- storage.py
- skills/

If adding UI required modifying those â€” architecture leaked.

---

## 5.8 Test Scenario

1. Launch CLI:
   python main.py --goal "Add buy milk"

2. Launch GUI:
   python main.py --gui

3. Enter:
   Plan my tasks

Both paths must go through the same agent.

If they donâ€™t â€” refactor.

---

## 5.9 Why This Matters

Most AI systems fail architecturally because:

- UI mixes reasoning
- Tools mix with agent logic
- Storage imports model code

We are proving:

You can change surface (CLI â†’ GUI)
Without touching core intelligence.

That is professional layering.

---

## 5.10 Optional Extension - Qt6 Enhancements

If you want more realism:

Ask Codex:

> Keep PySide6 (Qt6) and add small UX improvements (layout polish, clearer status text, keyboard submit).
> Keep identical backend interface.
> Do not modify agent, MCP, or storage.

If backend changes were required â€” design is flawed.

---

## 5.11 What This Teaches

You now understand:

- UI is a boundary
- Agent is a control system
- MCP is an execution boundary
- Skill is reasoning injection
- Storage is persistence

Each layer has one responsibility.

---

## ðŸŽ¯ Lesson 5 Checkpoint

Answer:

1. Does GUI know about OpenAI?
2. Does GUI know about MCP?
3. Can we replace UI entirely without touching agent?
4. Is CLI now just another UI?
5. Did adding GUI increase system intelligence?

If answers are clear, you understand clean layering.

---

## ðŸ”œ Next Phase Preview

Next, we will:

- Compile all lessons into a Cookbook
- Refactor project structure
- Add logging & observability
- Discuss production-hardening steps
- Provide roadmap for maturing this into a real product

You now understand the architecture.

