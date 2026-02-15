<!-- This is a skill, not a tool. -->

# task_planning

## When To Use This Skill
Use this skill when the user asks to plan work before execution, such as:
- Breaking a goal into actionable tasks
- Sequencing work across phases
- Choosing what to do first under time limits
- Clarifying dependencies, blockers, and assumptions

Do not use this skill when the user asks for direct implementation only and does not want planning.

## Structured Reasoning Rules
1. Restate the goal in one sentence to anchor scope.
2. Identify constraints from the prompt (time, quality bar, deadlines, resources).
3. Decompose the goal into discrete tasks with clear outcomes.
4. Identify dependencies and ordering constraints.
5. Mark unknowns and assumptions explicitly.
6. Build a minimal viable sequence that can start immediately.
7. Define completion criteria for each step.
8. Present plan steps in concise, testable language.

## Constraints
- Never invent goals, requirements, or deadlines.
- Never create tasks that are unrelated to the stated objective.
- Never claim facts, files, or system state without evidence.
- Never convert assumptions into facts.
- Keep scope aligned to the user request.

## Prioritization Policy
Prioritize in this order:
1. Prerequisites and blockers
2. High-impact deliverables tied directly to the goal
3. Risk-reduction and validation tasks
4. Optimization tasks only after core outcomes are secured

Tie-breakers:
- Prefer reversible steps over irreversible steps.
- Prefer tasks with measurable completion criteria.
- Prefer smaller steps that provide fast feedback.

## Output Quality Bar
- Plan should be executable without hidden assumptions.
- Each step should have an observable outcome.
- Sequence should reflect dependencies and urgency, not guesswork.
