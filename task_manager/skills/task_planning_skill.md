# Task Planning Skill (Text-Only Policy)

## When To Use This Skill
Use this skill when the user asks to plan work before execution, such as:
- Breaking a goal into actionable tasks
- Sequencing work across phases
- Choosing what to do first under time limits
- Clarifying dependencies, blockers, and assumptions

Do not use this skill when the user asks for direct implementation only and does not want planning.

## Structured Reasoning Rules For Task Planning
1. Restate the goal in one sentence to anchor scope.
2. Identify constraints from the user prompt (time, tools, quality bar, deadlines).
3. Decompose the goal into discrete tasks with clear outcomes.
4. Identify dependencies between tasks (what must happen first).
5. Flag unknowns and assumptions explicitly.
6. Order tasks into a minimal viable sequence.
7. Define completion criteria for each task.
8. Present the plan in concise, testable steps.

## Constraints
- Do not invent user goals, requirements, or deadlines.
- Do not create tasks that were not requested or implied.
- Do not claim facts, files, or system states without evidence.
- Do not convert assumptions into facts; mark them as assumptions.
- Keep scope aligned to the user's stated objective.

## Task Prioritization Rules
Prioritize tasks in this order:
1. Blockers and prerequisites (items that unlock other work)
2. High-impact deliverables tied directly to the user goal
3. Risk-reduction tasks (validation, checks, edge-case prevention)
4. Efficiency tasks (automation/refactor) only after core value is delivered

Tie-breakers:
- Prefer reversible steps over irreversible steps.
- Prefer tasks with clear validation over ambiguous tasks.
- Prefer smaller steps that produce fast feedback.

## Example Skill Content Structure
When user asks to "plan" or "organize":
- First list existing tasks using tool
- Group by priority
- Estimate time realistically
- Never invent tasks