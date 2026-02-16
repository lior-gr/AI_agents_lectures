# Tutorial: Codex, Agents, MCP and Skills
# Lesson 2 - Introducing a Real Minimal Agent Loop

---

## Goal of This Lesson

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
User -> CLI -> storage.py -> tasks_db.json
```

New system:

```
User
  ->
agent.py (loop)
  ->
tools.py (execution)
  ->
storage.py
  ->
tasks_db.json
```

Important:

The agent does NOT replace storage.
It sits above it.

---

## 2.2 Tool Schema Concept

Definition:

`schema = interface contract, implementation = behavior`

Meaning:

- Schema defines what the model is allowed to call and with what arguments.
- Implementation defines what real code does when that tool is called.
- Schema can exist before implementation.

Schema explanation and usage examples:

- Put the schema in `tools.py`.
- Keep behavior in tool execution functions (stub first, real implementation later).

Example schema snippet:

```python
# tools.py
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "delete_tasks",
            "description": "Delete one or more tasks by IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_ids": {"type": "array", "items": {"type": "integer"}}
                },
                "required": ["task_ids"],
            },
        },
    }
]
```

---

## 2.3 Task 1 - Create Schema and Stubs in tools.py

Step 1 prompt:

> Create tools.py.
> Define TOOL_SCHEMAS for:
> - add_task(text: str)
> - list_tasks()
> - complete_task(task_id: int)
> - delete_tasks(task_ids: list[int])  (one or more IDs, matching CLI: `--delete [task_id ...]`)
> Create stub execution functions only (not implemented yet).
> Do not call storage.py yet.
> Add comments that explicitly teach:
> `schema = interface contract, implementation = behavior`.
> Explanation placement:
> - In code comments: explain non-obvious logic and boundaries.
> - In Codex chat response: summarize what changed and how to verify.
> - In both: explain why schema and behavior stay separated.

Expected output after Step 1:

- `tools.py` exists.
- `TOOL_SCHEMAS` exists near top of file.
- Stub execution functions exist for all tools.
- No storage behavior is implemented yet.

Student task after Step 1:

1. Confirm schema exists in tools.py (not agent.py).
2. Confirm delete schema uses one or more IDs.
3. Confirm behavior is still stubbed.

---

## 2.4 Task 2 - Implement the tools

Step 2 prompt:

> Update tools.py.
> Keep TOOL_SCHEMAS unchanged.
> Replace stub execution functions with real storage.py calls for:
> - add_task
> - list_tasks
> - complete_task
> - delete_tasks (one or more IDs)
> Do not move schema into agent.py.
> Explanation placement:
> - In code comments: explain each tool function responsibility.
> - In Codex chat response: summarize behavior changes and verification commands.
> - In both: explain why execution belongs in tools/storage, not agent.

Expected output after Step 2:

- tools.py contains both contract and behavior.
- delete path supports one or more IDs.
- agent.py is still untouched.

Student task after Step 2:

1. Run deterministic commands and verify behavior.
2. Verify schema stayed in tools.py.
3. Verify no agent or model logic was added here.

---

## 2.5 Task 3 - Build agent.py in 4 steps

Step 1 prompt (loop only):

> Create agent.py with a minimal loop skeleton:
> - run_agent(goal: str)
> - max_steps=5
> - message history list
> - stop conditions
> Use a model-call stub for now (no OpenAI call yet).
> Import TOOL_SCHEMAS from tools.py.
> Explanation placement:
> - In code comments: explain loop purpose and stop conditions.
> - In Codex chat response: summarize loop flow and stop behavior.
> - In both: explain why model and tools remain stubbed in Step 1.

Expected output after Agent Step 1:

- agent.py exists with bounded loop skeleton.
- model interaction is still stubbed.

Student task for Step 1:

1. Confirm only loop skeleton primitives were added.
2. Confirm model and tools are still stubs.
3. Explain why agent owns stop conditions and step limit.

Run to verify:

```bash
python -c "from pathlib import Path; s=Path('agent.py').read_text(encoding='utf-8'); print('run_agent' in s and 'max_steps' in s and 'stop' in s)"
```

Step 2 prompt (logger):

> Update agent.py logging.
> Logging requirements:
> - Use Python logging module (not print)
> - Configure format: "%(asctime)s [%(levelname)s] %(message)s"
> - Log events: agent_start, step_start, tool_called, tool_result, stop, error
> - Include `step=<n>/<max_steps>` when relevant
> - Include stop reason in stop logs
> - Do not log secrets
> Explanation placement:
> - In code comments: explain what each log event represents.
> - In Codex chat response: summarize log format and where events appear.
> - In both: explain why logging is added before live model calls.

Expected output after Agent Step 2:

- logging contract is implemented.
- step and stop reason fields exist where relevant.

Student task for Step 2:

1. Confirm logging uses the required format.
2. Confirm required event names appear in code path.
3. Confirm no secrets are logged.

Run to verify:

```bash
python -c "from pathlib import Path; s=Path('agent.py').read_text(encoding='utf-8'); print('%(asctime)s [%(levelname)s] %(message)s' in s and 'agent_start' in s and 'tool_called' in s and 'stop' in s)"
```

Step 3 prompt (wire tools):

> Update agent.py.
> Replace tool-execution stub with real calls to tools.py execution layer.
> Keep model interaction stubbed for now.
> Do not change loop structure.
> Explanation placement:
> - In code comments: explain tool dispatch path.
> - In Codex chat response: summarize which files changed and why.
> - In both: explain why loop control must remain unchanged.

Expected output after Agent Step 3:

- tool calls execute through tools.py.
- model call is still stubbed.

Student task for Step 3:

1. Confirm tool execution now routes via `tools.py`.
2. Confirm model call remains stubbed.
3. Confirm no loop/stop-condition logic changed.

Run to verify:

```bash
python -c "from pathlib import Path; s=Path('agent.py').read_text(encoding='utf-8'); print('TOOL_SCHEMAS' in s and ('from tools import' in s or 'import tools' in s) and 'tool_result' in s)"
```

Step 4 prompt (OpenAI call):

> Update agent.py.
> Replace model-call stub with real OpenAI integration.
> Requirements:
> - API key from environment variable
> - low temperature
> - max token cap (<= 800) using model-compatible parameter:
>   - use `max_completion_tokens` for reasoning models
>   - use `max_tokens` for models that require it
> - pass tools=TOOL_SCHEMAS
> - keep existing loop/logging/tool execution flow unchanged
> Explanation placement:
> - In code comments: explain API-key loading and token-parameter choice.
> - In Codex chat response: summarize model-call settings and error handling.
> - In both: explain why this step changes only model interaction.

OpenAI API key concept and shell setup:

Concept:

- `OPENAI_API_KEY` is a secret credential used by your runtime app to authenticate with OpenAI.
- Generate it in the OpenAI dashboard (API keys page), then copy/store it securely because it is shown only once.
- API usage has real cost; set billing budgets/limits and usage alerts before running repeated tests.
- Never hardcode it in source files, never commit it to git, and load it from environment variables at runtime.

| Shell | Command |
| --- | --- |
| PowerShell | `$env:OPENAI_API_KEY = "your_key_here"` |
| Unix bash | `export OPENAI_API_KEY="your_key_here"` |
| Unix tcsh | `setenv OPENAI_API_KEY "your_key_here"` |

Expected output after Agent Step 4:

- OpenAI interaction is live.
- loop + logger + tools still work as before.

Student task for Step 4:

1. Set your API key for the current shell:

```powershell
$env:OPENAI_API_KEY = "your_key_here"
```

2. Confirm `agent.py` reads key from environment variable only.
3. Do not run end-to-end goal yet; first full run happens in 2.6 after CLI wiring.
4. Confirm loop and tool execution flow remained unchanged.

Run to verify:

```bash
python -c "import os; print('OPENAI_API_KEY set:', bool(os.getenv('OPENAI_API_KEY')))"
```

---

## 2.6 Task 4 - Connect agent to CLI

Step prompt:

> Modify main.py:
> Add a new command:
> `python main.py --goal "Plan my tasks for today"`
> Route it to:
> `agent.run_agent(goal)`
> Keep existing deterministic commands working unchanged.
> Explanation placement:
> - In code comments: explain shared backend entry points between deterministic CLI and goal path.
> - In Codex chat response: summarize compatibility checks and regression verification.
> - In both: explain why this adds a layer instead of replacing deterministic commands.

Expected output after this stage:

- goal path is active.
- deterministic commands still work.
- boundaries remain clean.

Student task:

1. Run deterministic commands and verify no regressions.
2. Run one goal command and inspect logs.
3. Confirm storage remains model-agnostic.

---

## 2.7 Tool Schema Checklist

What to check:

- `TOOL_SCHEMAS` exists in tools.py.
- one entry per tool.
- each entry has `type`, `function.name`, `function.description`, `function.parameters`.
- parameters use JSON-schema-like shape (`type`, `properties`, `required`).
- agent imports schema and passes `tools=TOOL_SCHEMAS`.

Minimal example:

```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "delete_tasks",
            "description": "Delete one or more tasks by task IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                    }
                },
                "required": ["task_ids"],
            },
        },
    }
]
```

---

## 2.8 Checkpoint

Answer clearly:

1. Where does schema live in this lesson?
2. Why can schema exist before implementation?
3. At which step does OpenAI interaction become real?
4. Who owns loop control?
5. Does storage know that an agent exists?

---

## Next Lesson Preview

Lesson 3 will:

- replace local tool execution with MCP boundary,
- keep the loop structure stable,
- show decoupling in practice.
