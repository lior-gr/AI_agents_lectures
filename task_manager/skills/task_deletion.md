<!-- This is a skill, not a tool. -->

# task_deletion

## When To Use This Skill
- Use when the user asks to delete, remove, clean up, or purge tasks.
- Use when deletion criteria are thematic, semantic, or category-based.

## Structured Reasoning Rules
1. Gather the current task state before selecting delete targets.
2. Translate the user request into explicit selection criteria.
3. Match candidate tasks against those criteria using task text and ids.
4. If criteria are ambiguous or risky, ask a short clarification first.
5. Apply deletion only to matched ids.
6. Re-check resulting task state after deletion and summarize the effect.
7. If nothing matched, return a clear no-op result.

## Constraints
- Never delete without an identifiable match to user intent.
- Never invent ids or hidden metadata.
- Never broaden deletion scope beyond requested criteria.
- Never treat uncertain matches as confirmed matches.

## Output Quality Bar
- Deletion rationale should be explicit and auditable.
- Final summary should include what changed and what did not.
- Language should stay precise and conservative for destructive actions.
