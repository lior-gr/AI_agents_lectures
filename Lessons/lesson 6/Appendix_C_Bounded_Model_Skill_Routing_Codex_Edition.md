# Appendix C — Bounded Model-Assisted Skill Routing Using Codex (No Keyword Fallback)

---

## C.1 Goal

Keyword routing is weak. We want synonyms and disambiguation without giving the model full control.

This appendix adds a **bounded, model-assisted skill router** where:

- A *small* model call classifies intent into a fixed enum of skills
- Output must be strict JSON
- We validate deterministically
- We retry until success or a defined fail state
- **No keyword fallback** (your rule)

This is implemented **with Codex writing the code**, step by step.

---

## C.2 Conceptual Diagram

```
User goal text
   ↓
Skill Router (bounded model call)
   ↓  (validated JSON)
Selected optional skills
   ↓
Agent prompt = base system + always_on + selected skill files + user goal
   ↓
Normal agent loop (unchanged)
   ↓
MCP tools (unchanged)
```

Routing affects **prompt composition only**.

---

## C.3 Prerequisites

You already have from earlier lessons:

- `agent.py` with a stable agent loop
- `skills/` directory
- `skills/always_on.md` (always injected)
- Optional skills like:
  - `skills/task_planning.md`
  - `skills/status_reporting.md`
  - `skills/output_format.md`

Also:
- Your OpenAI API key set in your environment (or config) for runtime agent calls.

---

## C.4 The bounded routing contract

### Allowed skills enum

Only these are allowed to be selected by routing:

- `task_planning`
- `status_reporting`
- `output_format`

`always_on` is **not** routable, because it is always injected deterministically.

### Output JSON shape (strict)

The router model must output exactly:

```json
{
  "skills": ["task_planning", "output_format"],
  "confidence": 0.82,
  "notes": "One short sentence."
}
```

Validation rules:

- Must parse as JSON object
- Keys must be exactly: `skills`, `confidence`, `notes`
- `skills` list contains only allowed names, no duplicates
- `confidence` is number in [0, 1]
- `notes` short string (optional for logging only)

If invalid: retry (no fallback).

---

## C.5 Lesson → Task → Expected output → Explanation (Codex driven)

### Lesson: Create a dedicated router module

#### Task (ask Codex)

Ask Codex:

> Create a new file `skill_router.py`.  
> Implement a bounded model-assisted router:
> - `route_skills_with_model(goal: str, call_model_fn, max_attempts: int) -> (ok, skills, reason)`
> - The router must:
>   - Build a routing prompt that lists the allowed skill enum and descriptions
>   - Demand JSON only
>   - Validate the JSON deterministically
>   - Retry until success or fail state after max_attempts
>   - No keyword fallback
> - Keep code pure Python, standard library only (json, typing).
> - Add comments explaining why this is safe and debuggable.
> - Use ASCII only in strings.

#### Expected output

- New file `skill_router.py` exists
- It exports:
  - `ALLOWED_SKILLS`
  - `route_skills_with_model(...)`
- It contains a validator function that rejects:
  - wrong keys
  - unknown skills
  - duplicates
  - non-JSON output

#### Explanation

This isolates routing logic from the rest of the agent.

- Easy to unit test
- Easy to replace later (embeddings, rules, etc.)
- Keeps agent loop unchanged

---

### Lesson: Add a low-cost model call for routing

#### Task (ask Codex)

Ask Codex:

> In `agent.py`, create a small helper `call_router_model(messages) -> str` that:
> - Calls OpenAI with:
>   - low temperature (0 or close)
>   - small max_output_tokens (keep it cheap)
> - Returns the raw text output only
> - Add a short comment explaining why router calls must be cheap.
> Then wire it into `route_skills_with_model`.

#### Expected output

- A separate, cheaper call path is used for routing
- The main agent model call remains unchanged

#### Explanation

Routing does not need creativity. It needs consistency and low cost.

---

### Lesson: Integrate router into prompt construction (without changing the loop)

#### Task (ask Codex)

Ask Codex:

> In `agent.py`, modify the prompt construction so it:
> 1) Always loads `skills/always_on.md`
> 2) Calls `route_skills_with_model(goal, call_router_model, max_attempts=3)`
> 3) If ok:
>    - Loads each selected skill file from `skills/<skill_name>.md` OR maps names to filenames
> 4) If not ok (fail state):
>    - Loads no optional skills, proceed with always_on only
> 5) Concatenates skill texts with a clear separator like "\n\n---\n\n"
> Requirements:
> - Do NOT change the agent loop structure
> - Do NOT change tool execution logic
> - Add comments emphasizing: routing affects reasoning only

#### Expected output

- Agent behavior changes only in reasoning style, not in control-flow
- MCP server and tools remain untouched

#### Explanation

You are changing **instructions** presented to the model, not the runtime mechanics.

---

## C.6 Fail state behavior (no fallback)

When routing fails after `max_attempts`:

- Apply only `always_on` skill
- Continue normal agent loop
- Optionally include a debug log line (one line) stating routing failed

Why:

- No silent application of wrong skills
- No guessing by keywords
- Deterministic safe behavior

---

## C.7 Practical tests (run after Codex implementation)

Run these commands and observe:

1) Synonyms:

- Goal: "display my tasks"
  - expected: `status_reporting`

- Goal: "print tasks in JSON"
  - expected: `status_reporting` + `output_format`

2) Disambiguation:

- Goal: "add tasks about planning a TV show"
  - expected: often none, or only what you decide is correct based on your skill definitions
  - important: router should not crash; if uncertain it can return empty skills with lower confidence

3) Mixed:

- Goal: "plan today in a markdown table"
  - expected: `task_planning` + `output_format`

Tip:

- Temporarily log the selected skills list in agent.py (one line), then remove it.

---

## C.8 Checkpoint

Answer:

1) Who controls which skills are even possible?  
2) Who validates the router output?  
3) What happens if routing fails after all retries?  
4) Did we change the agent loop?  

If these are clear, you have a robust alternative to keyword routing while staying debuggable.

---

## C.9 Notes and sources

Codex skills are typically described as directories containing `SKILL.md` and loaded via progressive disclosure. citeturn0search2turn0search3

This appendix uses our course project style (skills as simple `.md` files loaded by the runtime agent) while keeping the same mental model: skills are passive instructions, not tools. citeturn0search2
