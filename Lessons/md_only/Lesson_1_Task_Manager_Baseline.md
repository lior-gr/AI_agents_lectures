# 🧠 Tutorial: Codex, Agents, MCP & Skills  
# Lesson 1 — Building a Baseline System (No Agents Yet)

---

## 🎯 Goal of This Lesson

Before we build an agent…

We must build something **that does not require one**.

Why?

Because if you don’t understand a deterministic baseline,
you will not understand what the agent actually adds.

In this lesson we will:

- Set up Windows-first environment
- Create a minimal CLI task manager
- Use Codex deliberately and incrementally
- Force Codex to explain its code
- Keep architecture clean

No agents yet. No MCP yet. No skills yet.

Just a deterministic system.

---

## 1.1 Mental Model

We are building this:

```
User → CLI → Task Storage → File (JSON)
```

No decisions.  
No loops.  
No planning.

Pure command → effect.

---

## 1.2 Environment Setup (Windows First)

### Task 1 — Ask Codex to Scaffold the Project

Open VS Code in an empty folder.

Ask Codex:

> Create a minimal cross-platform Python CLI project for a task manager.  
> Requirements:  
> - Must work on Windows first  
> - Use argparse  
> - Store tasks in tasks_db.json  
> - Create virtual environment instructions  
> - Add comments explaining each file  
> - Explanation contract:
>   - In-file comments: explain non-obvious logic, responsibilities, and validations.
>   - Codex chat response: explain architecture choices, assumptions, and verification steps.
>   - Use both when future maintainers and learners both need context.
> Do NOT implement advanced features yet.

---

## Expected Output

Codex should create something like:

```
task_manager/
 ├── main.py
 ├── storage.py
 ├── tasks_db.json (auto-created later)
 ├── README.md
 └── requirements.txt (likely empty)
```

---

## What You Must Check

1. Did Codex separate CLI from storage?
2. Did it comment every function?
3. Did it avoid premature features?
4. Did it include Windows PowerShell setup?

If not — correct it.

You are training Codex.

---

## 1.3 What the Code Should Do

Minimum features:

```
python main.py --add "Buy milk"
python main.py --list
python main.py --complete 1
python main.py --delete 2
python main.py --delete 3 4
```

That’s it.

No sorting.  
No scheduling.  
No AI.

---

## 1.4 Architecture Explanation

We intentionally want this:

```
main.py      → CLI parsing
storage.py   → Read/Write JSON
tasks_db.json   → Data
```

Why?

Because later:

- Agent logic must NOT go inside storage.
- MCP server must NOT go inside main.
- Skills must NOT mutate JSON directly.

Separation now avoids confusion later.

---

## 1.5 Important Engineering Rule

We are building a **clean boundary system**.

Later:

- The Agent will call a tool.
- The tool will call storage.
- Storage will touch JSON.

If we mix everything now,
the architecture collapses.

---

## 1.6 Controlled Prompting Technique

Do NOT say:

> Build a complete task manager with AI planning.

Instead:

Ask in small increments.

Example:

Step 1 prompt:
> Implement only the --add command.  
> Include detailed comments.  
> Do not implement listing yet.  
> In-file comments: explain non-obvious logic and validation checks.  
> In chat: explain what changed and how to test it.

Step 2:
> Now implement --list.  
> Explain how indexing works.  
> In-file comments: explain index rendering rules.  
> In chat: explain index assumptions and edge cases.

Step 3:
> Now implement --complete by task ID.  
> In-file comments: explain edge-case handling.  
> In chat: explain state transitions and verification commands.

Step 4:
> Now implement --delete by task ID (support one or more IDs).  
> In-file comments: explain multi-ID handling and invalid-ID behavior.  
> In chat: explain deletion outcomes and verification commands.

This forces:
- Iterative growth
- Clear structure
- No hallucinated architecture

---

## 1.7 Why No Agent Yet?

Because:

If you introduce AI before baseline stability,
you will never understand what the AI is actually doing.

We want this mental separation:

```
Deterministic system
     +
Agent layer
```

Not:

```
AI spaghetti
```

---

## 🧠 Conceptual Diagram

System Now:

```
User
  ↓
CLI (main.py)
  ↓
Storage (storage.py)
  ↓
tasks_db.json
```

No decision-making loop exists.

Therefore:
This is NOT an agent.

---

## 🎯 Lesson 1 Checkpoint

Answer:

1. Does this system contain an agent?
2. Where would an agent sit if added?
3. Should storage ever call OpenAI?
4. Is Codex part of runtime?

If you can answer clearly,
you are ready for Lesson 2.

---

## 🔜 Next Lesson Preview

Lesson 2 will introduce:

- A real minimal agent loop
- OpenAI API integration
- Cost control
- Max step limits
- Deterministic guardrails

We will wrap the baseline CLI with an agent layer.
